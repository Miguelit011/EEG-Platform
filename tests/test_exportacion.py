"""Exportación a CSV: una fila por grabación procesada, con columnas estables y documentadas."""

import csv
import io
import math
import re

import pandas as pd
import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.procesado.matrix import REGIONES

from grabaciones.exportacion import (
    BANDAS, columnas, csv_de, documentacion_markdown, nombre_de_archivo_seguro)
from grabaciones.models import Grabacion
from tests.auxiliar import FIXTURE, grabacion_con, variante
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB

DESCARTADOS_FIXTURE = ["F7", "F3"]


def leer(contenido):
    """El CSV como DataFrame, leído como lo haría Excel en español (o pandas con sus opciones)."""
    return pd.read_csv(io.BytesIO(contenido), sep=";", decimal=",", encoding="utf-8-sig")


def filas_de_texto(contenido):
    """El CSV como lista de dicts de texto, sin conversiones."""
    texto = contenido.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"))


# ---------------------------------------------------------------------------
# Columnas
# ---------------------------------------------------------------------------

def test_columnas_estables():
    nombres = [c.nombre for c in columnas()]
    assert nombres[:8] == ["archivo", "lote", "condicion", "origen_condicion", "duracion_s",
                           "n_epocas", "frecuencia_original_hz", "remuestreada"]
    assert nombres[8:17] == [
        "electrodos_buenos", "electrodos_descartados", "referencia", "car_aplicada",
        "banda_min_hz", "banda_max_hz", "notch_hz", "ica_n_componentes_eliminadas",
        "ica_componentes_eliminadas"]
    assert nombres[17:21] == ["cabeza_delta_rel", "cabeza_theta_rel", "cabeza_alfa_rel",
                              "cabeza_beta_rel"]
    assert nombres[21:29] == [
        "zona_frontal_delta_rel", "zona_frontal_theta_rel", "zona_frontal_alfa_rel",
        "zona_frontal_beta_rel", "zona_frontal_delta_logabs", "zona_frontal_theta_logabs",
        "zona_frontal_alfa_logabs", "zona_frontal_beta_logabs"]
    assert nombres[53:61] == [
        "rel_AF3_delta", "rel_AF3_theta", "rel_AF3_alfa", "rel_AF3_beta",
        "logabs_AF3_delta", "logabs_AF3_theta", "logabs_AF3_alfa", "logabs_AF3_beta"]
    assert nombres[165:167] == ["version_eeg_library", "fecha_analisis"]
    # 8 + 9 + 4 + 4 zonas × 8 + 14 electrodos × 8 + 2, los modelos (4 + 4 + 7) y, al final,
    # fatiga aguda (4): añadirlas al final no movió ninguna columna anterior.
    assert len(nombres) == 8 + 9 + 4 + 4 * 8 + 14 * 8 + 2 + 15 + 4 == 186
    assert nombres[182:] == ["fatiga_aguda_rho", "fatiga_aguda_p_primer_tercio",
                             "fatiga_aguda_p_ultimo_tercio", "fatiga_aguda_final_mayor"]
    assert nombres[167:182] == [
        "c1_oa_oc_logistica_clase", "c1_oa_oc_logistica_p_OA", "c1_oa_oc_logistica_p_OC",
        "c1_oa_oc_logistica_condicion_estimada",
        "c2_reposo_tarea_logistica_clase", "c2_reposo_tarea_logistica_p_reposo",
        "c2_reposo_tarea_logistica_p_tarea", "c2_reposo_tarea_logistica_condicion_estimada",
        "c3_tareas_logistica_clase", "c3_tareas_logistica_p_STROOP", "c3_tareas_logistica_p_PASAT",
        "c3_tareas_logistica_p_PVTB", "c3_tareas_logistica_p_MSIT", "c3_tareas_logistica_p_PVSAT",
        "c3_tareas_logistica_condicion_estimada"]


def test_nombres_validos_para_spss_y_sin_fatiga():
    nombres = [c.nombre for c in columnas()]
    assert len(set(nombres)) == len(nombres)
    for n in nombres:
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n) and len(n) <= 64, n
        # Solo las columnas de la pestaña Fatiga aguda llevan la palabra (decisión del autor).
        assert ("fatiga" not in n.lower() or n.startswith("fatiga_aguda_")) and not n.startswith("indice_")
    assert all(c.descripcion and c.unidad and c.seccion for c in columnas())


def test_hay_columna_por_electrodo_banda_y_zona_banda():
    nombres = {c.nombre for c in columnas()}
    for canal in CANALES_EPOC:
        for b in BANDAS:
            assert f"rel_{canal}_{b}" in nombres and f"logabs_{canal}_{b}" in nombres
    for zona in REGIONES:
        for b in BANDAS:
            assert f"zona_{zona}_{b}_rel" in nombres and f"zona_{zona}_{b}_logabs" in nombres


def test_la_documentacion_esta_al_dia():
    ruta = settings.BASE_DIR / "docs" / "COLUMNAS_CSV.md"
    assert ruta.read_text(encoding="utf-8") == documentacion_markdown(), \
        "docs/COLUMNAS_CSV.md está desactualizado: ejecuta `manage.py documentar_csv`."
    # Cada columna aparece documentada una vez.
    texto = ruta.read_text(encoding="utf-8")
    for c in columnas():
        assert texto.count(f"| `{c.nombre}` |") == 1, c.nombre


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------

def test_formato_para_excel_en_espanol(client):
    g = grabacion_con(FIXTURE)
    contenido = csv_de([g])
    assert contenido.startswith(b"\xef\xbb\xbf")             # UTF-8 con BOM
    assert contenido.count(b"\xef\xbb\xbf") == 1
    lineas = contenido.decode("utf-8-sig").split("\r\n")
    assert len(lineas) == 3 and lineas[2] == ""              # cabecera + 1 fila, saltos de Windows
    assert lineas[0].split(";") == [c.nombre for c in columnas()]
    assert len(lineas[1].split(";")) == len(columnas())      # ningún valor contiene «;»
    assert "0,286840" in lineas[1]                           # decimal con coma


def test_valores_del_fixture():
    f = filas_de_texto(csv_de([grabacion_con(FIXTURE)]))[0]
    assert f["archivo"] == "ejemplo_OA.edf" and f["condicion"] == "OA"
    assert f["origen_condicion"] == "vacia" and f["lote"].isdigit()
    assert f["duracion_s"] == "137,00" and f["n_epocas"] == "62"
    assert f["frecuencia_original_hz"] == "256" and f["remuestreada"] == "0"
    assert f["electrodos_buenos"] == "12" and f["electrodos_descartados"] == "F7|F3"
    assert f["referencia"] == "car_condicional" and f["car_aplicada"] == "1"
    assert (f["banda_min_hz"], f["banda_max_hz"], f["notch_hz"]) == ("1", "30", "50")
    assert f["ica_n_componentes_eliminadas"] == "0" and f["ica_componentes_eliminadas"] == ""
    assert f["version_eeg_library"] == "0.15.0"
    assert f["fecha_analisis"] == "2026-11-01T19:41:01"


def test_las_potencias_coinciden_con_el_json():
    tabla = leer(csv_de([grabacion_con(FIXTURE)]))
    fila = tabla.iloc[0]
    por_canal = FIXTURE["potencia"]["por_canal"]
    por_region = FIXTURE["potencia"]["por_region"]
    for canal in CANALES_EPOC:
        for b in BANDAS:
            if canal in DESCARTADOS_FIXTURE:
                assert pd.isna(fila[f"rel_{canal}_{b}"]) and pd.isna(fila[f"logabs_{canal}_{b}"])
            else:
                datos = por_canal[canal][b]
                assert fila[f"rel_{canal}_{b}"] == pytest.approx(datos["relativa"], abs=1e-6)
                assert fila[f"logabs_{canal}_{b}"] == pytest.approx(
                    math.log10(datos["absoluta_v2"]), abs=1e-4)
    for zona in REGIONES:
        for b in BANDAS:
            assert fila[f"zona_{zona}_{b}_rel"] == pytest.approx(
                por_region[zona][b]["relativa"], abs=1e-6)
            assert fila[f"zona_{zona}_{b}_logabs"] == pytest.approx(
                por_region[zona][b]["log10_absoluta_v2"], abs=1e-4)
    for b in BANDAS:
        validos = [por_canal[c][b]["relativa"] for c in CANALES_EPOC
                   if c not in DESCARTADOS_FIXTURE]
        assert fila[f"cabeza_{b}_rel"] == pytest.approx(sum(validos) / len(validos), abs=1e-6)


def test_las_columnas_numericas_se_leen_como_numeros():
    tabla = leer(csv_de([grabacion_con(FIXTURE)]))
    for c in columnas():
        if c.unidad not in ("texto",):
            assert pd.api.types.is_numeric_dtype(tabla[c.nombre]), c.nombre


def test_los_descartados_van_vacios_y_nunca_a_cero():
    f = filas_de_texto(csv_de([grabacion_con(FIXTURE)]))[0]
    for canal in DESCARTADOS_FIXTURE:
        for b in BANDAS:
            assert f[f"rel_{canal}_{b}"] == "" and f[f"logabs_{canal}_{b}"] == ""
    assert f["rel_AF3_delta"] != ""


def test_zona_sin_electrodos_validos_va_vacia():
    f = filas_de_texto(csv_de([grabacion_con(variante(["T7", "T8"]))]))[0]
    assert f["electrodos_descartados"] == "T7|T8"
    for b in BANDAS:
        assert f[f"zona_temporal_{b}_rel"] == "" and f[f"zona_temporal_{b}_logabs"] == ""
        assert f[f"zona_frontal_{b}_rel"] != ""


def test_ica_car_y_paso_banda():
    r = variante(CANALES_EPOC[5:], car=False, eliminadas=[0, 3], banda_hz=[3.0, 30.0])
    r["parametros_aplicados"]["notch_hz"] = None
    f = filas_de_texto(csv_de([grabacion_con(r)]))[0]
    assert f["ica_n_componentes_eliminadas"] == "2" and f["ica_componentes_eliminadas"] == "0|3"
    assert f["car_aplicada"] == "0" and f["banda_min_hz"] == "3" and f["notch_hz"] == ""
    assert f["electrodos_buenos"] == "5"


def test_remuestreada():
    r = variante()
    r["metadatos"]["resampleado"] = True
    r["metadatos"]["sfreq_original_hz"] = 128.0
    f = filas_de_texto(csv_de([grabacion_con(r)]))[0]
    assert (f["remuestreada"], f["frecuencia_original_hz"]) == ("1", "128")


@pytest.mark.parametrize("nombre", ["=SUMA(A1:A2).edf", "+cmd.edf", "-1.edf", "@x.edf"])
def test_texto_que_excel_tomaria_por_formula(nombre):
    g = grabacion_con(FIXTURE)
    g.nombre_original = nombre
    g.condicion = "=1+1"
    f = filas_de_texto(csv_de([g]))[0]
    assert f["archivo"] == "'" + nombre and f["condicion"] == "'=1+1"


def test_sin_fatiga_en_el_csv():
    """Fuera de los nombres de las columnas `fatiga_aguda_*`, el CSV no menciona la fatiga."""
    cabecera, filas = csv_de([grabacion_con(FIXTURE)]).decode("utf-8").split("\r\n", 1)
    assert "fatiga" not in filas.lower()
    assert all(c.startswith("fatiga_aguda_") for c in cabecera.lstrip("\ufeff").split(";")
               if "fatiga" in c.lower())


def test_formato_configurable(settings):
    settings.CSV_SEPARADOR, settings.CSV_DECIMAL, settings.CSV_CODIFICACION = ",", ".", "utf-8"
    contenido = csv_de([grabacion_con(FIXTURE)])
    assert not contenido.startswith(b"\xef\xbb\xbf")
    tabla = pd.read_csv(io.BytesIO(contenido))               # formato internacional
    assert tabla.loc[0, "rel_AF3_alfa"] == pytest.approx(0.28684, abs=1e-6)
    assert tabla.loc[0, "electrodos_descartados"] == "F7|F3"


def test_nombre_de_archivo_seguro():
    assert nombre_de_archivo_seguro("sub-T1F081_ses-M2_task-OA_eeg") == \
        "sub-T1F081_ses-M2_task-OA_eeg"
    assert nombre_de_archivo_seguro("sub C1/ñ 01") == "sub_C1___01"
    assert nombre_de_archivo_seguro("...") == "grabacion"


# ---------------------------------------------------------------------------
# Descargas
# ---------------------------------------------------------------------------

def test_descarga_de_una_grabacion(client):
    g = grabacion_con(FIXTURE)
    g.nombre_original = "sub-T1F081_ses-M2_task-OA_eeg.edf"
    g.save()
    r = client.get(reverse("grabaciones:csv_grabacion", args=[g.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "text/csv; charset=utf-8"
    assert r["Content-Disposition"] == 'attachment; filename="eeg_sub-T1F081_ses-M2_task-OA_eeg.csv"'
    tabla = leer(r.content)
    assert len(tabla) == 1 and tabla.loc[0, "archivo"] == "sub-T1F081_ses-M2_task-OA_eeg.edf"


def test_descarga_del_lote_solo_incluye_las_procesadas(client):
    primera = grabacion_con(FIXTURE)
    lote = primera.lote
    for nombre, estado, resultado in [("b.edf", "procesada", variante(["O1"])),
                                      ("c.edf", "en_cola", None), ("d.edf", "error", None)]:
        Grabacion.objects.create(lote=lote, nombre_original=nombre, estado=estado,
                                 resultado=resultado)
    r = client.get(reverse("grabaciones:csv_lote", args=[lote.pk]))
    assert r.status_code == 200
    assert r["Content-Disposition"] == (
        f'attachment; filename="eeg_lote_{lote.pk}_{lote.fecha:%Y-%m-%d}.csv"')
    tabla = leer(r.content)
    assert list(tabla["archivo"]) == ["ejemplo_OA.edf", "b.edf"]       # una fila por grabación
    assert list(tabla["electrodos_buenos"]) == [12, 13]
    assert list(tabla.columns) == [c.nombre for c in columnas()]       # mismas columnas que la individual


def test_sin_nada_que_exportar_no_hay_csv_vacio(client):
    g = grabacion_con(None, estado="en_cola")
    r = client.get(reverse("grabaciones:csv_grabacion", args=[g.pk]), follow=True)
    assert r.redirect_chain and "Solo se pueden exportar las grabaciones ya procesadas" in \
        r.content.decode()
    r = client.get(reverse("grabaciones:csv_lote", args=[g.lote_id]), follow=True)
    assert r.redirect_chain and "no tiene grabaciones procesadas que exportar" in \
        r.content.decode()


def test_exportar_algo_que_no_existe(client):
    assert client.get(reverse("grabaciones:csv_grabacion", args=[999])).status_code == 404
    assert client.get(reverse("grabaciones:csv_lote", args=[999])).status_code == 404


# ---------------------------------------------------------------------------
# Botones
# ---------------------------------------------------------------------------

def test_botones_en_la_lista(client):
    g = grabacion_con(FIXTURE)
    Grabacion.objects.create(lote=g.lote, nombre_original="x.edf", estado="en_cola")
    html = client.get("/grabaciones/").content.decode()
    # Botón compacto del lote: lleva el recuento de procesadas en su título.
    assert re.search(rf'href="{reverse("grabaciones:csv_lote", args=[g.lote_id])}" '
                     r'title="Descargar el CSV del lote \(1 procesadas\)">.*?CSV del lote</a>', html, re.S)
    assert html.count(">CSV</a>") == 1                    # solo la grabación procesada
    assert f'href="{reverse("grabaciones:csv_grabacion", args=[g.pk])}">CSV</a>' in html


def test_boton_del_lote_desactivado_sin_procesadas(client):
    grabacion_con(None, estado="en_cola")
    html = client.get("/grabaciones/").content.decode()
    assert "boton-desactivado" in html and "csv/" not in html


def test_boton_en_la_pantalla_de_analisis(client):
    g = grabacion_con(FIXTURE)
    html = client.get(reverse("grabaciones:analisis", args=[g.pk])).content.decode()
    assert reverse("grabaciones:csv_grabacion", args=[g.pk]) in html
    sin = grabacion_con(None, estado="en_cola")
    html = client.get(reverse("grabaciones:analisis", args=[sin.pk])).content.decode()
    assert "Descargar CSV" not in html


# ---------------------------------------------------------------------------
# De extremo a extremo con un EDF sintético
# ---------------------------------------------------------------------------

def test_csv_de_una_grabacion_procesada_de_verdad(client, tmp_path):
    from grabaciones import procesador
    from tests.test_procesador import EjecutorSincrono

    datos = {"referencia": "car_condicional", "banda": "1-30", "notch": "on",
             "archivos": [SimpleUploadedFile(
                 "sub-T1F001_task-OC.edf", escribir_edf(tmp_path / "a.edf", 30).read_bytes())]}
    client.post(reverse("grabaciones:subir"), datos)
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())

    g = Grabacion.objects.get()
    tabla = leer(client.get(reverse("grabaciones:csv_grabacion", args=[g.pk])).content)
    fila = tabla.iloc[0]
    assert fila["condicion"] == "OC" and fila["origen_condicion"] == "nombre"
    assert fila["electrodos_buenos"] == g.n_canales_buenos
    con_valor = [c for c in tabla.columns if c.startswith("rel_") and not pd.isna(fila[c])]
    assert len(con_valor) == g.n_canales_buenos * 4
    assert fila["referencia"] == "car_condicional" and fila["remuestreada"] == 0
