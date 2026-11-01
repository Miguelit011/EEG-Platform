"""
Pestaña «Fatiga aguda» (Fase 10): estados, datos de la pantalla, cifras del test, CSV y la
excepción a la regla de no mencionar la fatiga.

Usan el ejemplo PASAT de la librería (`tests/fixtures/analisis_grabacion_pasat.json`, una
grabación de train con el bloque `por_ventana`), sin el dataset. La paridad de la librería con
el análisis está en EEG-Library (`tests/datos/test_fatiga_aguda_datos.py`).
"""

import copy
import csv
import io
import json
import re
from pathlib import Path

import numpy as np
import pytest
from django.urls import reverse
from eeg_library.modelado.fatiga_aguda import leer_ficha_fatiga_aguda, puntuar

from grabaciones.exportacion import csv_de
from grabaciones.fatiga_aguda import VENTANAS_SUAVIZADO, resumen_fatiga_aguda, suavizar
from grabaciones.models import Grabacion
from tests.auxiliar import FIXTURE, grabacion_con, sin_enlace_fatiga_aguda
from tests.conftest import USA_LA_WEB

pytestmark = USA_LA_WEB

PASAT = json.loads((Path(__file__).parent / "fixtures" / "analisis_grabacion_pasat.json")
                   .read_text(encoding="utf-8"))
RESULTADOS_TEST = (Path(__file__).resolve().parents[2] / "EEG-Library" / "analisis" / "fatiga_aguda"
                   / "06_test" / "resultados_test.json")


def grabacion(resultado=PASAT, condicion="PASAT", estado="procesada"):
    g = grabacion_con(resultado, estado=estado)
    g.condicion = condicion
    g.nombre_original = f"ejemplo_{condicion or 'sin'}.edf"
    g.save()
    return g


def pagina(client, g):
    return client.get(reverse("grabaciones:fatiga_aguda", args=[g.pk])).content.decode()


# ---------------------------------------------------------------------------
# Estados de la pestaña
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("condicion", ["PASAT", "PVTB", "pasat"])
def test_pasat_y_pvtb_muestran_la_pestana_completa(client, condicion):
    html = pagina(client, grabacion(condicion=condicion))
    assert 'id="datos-fatiga"' in html and 'id="datos-visor"' in html
    assert 'id="fa-cinta"' in html and 'id="fa-play"' in html
    assert 'id="escena-3d"' in html
    assert "no el nivel de fatiga de la persona" in html          # el aviso fijo


@pytest.mark.parametrize("condicion", ["OA", "STROOP", ""])
def test_otras_condiciones_explican_a_que_se_aplica(client, condicion):
    html = pagina(client, grabacion(condicion=condicion))
    assert 'id="datos-fatiga"' not in html
    assert "solo existen para las tareas largas <strong>PASAT</strong> y <strong>PVTB</strong>" in html
    assert ("No se conoce la condición" in html) == (condicion == "")


def test_sin_procesar(client):
    html = pagina(client, grabacion(resultado=None, estado="en_cola"))
    assert "todavía no se ha procesado" in html and 'id="datos-fatiga"' not in html


def test_procesada_antes_de_la_fase_ofrece_reprocesar(client):
    g = grabacion(resultado=FIXTURE)          # el ejemplo antiguo, sin `por_ventana`
    g.resultado = {k: v for k, v in FIXTURE.items() if k != "por_ventana"}
    g.archivo = "demo/x.edf"
    g.save()
    html = pagina(client, g)
    assert "volver a procesarla" in html
    assert ('action="' + reverse("grabaciones:encolar", args=[g.pk]) + '"' in html) == g.reprocesable


def test_otros_parametros_no_disponible(client):
    r = copy.deepcopy(PASAT)
    r["parametros_aplicados"]["banda_hz"] = [3.0, 30.0]
    html = pagina(client, grabacion(resultado=r))
    assert "solo es válido con los parámetros" in html and 'id="datos-fatiga"' not in html


def test_atajo_lleva_a_la_grabacion_activa(client):
    g = grabacion()
    respuesta = client.get("/fatiga-aguda/")
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("grabaciones:fatiga_aguda", args=[g.pk])


def test_atajo_sin_grabaciones(client):
    html = client.get("/fatiga-aguda/").content.decode()
    assert "cómo cambia el EEG a lo largo de una tarea PASAT o PVTB" in html


# ---------------------------------------------------------------------------
# Datos de la pantalla
# ---------------------------------------------------------------------------

def test_veredicto_y_cifras_son_los_de_la_libreria_y_el_test():
    g = grabacion()
    fa = resumen_fatiga_aguda(g)
    p = puntuar(PASAT, "PASAT")
    ficha = leer_ficha_fatiga_aguda("PASAT")
    assert fa["estado"] == "ok" and fa["final_mayor"] is p["tercios"]["final_mayor"] is True
    assert fa["veredicto"].startswith("El último tercio de esta grabación se parece más")
    assert fa["rho"] == p["rho"]
    assert fa["ficha"]["test"]["valor"] == f"{ficha['resultado_test']['valor']:.3f}".replace(".", ",")
    assert fa["ficha"]["test"]["azar"] == "0,50"
    assert fa["ficha"]["test"]["n_personas"] == 28


@pytest.mark.skipif(not RESULTADOS_TEST.is_file(), reason="no está EEG-Library al lado")
def test_la_ficha_de_la_pantalla_coincide_con_resultados_test():
    resultados = json.loads(RESULTADOS_TEST.read_text(encoding="utf-8"))
    for condicion, grabaciones in (("PASAT", 102), ("PVTB", 103)):
        fa = resumen_fatiga_aguda(grabacion(condicion=condicion))
        t = resultados["descriptivos"][f"completa | {condicion} | tercios_pareado"]
        lo, hi = t["ic95"]
        assert fa["ficha"]["test"]["valor"] == f"{t['valor']:.3f}".replace(".", ",")
        assert fa["ficha"]["test"]["ic"] == f"{lo:.3f}–{hi:.3f}".replace(".", ",")
        assert fa["ficha"]["test"]["n_grabaciones"] == grabaciones


def test_suavizado_es_media_movil_centrada():
    v = np.arange(30, dtype=float)
    s = suavizar(v)
    mitad = VENTANAS_SUAVIZADO // 2
    assert s[15] == pytest.approx(v[15 - mitad:15 + mitad + 1].mean())
    assert s[0] == pytest.approx(v[:mitad + 1].mean())          # en el extremo, las que hay
    assert s[-1] == pytest.approx(v[-mitad - 1:].mean())


def test_datos_de_la_animacion():
    fa = resumen_fatiga_aguda(grabacion())
    datos, visor = fa["fatiga"], fa["visor"]
    n = PASAT["metadatos"]["n_epocas"]
    assert len(datos["instante_s"]) == len(datos["puntuacion"]) == n
    assert max(abs(x) for x in datos["puntuacion"]) == pytest.approx(1.0)   # normalizada para la cinta
    assert list(datos["fotogramas"]) == ["delta", "theta", "alfa", "beta"]
    for banda, por_canal in datos["cambios"].items():
        for canal, serie in por_canal.items():
            assert len(serie) == n == len(datos["fotogramas"][banda][canal])
    assert visor["banda_inicial"] == "beta" and visor["metrica_inicial"] == "cambio"
    lo, hi = visor["rango_cambio"]["beta"]
    assert lo == -hi and hi > 0
    lo, hi = visor["rango_fijo"]["beta"]
    assert 0 <= lo < hi <= 100
    # Los tercios de la cinta se cortan como en la librería: por el inicio de la última ventana.
    assert datos["tercios_s"] == pytest.approx([datos["instante_s"][-1] / 3, 2 * datos["instante_s"][-1] / 3])


def test_el_cambio_parte_de_cero_en_el_primer_tercio():
    fa = resumen_fatiga_aguda(grabacion())
    instantes = np.array(fa["fatiga"]["instante_s"])
    primero = instantes <= instantes[-1] / 3
    for por_canal in fa["fatiga"]["cambios"].values():
        for serie in por_canal.values():
            assert abs(np.mean(np.array(serie)[primero])) < 0.01


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def test_csv_lleva_los_valores_de_la_libreria():
    g, otra = grabacion(), grabacion(condicion="OA")
    filas = list(csv.DictReader(io.StringIO(csv_de([g, otra]).decode("utf-8-sig")), delimiter=";"))
    p = puntuar(PASAT, "PASAT")
    assert float(filas[0]["fatiga_aguda_rho"].replace(",", ".")) == pytest.approx(p["rho"], abs=1e-6)
    assert float(filas[0]["fatiga_aguda_p_ultimo_tercio"].replace(",", ".")) == pytest.approx(
        p["tercios"]["p_ultimo"], abs=1e-6)
    assert filas[0]["fatiga_aguda_final_mayor"] == "1"
    assert all(filas[1][c] == "" for c in filas[1] if c.startswith("fatiga_aguda_"))


# ---------------------------------------------------------------------------
# La palabra «fatiga»: en la barra y en esta pestaña, en ningún otro sitio nuevo
# ---------------------------------------------------------------------------

def test_enlace_en_la_barra_y_unica_excepcion(client):
    g = grabacion()
    lista = client.get("/grabaciones/").content.decode()
    assert reverse("grabaciones:fatiga_aguda", args=[g.pk]) in lista
    assert "fatiga" not in sin_enlace_fatiga_aguda(lista).lower()


def test_sin_recursos_externos(client):
    html = pagina(client, grabacion())
    assert not re.search(r'(src|href)\s*=\s*["\'](https?:)?//', html, re.I)


def test_pagina_marca_la_pestana_activa(client):
    html = pagina(client, grabacion())
    assert re.search(r'aria-current="page"\s*>Fatiga aguda</a>', html)


def test_los_estados_no_dependen_de_un_objeto_raro():
    g = Grabacion(estado="procesada", condicion="PVTB", resultado=None)
    assert resumen_fatiga_aguda(g) == {"estado": "sin_procesar"}
