"""Pantalla de calidad: se construye solo a partir del JSON guardado de la grabación."""

import contextlib
import copy
import io
import json
import math
import re
from pathlib import Path

import mne
import numpy as np
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.preprocesado.referencing import aplicar_car

from grabaciones import calidad
from grabaciones.calidad import POSICIONES, nivel_de_fiabilidad, resumen_calidad
from grabaciones.models import Grabacion, Lote
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "analisis_grabacion.json")
                     .read_text(encoding="utf-8"))
MOTIVO = "Amplitud excesiva (z=5.00 > 3.00)"


def variante(descartados=(), car=True, eliminadas=(), referencia="car_condicional"):
    """El fixture con otros electrodos descartados, otra CAR o más componentes de ICA."""
    r = copy.deepcopy(FIXTURE)
    for canal, datos in r["calidad"].items():
        malo = canal in descartados
        datos["estado"] = "descartado" if malo else "bueno"
        datos["motivo"] = MOTIVO if malo else None
    r["metadatos"]["n_canales_buenos"] = len(CANALES_EPOC) - len(descartados)
    r["parametros_aplicados"]["car_aplicada"] = car
    r["parametros_aplicados"]["referencia"] = referencia
    r["parametros_aplicados"]["ica"]["componentes_eliminadas"] = list(eliminadas)
    return r


def grabacion_con(resultado, estado="procesada"):
    lote = Lote.objects.create()
    return Grabacion.objects.create(
        lote=lote, nombre_original="ejemplo_OA.edf", condicion="OA", estado=estado,
        duracion_s=137.0, sfreq_original_hz=256.0, resultado=resultado,
        n_canales_buenos=(resultado or {}).get("metadatos", {}).get("n_canales_buenos"))


def mapa(html):
    return re.search(r'<svg class="mapa-cabeza".*?</svg>', html, re.S).group(0)


# ---------------------------------------------------------------------------
# Datos de la pantalla (función pura)
# ---------------------------------------------------------------------------

def test_con_el_fixture():
    r = resumen_calidad(FIXTURE)
    assert r["titular"] == "12 de 14 electrodos buenos"
    assert r["frase"] == "Se han descartado 2 electrodos: F7, F3."
    assert [e["canal"] for e in r["electrodos"]] == CANALES_EPOC
    f7 = next(e for e in r["electrodos"] if e["canal"] == "F7")
    assert not f7["bueno"] and f7["zona"] == "Frontal" and f7["estado"] == "Descartado"
    assert f7["motivo"].startswith("Amplitud excesiva") and "amplitud" in f7["ayuda"]
    assert next(e for e in r["electrodos"] if e["canal"] == "AF3")["motivo"] == ""
    assert r["nivel"] == "normal" and r["aviso"] == ""


def test_sin_ningun_descartado():
    r = resumen_calidad(variante())
    assert r["titular"] == "14 de 14 electrodos buenos"
    assert r["frase"] == "Los 14 electrodos son aprovechables."
    assert all(e["bueno"] for e in r["electrodos"]) and r["aviso"] == ""


def test_un_descartado():
    r = resumen_calidad(variante(["O1"]))
    assert r["titular"] == "13 de 14 electrodos buenos"
    assert r["frase"] == "Se ha descartado 1 electrodo: O1."


def test_varios_descartados():
    r = resumen_calidad(variante(["O1", "O2", "T7", "T8", "P7", "P8"]))
    assert r["n_buenos"] == 8 and r["nivel"] == "normal"
    assert r["frase"].startswith("Se han descartado 6 electrodos: ")


@pytest.mark.parametrize("n_buenos, nivel, texto", [
    (14, "normal", ""),
    (8, "normal", ""),
    (7, "aviso", "7 electrodos buenos (se recomiendan al menos 8)."),
    (6, "aviso", "6 electrodos buenos (se recomiendan al menos 8)."),
    (5, "critico", "Solo 5 electrodos buenos: resultados no fiables (mínimo recomendado: 6)."),
    (0, "critico", "Solo 0 electrodos buenos: resultados no fiables (mínimo recomendado: 6)."),
])
def test_avisos_como_en_la_libreria(n_buenos, nivel, texto):
    assert nivel_de_fiabilidad(n_buenos) == (nivel, texto)
    r = resumen_calidad(variante(CANALES_EPOC[n_buenos:]))
    assert (r["nivel"], r["aviso"]) == (nivel, texto)


def _raw_con_14_canales():
    info = mne.create_info(list(CANALES_EPOC), 256, "eeg")
    return mne.io.RawArray(np.random.default_rng(0).normal(0, 1e-6, (14, 256)), info,
                           verbose=False)


def test_los_umbrales_siguen_siendo_los_de_la_libreria():
    """La librería no expone sus umbrales: se leen de lo que hace y de lo que avisa."""
    raw = _raw_con_14_canales()

    def car(n):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            _, meta = aplicar_car(raw, list(CANALES_EPOC[:n]))
        return meta["metodo"], salida.getvalue()

    minimo = calidad.MINIMO_FIABLE
    recomendados = calidad.RECOMENDADOS
    assert car(minimo - 1)[0] == "ninguno"                      # < mínimo: CAR omitida
    assert car(minimo)[0] == "CAR"
    metodo, texto = car(recomendados - 1)                        # < recomendados: avisa
    assert metodo == "CAR" and f"al menos {recomendados}" in texto
    assert "ADVERTENCIA" not in car(recomendados)[1]             # ≥ recomendados: no avisa


def test_car_omitida_se_explica():
    r = resumen_calidad(variante(CANALES_EPOC[5:], car=False))
    pipeline = dict(r["pipeline"])
    assert r["car_omitida"] and pipeline["CAR"].startswith("No: con menos de 6")


def test_referencia_original_sin_car():
    r = resumen_calidad(variante(car=False, referencia="original"))
    pipeline = dict(r["pipeline"])
    assert not r["car_omitida"] and "referencia original" in pipeline["CAR"]
    assert pipeline["Referencia"].startswith("Original del casco")


def test_componentes_de_ica_eliminadas():
    pipeline = dict(resumen_calidad(variante(eliminadas=[0, 3]))["pipeline"])
    assert "2 componentes eliminadas (nº 0, 3)" in pipeline["ICA"]
    assert "Ninguna componente eliminada" in dict(resumen_calidad(FIXTURE)["pipeline"])["ICA"]
    assert "1 componente eliminada (nº 2)" in dict(
        resumen_calidad(variante(eliminadas=[2]))["pipeline"])["ICA"]


def test_resumen_sin_calidad():
    assert resumen_calidad(None) is None and resumen_calidad({}) is None


# ---------------------------------------------------------------------------
# Mapa de electrodos
# ---------------------------------------------------------------------------

def test_posiciones_del_emotiv():
    assert set(POSICIONES) == set(CANALES_EPOC)
    izquierda = {"AF3", "F7", "F3", "FC5", "T7", "P7", "O1"}
    for canal, (x, y) in POSICIONES.items():
        assert (x < 0) == (canal in izquierda), canal   # impares a la izquierda
        assert math.hypot(x, y) < 0.9
    y = {c: POSICIONES[c][1] for c in CANALES_EPOC}
    assert y["AF3"] > y["F3"] > y["FC5"] > y["T7"] > y["P7"] > y["O1"]   # frente → nuca


def test_los_electrodos_no_se_solapan_y_caben_en_la_cabeza():
    puntos = resumen_calidad(FIXTURE)["electrodos"]
    for i, a in enumerate(puntos):
        d_centro = math.hypot(a["cx"] - calidad.CENTRO[0], a["cy"] - calidad.CENTRO[1])
        assert d_centro + 25 <= calidad.RADIO + 5, a["canal"]
        for b in puntos[i + 1:]:
            assert math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"]) >= 46, (a["canal"], b["canal"])


# ---------------------------------------------------------------------------
# Vista
# ---------------------------------------------------------------------------

def test_pantalla_con_el_fixture(client):
    g = grabacion_con(FIXTURE)
    respuesta = client.get(reverse("grabaciones:calidad", args=[g.pk]))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "12 de 14 electrodos buenos" in html
    assert "Se han descartado 2 electrodos: F7, F3." in html
    assert "Amplitud excesiva (z=8.27 &gt; 3.00)" in html
    assert "ejemplo_OA.edf" in html and "Condición: OA" in html
    svg = mapa(html)
    assert svg.count("<circle cx=") == 12 and svg.count("<polygon") == 2
    # Cada electrodo lleva su nombre y su símbolo.
    for canal in CANALES_EPOC:
        assert f">{canal}</text>" in svg
    assert svg.count("✔") == 12 and svg.count("✖") == 2


def test_el_estado_no_depende_solo_del_color(client):
    html = client.get(reverse("grabaciones:calidad",
                              args=[grabacion_con(variante(["F7"])).pk])).content.decode()
    svg = mapa(html)
    # Forma distinta (rombo / círculo), símbolo, título con el motivo y texto en la tabla.
    assert "<polygon" in svg and "<title>F7: descartado. Amplitud excesiva" in svg
    assert "<title>AF3: bueno</title>" in svg
    assert "✖ Descartado" in html and "✔ Bueno" in html
    # Y la leyenda explica las dos formas.
    assert "Leyenda" in html


@pytest.mark.parametrize("descartados, n_rombos", [
    ([], 0),
    (["O2"], 1),
    (["F7", "F3", "T7", "O1", "O2"], 5),
    (list(CANALES_EPOC[:11]), 11),
])
def test_pantalla_con_0_1_o_varios_descartados(client, descartados, n_rombos):
    g = grabacion_con(variante(descartados))
    html = client.get(reverse("grabaciones:calidad", args=[g.pk])).content.decode()
    svg = mapa(html)
    assert svg.count("<polygon") == n_rombos
    assert svg.count("<circle cx=") == 14 - n_rombos
    assert f"{14 - n_rombos} de 14 electrodos buenos" in html
    assert ("aprovechables" in html) == (n_rombos == 0)


def test_aviso_con_pocos_electrodos_buenos(client):
    g = grabacion_con(variante(CANALES_EPOC[5:], car=False))
    html = client.get(reverse("grabaciones:calidad", args=[g.pk])).content.decode()
    assert "Solo 5 electrodos buenos: resultados no fiables (mínimo recomendado: 6)." in html
    assert "No se aplicó la CAR." in html and "se procesa igualmente" in html


def test_sin_aviso_con_electrodos_suficientes(client):
    html = client.get(reverse("grabaciones:calidad",
                              args=[grabacion_con(FIXTURE).pk])).content.decode()
    assert "no fiables" not in html and "se recomiendan" not in html


def test_svg_sin_decimales_con_coma(client):
    html = client.get(reverse("grabaciones:calidad",
                              args=[grabacion_con(FIXTURE).pk])).content.decode()
    svg = mapa(html)
    assert not re.search(r'\b(cx|cy|x|y)="[^"]*,', svg)
    # Los rombos son cuatro pares «x,y»; un decimal con coma rompería el recuento.
    for puntos in re.findall(r'points="([^"]*)"', svg):
        assert re.fullmatch(r"(-?\d+,-?\d+ ?){4}", puntos), puntos


@pytest.mark.parametrize("estado, texto", [
    ("en_cola", "todavía no se ha procesado (en cola)"),
    ("procesando", "todavía no se ha procesado (procesando)"),
    ("error", "no se pudo procesar"),
])
def test_grabacion_sin_procesar(client, estado, texto):
    g = grabacion_con(None, estado=estado)
    g.mensaje_error = "fallo de prueba"
    g.save()
    respuesta = client.get(reverse("grabaciones:calidad", args=[g.pk]))
    assert respuesta.status_code == 200 and texto in respuesta.content.decode()


def test_grabacion_inexistente(client):
    assert client.get(reverse("grabaciones:calidad", args=[999])).status_code == 404


def test_navegacion_de_la_pantalla(client):
    g = grabacion_con(FIXTURE)
    html = client.get(reverse("grabaciones:calidad", args=[g.pk])).content.decode()
    assert re.search(r'<a href="[^"]+calidad/"\s+aria-current="page">Calidad', html)
    assert re.search(r'class="desactivado"[^>]*>Análisis<', html)   # llega en la Fase 5


def test_sin_recursos_externos_ni_fatiga(client):
    for resultado in (FIXTURE, variante(), variante(CANALES_EPOC[5:], car=False)):
        g = grabacion_con(resultado)
        html = client.get(reverse("grabaciones:calidad", args=[g.pk])).content.decode()
        assert not re.search(r'(src|href)\s*=\s*["\'](https?:)?//', html, re.I)
        assert "fatiga" not in html.lower()


# ---------------------------------------------------------------------------
# Lista
# ---------------------------------------------------------------------------

def test_la_lista_enlaza_a_calidad_y_avisa(client):
    lote = Lote.objects.create()
    for nombre, estado, n in [("bien.edf", "procesada", 12), ("justa.edf", "procesada", 7),
                              ("mal.edf", "procesada", 5), ("cola.edf", "en_cola", None)]:
        Grabacion.objects.create(lote=lote, nombre_original=nombre, estado=estado,
                                 n_canales_buenos=n)
    html = client.get("/").content.decode()
    assert html.count(">Calidad</a>") == 3          # solo las procesadas
    assert "7 electrodos buenos (se recomiendan al menos 8)." in html
    assert "Solo 5 electrodos buenos: resultados no fiables" in html
    assert html.count("electrodos buenos") == 2     # la de 12 no avisa


def test_la_lista_no_carga_el_json_de_resultados(client):
    grabacion_con(FIXTURE)
    contexto = client.get("/").context
    g = contexto["lotes"][0].grabaciones.all()[0]
    assert "resultado" in g.get_deferred_fields()


# ---------------------------------------------------------------------------
# De extremo a extremo con un EDF sintético
# ---------------------------------------------------------------------------

def test_grabacion_procesada_de_verdad(client, tmp_path):
    from grabaciones import procesador
    from tests.test_procesador import EjecutorSincrono

    datos = {"referencia": "car_condicional", "banda": "1-30", "notch": "on",
             "archivos": [SimpleUploadedFile(
                 "sub-C1F001_task-OC.edf", escribir_edf(tmp_path / "a.edf", 30).read_bytes())]}
    client.post(reverse("grabaciones:subir"), datos)
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())

    g = Grabacion.objects.get()
    assert g.estado == "procesada"
    assert g.n_canales_buenos == g.resultado["metadatos"]["n_canales_buenos"]
    html = client.get(reverse("grabaciones:calidad", args=[g.pk])).content.decode()
    assert f"{g.n_canales_buenos} de 14 electrodos buenos" in html
    assert len(re.findall(r'<g class="punto punto-', mapa(html))) == 14
