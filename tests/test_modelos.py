"""Modelos enchufables: qué modelos se aplican a cada grabación y cómo se muestran y exportan."""

import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from eeg_library.modelado.prediccion import CLAVES_FICHA, leer_ficha
from eeg_library.procesado.parametros import PARAMETROS_ESTUDIO

from grabaciones import modelos
from grabaciones.exportacion import columnas, csv_de
from grabaciones.models import Grabacion
from tests.auxiliar import (FIXTURE, grabacion_con, sin_bloque_de_modelos,
                            variante)
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB

C1, C2, C3 = "c1_oa_oc_logistica", "c2_reposo_tarea_logistica", "c3_tareas_logistica"
COLUMNAS_70 = leer_ficha(C1)[0]["columnas"]
DOCS = Path(__file__).resolve().parents[1] / "docs"


@pytest.fixture(autouse=True)
def _modelos_limpios(settings, tmp_path):
    """Cada test parte de los tres modelos del estudio y de una carpeta de modelos vacía."""
    settings.MODELOS = [C1, C2, C3]
    settings.MODELOS_DIR = tmp_path / "modelos"
    settings.MODELOS_DIR.mkdir()
    modelos.limpiar_cache()
    yield
    modelos.limpiar_cache()


def crear_modelo_externo(carpeta, id="prueba_externo", condiciones=("OA",), clases=("alta", "baja"),
                         por_clase=True, columnas=None, sha=None, parametros=None):
    """Un modelo de juguete (Pipeline de scikit-learn) con su ficha, como lo dejaría un investigador."""
    columnas = list(columnas or COLUMNAS_70)
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(60, len(columnas))), columns=columnas)
    y = np.arange(60) % len(clases)
    pipeline = Pipeline([("imputar", SimpleImputer()), ("escalar", StandardScaler()),
                         ("modelo", LogisticRegression())]).fit(X, y)
    ruta = Path(carpeta) / f"{id}.joblib"
    joblib.dump(pipeline, ruta)
    ficha = {
        "id": id, "titulo": "Modelo de prueba", "archivo": ruta.name,
        "sha256_modelo": sha or hashlib.sha256(ruta.read_bytes()).hexdigest(),
        "que_predice": "Una prueba.",
        "clases": [{"codigo": i, "nombre": n} for i, n in enumerate(clases)],
        "condiciones_aplicables": list(condiciones),
        "parametros_validos": parametros or dict(PARAMETROS_ESTUDIO),
        "columnas": columnas,
        "resultado_test": {"metrica": "exactitud_balanceada", "valor": 0.7, "ic95": [0.6, 0.8],
                           "azar": 0.5, "n_grabaciones": 100, "n_personas": 10, "fuente": "prueba"},
        "entrenamiento": {"fecha": "2026-10-16", "variante": "regresión logística de prueba"},
        "avisos": ["Aviso de prueba del modelo."],
    }
    if por_clase:
        ficha["condiciones_por_clase"] = {clases[0]: list(condiciones), clases[1]: []} \
            if len(condiciones) else {c: [] for c in clases}
    (Path(carpeta) / f"{id}.json").write_text(json.dumps(ficha), encoding="utf-8")
    return ficha


def por_id(resultado):
    return {t["id"]: t for t in resultado["tarjetas"]}


# ---------------------------------------------------------------------------
# Qué modelos se aplican
# ---------------------------------------------------------------------------

def test_condicion_conocida_de_reposo():
    r = modelos.aplicar(FIXTURE, "OA")
    assert [t["id"] for t in r["tarjetas"]] == [C2, C1]
    assert all(t["origen"] == "conocida" and t["estado"] == "ok" for t in r["tarjetas"])
    assert por_id(r)[C1]["clase"] == "OA" and por_id(r)[C2]["clase"] == "reposo"
    assert r["mensajes"] == []


def test_condicion_conocida_de_tarea():
    r = modelos.aplicar(FIXTURE, "STROOP")
    assert [t["id"] for t in r["tarjetas"]] == [C2, C3]


def test_la_condicion_no_distingue_mayusculas():
    assert [t["id"] for t in modelos.aplicar(FIXTURE, "oa")["tarjetas"]] == [C2, C1]


def test_comparacion_con_la_condicion_usa_las_condiciones_por_clase():
    """En c2 las clases son reposo/tarea: OA corresponde a «reposo» según la ficha."""
    t = por_id(modelos.aplicar(FIXTURE, "OA"))[C2]
    assert t["comparacion"]["coincide"] and "Coincide con la condición del archivo (OA)" in \
        t["comparacion"]["texto"]


def test_discrepancia_con_alta_y_baja_confianza(settings):
    # El fixture es un reposo con ojos abiertos: etiquetado como STROOP, c2 y c3 discrepan.
    settings.UMBRAL_DISCREPANCIA = 0.8
    r = por_id(modelos.aplicar(FIXTURE, "STROOP"))
    c2 = r[C2]
    p = c2["probabilidades"][0]["p"] if c2["clase"] == "reposo" else None
    assert c2["comparacion"]["coincide"] is False
    assert c2["comparacion"]["alta_confianza"] == (max(x["p"] for x in c2["probabilidades"]) >= 0.8)
    assert "el modelo esperaba «tarea» y predice «reposo»" in c2["comparacion"]["texto"]

    settings.UMBRAL_DISCREPANCIA = 0.0
    assert por_id(modelos.aplicar(FIXTURE, "STROOP"))[C2]["comparacion"]["alta_confianza"] is True
    assert "conviene revisar la etiqueta" in \
        por_id(modelos.aplicar(FIXTURE, "STROOP"))[C2]["comparacion"]["texto"]
    settings.UMBRAL_DISCREPANCIA = 1.01
    c2 = por_id(modelos.aplicar(FIXTURE, "STROOP"))[C2]
    assert c2["comparacion"]["alta_confianza"] is False and "La confianza es baja" in \
        c2["comparacion"]["texto"]


def test_condicion_desconocida_c2_decide_reposo_o_tarea(monkeypatch):
    r = modelos.aplicar(FIXTURE, "")
    assert [(t["id"], t["origen"]) for t in r["tarjetas"]] == [(C2, "estimadora"), (C1, "estimada")]
    assert r["mensajes"] == ["Condición estimada por «Reposo / tarea»: reposo."]

    # Si c2 dijera «tarea», se mostraría c3 y no c1.
    real = modelos.predecir

    def falso(modelo, caracteristicas, parametros):
        p = real(modelo, caracteristicas, parametros)
        if modelo.id == C2:
            p = {**p, "clase": "tarea", "codigo": 1, "probabilidades": {"reposo": 0.1, "tarea": 0.9}}
        return p
    monkeypatch.setattr(modelos, "predecir", falso)
    r = modelos.aplicar(FIXTURE, "")
    assert [(t["id"], t["origen"]) for t in r["tarjetas"]] == [(C2, "estimadora"), (C3, "estimada")]
    assert r["mensajes"] == ["Condición estimada por «Reposo / tarea»: tarea."]
    assert all(t["comparacion"] is None for t in r["tarjetas"])    # sin etiqueta no se compara


def test_condicion_que_ningun_modelo_cubre():
    r = modelos.aplicar(FIXTURE, "XYZ")
    assert r["tarjetas"] == []
    assert r["mensajes"] == ["Ningún modelo registrado se aplica a la condición «XYZ»."]


def test_c3_muestra_las_cinco_probabilidades():
    c3 = por_id(modelos.aplicar(FIXTURE, "STROOP"))[C3]
    assert [p["nombre"] for p in c3["probabilidades"]] == ["STROOP", "PASAT", "PVTB", "MSIT", "PVSAT"]
    assert sum(p["p"] for p in c3["probabilidades"]) == pytest.approx(1.0)
    assert sum(p["ganadora"] for p in c3["probabilidades"]) == 1


# ---------------------------------------------------------------------------
# Parámetros distintos a los del entrenamiento
# ---------------------------------------------------------------------------

def test_con_otros_parametros_no_hay_predicciones():
    r = modelos.aplicar(variante(banda_hz=[3.0, 30.0]), "OA")
    for t in r["tarjetas"]:
        assert t["estado"] == "no_disponible" and t["clase"] is None and t["probabilidades"] == []
        assert t["motivo"] == "No disponible con estos parámetros de procesado."
        assert t["requeridos"] == "CAR condicional (la del estudio) · 1–30 Hz · con notch 50 Hz"


def test_con_otros_parametros_y_condicion_desconocida_no_se_estima_nada():
    r = modelos.aplicar(variante(banda_hz=[3.0, 30.0]), "")
    assert [(t["id"], t["estado"]) for t in r["tarjetas"]] == [(C2, "no_disponible")]
    assert any("No se puede estimar la condición" in m for m in r["mensajes"])


def test_pantalla_con_otros_parametros(client):
    g = grabacion_con(variante(banda_hz=[3.0, 30.0]))
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert html.count("No disponible con estos parámetros de procesado.") == 2
    assert "Predice:" not in html and "Este modelo solo es válido con" in html


# ---------------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------------

def test_bloque_de_modelos_en_la_pantalla(client):
    g = grabacion_con(FIXTURE)
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert '<section class="bloque-modelos" id="modelos"' in html
    assert modelos.AVISO_FIJO in html.replace("&quot;", '"')
    assert "Predice: <strong>OA</strong>" in html and "Predice: <strong>reposo</strong>" in html
    assert 'class="probabilidades"' in html and html.count('<span class="barra"') == 4
    # Ficha: resultado en el test independiente con su intervalo y el azar.
    assert "En un test independiente (28 personas, 207 grabaciones)" in html
    assert "exactitud balanceada 0,855" in html and "0,794–0,912" in html
    assert "Nivel de azar: 0,50" in html


def test_la_palabra_fatiga_solo_aparece_en_el_bloque_de_modelos(client):
    for condicion in ("OA", "STROOP", ""):
        g = grabacion_con(FIXTURE)
        g.condicion = condicion
        g.save()
        html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
        assert "fatiga" in html.lower()                      # el aviso fijo, dentro del bloque
        assert "fatiga" not in sin_bloque_de_modelos(html).lower()
    for url in ("/grabaciones/", reverse("grabaciones:calidad", args=[g.pk])):
        assert "fatiga" not in client.get(url).content.decode().lower()


def test_insignias_de_condicion_estimada(client):
    g = grabacion_con(FIXTURE)
    g.condicion = ""
    g.save()
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert "condición estimada</span>" in html and "estima la condición</span>" in html
    assert "Condición estimada por «Reposo / tarea»: reposo." in html
    # Con la condición conocida no hay insignias.
    g.condicion = "OA"
    g.save()
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert "insignia" not in re.search(r'id="modelos".*?</section>', html, re.S).group(0)


def test_aviso_de_discrepancia_en_pantalla(client):
    g = grabacion_con(FIXTURE)
    g.condicion = "PVTB"
    g.save()
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert "No coincide con la condición del archivo (PVTB)" in html


def test_sin_bloque_si_no_esta_procesada(client):
    g = grabacion_con(None, estado="en_cola")
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert 'id="modelos"' not in html


def test_cifras_de_la_pantalla_coinciden_con_resultados_json(client):
    """Las cifras que se muestran salen de las fichas, y estas de resultados.json del test."""
    datos = Path(os.environ.get("EEG_DATA", Path(__file__).resolve().parents[2] / "EEG-Data"))
    ruta = datos / "processed" / "test_20261007-133358" / "resultados.json"
    if not ruta.is_file():
        pytest.skip("no está EEG-Data (resultados.json del análisis confirmatorio)")
    resultados = json.loads(ruta.read_text(encoding="utf-8"))["familia_condicion"]
    claves = {C1: "C1_oa_oc", C2: "C2_reposo_tarea", C3: "C3_tareas"}
    for condicion in ("OA", "STROOP"):
        g = grabacion_con(FIXTURE)
        g.condicion = condicion
        g.save()
        html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
        for t in modelos.aplicar(FIXTURE, condicion)["tarjetas"]:
            esperado = resultados[claves[t["id"]]]
            logistica = esperado["modelos"]["logistica"]
            lo, hi = logistica["ic95"]
            f = lambda x, d=3: f"{x:.{d}f}".replace(".", ",")
            assert f"exactitud balanceada {f(logistica['exactitud_balanceada'])}" in html
            assert f"{f(lo)}–{f(hi)}" in html
            assert f"{esperado['n_personas']} personas, {esperado['n_grabaciones']} grabaciones" in html


# ---------------------------------------------------------------------------
# Añadir un modelo: solo su archivo y una línea en settings
# ---------------------------------------------------------------------------

def test_un_modelo_nuevo_aparece_en_la_pantalla_y_en_el_csv(client, settings):
    ficha = crear_modelo_externo(settings.MODELOS_DIR, condiciones=("OA",))
    g = grabacion_con(FIXTURE)
    otro = grabacion_con(variante())
    otro.condicion = "STROOP"
    otro.save()

    # Sin la línea en settings, no existe para la web.
    assert "Modelo de prueba" not in client.get(
        reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()

    settings.MODELOS = settings.MODELOS + ["prueba_externo.json"]          # la única línea
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert "Modelo de prueba" in html and "Aviso de prueba del modelo." in html
    assert "exactitud balanceada 0,700" in html and "0,600–0,800" in html

    nombres = [c.nombre for c in columnas()]
    # Las del modelo nuevo van tras las de los demás modelos y antes de las 6 de tiempo en tarea.
    assert nombres[-10:-6] == ["prueba_externo_clase", "prueba_externo_p_alta", "prueba_externo_p_baja",
                              "prueba_externo_condicion_estimada"]
    filas = list(csv.DictReader(io.StringIO(csv_de([g, otro]).decode("utf-8-sig")), delimiter=";"))
    esperado = modelos.aplicar(FIXTURE, "OA")["tarjetas"][-1]
    assert esperado["id"] == "prueba_externo"
    assert filas[0]["prueba_externo_clase"] == esperado["clase"]
    assert float(filas[0]["prueba_externo_p_alta"].replace(",", ".")) == pytest.approx(
        esperado["probabilidades"][0]["p"], abs=1e-6)
    assert filas[0]["prueba_externo_condicion_estimada"] == "0"
    # En una grabación de otra condición, el modelo no se aplica: celdas vacías.
    assert filas[1]["prueba_externo_clase"] == "" and filas[1]["prueba_externo_p_alta"] == ""
    assert filas[1]["prueba_externo_condicion_estimada"] == ""
    assert ficha["id"] == "prueba_externo"


def test_modelo_nuevo_con_clases_que_se_llaman_como_la_condicion(settings):
    """Sin `condiciones_por_clase`, la clase que se llama como la condición es la esperada."""
    crear_modelo_externo(settings.MODELOS_DIR, id="oa_oc_ext", condiciones=("OA", "OC"),
                         clases=("OA", "OC"), por_clase=False)
    settings.MODELOS = settings.MODELOS + ["oa_oc_ext.json"]
    t = por_id(modelos.aplicar(FIXTURE, "OC"))["oa_oc_ext"]
    assert t["comparacion"] is not None
    assert t["comparacion"]["coincide"] == (t["clase"] == "OC")


def test_el_modelo_nuevo_se_usa_sin_reprocesar(client, settings):
    """Se aplica sobre las características ya guardadas en el JSON de cada grabación."""
    g = grabacion_con(FIXTURE)
    guardado = Grabacion.objects.get(pk=g.pk).resultado
    crear_modelo_externo(settings.MODELOS_DIR)
    settings.MODELOS = settings.MODELOS + ["prueba_externo.json"]
    assert "Modelo de prueba" in client.get(
        reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert Grabacion.objects.get(pk=g.pk).resultado == guardado


def test_modelo_con_sha_incorrecto_no_tumba_la_pantalla(client, settings):
    crear_modelo_externo(settings.MODELOS_DIR, sha="0" * 64)
    settings.MODELOS = settings.MODELOS + ["prueba_externo.json"]
    g = grabacion_con(FIXTURE)
    respuesta = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk]))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "No se pudo cargar el modelo" in html and "SHA-256" in html
    assert "Predice: <strong>OA</strong>" in html                # los demás siguen funcionando
    # En el CSV el modelo roto deja sus celdas vacías y no impide exportar.
    assert csv_de([g]).startswith(b"\xef\xbb\xbf")


def test_modelo_que_no_existe(client, settings):
    settings.MODELOS = settings.MODELOS + ["no_existe.json"]
    g = grabacion_con(FIXTURE)
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert "No se pudo cargar el modelo" in html and "no_existe.json" in html


def test_modelo_que_necesita_caracteristicas_que_no_hay(client, settings):
    crear_modelo_externo(settings.MODELOS_DIR, columnas=COLUMNAS_70[:3] + ["otra_cosa"])
    settings.MODELOS = settings.MODELOS + ["prueba_externo.json"]
    t = por_id(modelos.aplicar(FIXTURE, "OA"))["prueba_externo"]
    assert t["estado"] == "error" and "otra_cosa" in t["motivo"]
    g = grabacion_con(FIXTURE)
    assert client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).status_code == 200


def test_los_modelos_se_cargan_una_vez(settings, monkeypatch):
    llamadas = []
    real = modelos.cargar_modelo
    monkeypatch.setattr(modelos, "cargar_modelo", lambda e: llamadas.append(e) or real(e))
    modelos.aplicar(FIXTURE, "OA")
    modelos.aplicar(FIXTURE, "OA")
    assert len(llamadas) == 3                        # c1, c2 y c3, una vez cada uno
    crear_modelo_externo(settings.MODELOS_DIR)
    settings.MODELOS = [C1, "prueba_externo.json"]
    modelos.aplicar(FIXTURE, "OA")
    modelos.aplicar(FIXTURE, "OA")
    assert len(llamadas) == 4                        # solo el nuevo; c1 ya estaba en memoria
    # Si cambia el archivo de un modelo, se recarga.
    crear_modelo_externo(settings.MODELOS_DIR, clases=("x", "y"))
    modelos.aplicar(FIXTURE, "OA")
    assert len(llamadas) == 5


def test_registrados_ignora_fichas_ilegibles(settings):
    (settings.MODELOS_DIR / "roto.json").write_text("{no es json", encoding="utf-8")
    settings.MODELOS = [C1, "roto.json", "falta.json"]
    assert [n for n, _ in modelos.registrados()] == [C1]


def test_texto_de_parametros():
    assert modelos.texto_parametros(PARAMETROS_ESTUDIO) == "CAR condicional (la del estudio) · 1–30 Hz · con notch 50 Hz"
    assert modelos.texto_parametros(
        {"referencia": "original", "banda_hz": [3, 30], "notch_hz": None}
    ) == "Original del casco, sin re-referenciar · 3–30 Hz · sin notch"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def leer_csv(contenido):
    return pd.read_csv(io.BytesIO(contenido), sep=";", decimal=",", encoding="utf-8-sig")


def test_columnas_de_modelos_en_el_csv():
    fila = leer_csv(csv_de([grabacion_con(FIXTURE)])).iloc[0]       # condición OA
    assert fila[f"{C1}_clase"] == "OA" and fila[f"{C2}_clase"] == "reposo"
    assert fila[f"{C1}_p_OA"] + fila[f"{C1}_p_OC"] == pytest.approx(1.0, abs=1e-5)
    assert fila[f"{C1}_condicion_estimada"] == 0 and fila[f"{C2}_condicion_estimada"] == 0
    # c3 no se aplica a OA: todo vacío.
    assert pd.isna(fila[f"{C3}_clase"]) and pd.isna(fila[f"{C3}_p_PVTB"])
    assert pd.isna(fila[f"{C3}_condicion_estimada"])


def test_csv_con_condicion_estimada():
    g = grabacion_con(FIXTURE)
    g.condicion = ""
    g.save()
    fila = leer_csv(csv_de([g])).iloc[0]
    assert fila[f"{C2}_clase"] == "reposo" and fila[f"{C2}_condicion_estimada"] == 1
    assert fila[f"{C1}_clase"] == "OA" and fila[f"{C1}_condicion_estimada"] == 1
    assert pd.isna(fila[f"{C3}_clase"])


def test_csv_con_otros_parametros_deja_los_modelos_vacios():
    fila = leer_csv(csv_de([grabacion_con(variante(banda_hz=[3.0, 30.0]))])).iloc[0]
    for c in columnas():
        if c.seccion == "Modelos":
            assert pd.isna(fila[c.nombre]), c.nombre


def test_las_columnas_de_modelos_estan_documentadas():
    texto = (DOCS / "COLUMNAS_CSV.md").read_text(encoding="utf-8")
    assert "## Modelos" in texto and f"`{C3}_p_PVSAT`" in texto
    for c in columnas():
        assert "fatiga" not in c.nombre.lower()
    cabecera, filas = csv_de([grabacion_con(FIXTURE)]).decode("utf-8").split("\r\n", 1)
    assert "fatiga" not in filas.lower()


# ---------------------------------------------------------------------------
# Comprobación de modelos y guía
# ---------------------------------------------------------------------------

def test_comprobar_modelos_con_los_del_estudio(capsys):
    call_command("comprobar_modelos")
    salida = capsys.readouterr().out
    assert salida.count("✔") == 3 and "Todos los modelos están bien." in salida


def test_comprobar_modelos_explica_los_fallos(capsys, settings):
    crear_modelo_externo(settings.MODELOS_DIR, sha="0" * 64)
    crear_modelo_externo(settings.MODELOS_DIR, id="raro", columnas=COLUMNAS_70[:3] + ["otra_cosa"])
    settings.MODELOS = settings.MODELOS + ["prueba_externo.json", "raro.json", "falta.json"]
    with pytest.raises(CommandError, match="3 modelo"):
        call_command("comprobar_modelos")
    salida = capsys.readouterr().out
    assert "SHA-256" in salida and "otra_cosa" in salida and "No se encuentra la ficha" in salida
    assert salida.count("✔") == 3


def test_la_guia_para_anadir_un_modelo():
    texto = (DOCS / "AÑADIR_UN_MODELO.md").read_text(encoding="utf-8")
    assert "MODELOS" in texto and "comprobar_modelos" in texto and "settings.py" in texto
    ejemplo = json.loads(re.search(r"```json\n(.*?)```", texto, re.S).group(1))
    assert all(clave in ejemplo for clave in CLAVES_FICHA)
    assert "condiciones_por_clase" in ejemplo and "resultado_test" in ejemplo


# ---------------------------------------------------------------------------
# De extremo a extremo con un EDF sintético
# ---------------------------------------------------------------------------

def test_modelos_sobre_una_grabacion_procesada_de_verdad(client, tmp_path):
    from grabaciones import procesador
    from tests.test_procesador import EjecutorSincrono

    datos = {"referencia": "car_condicional", "banda": "1-30", "notch": "on",
             "archivos": [SimpleUploadedFile(
                 "sub-T1F001_task-OC.edf", escribir_edf(tmp_path / "a.edf", 30).read_bytes())]}
    client.post(reverse("grabaciones:subir"), datos)
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    g = Grabacion.objects.get()
    html = client.get(reverse("grabaciones:modelos_grabacion", args=[g.pk])).content.decode()
    assert g.condicion == "OC" and "No se pudo" not in html
    assert html.count("Predice:") == 2                       # c1 y c2 para OC
    fila = leer_csv(client.get(reverse("grabaciones:csv_grabacion", args=[g.pk])).content).iloc[0]
    assert fila[f"{C1}_clase"] in ("OA", "OC") and fila[f"{C2}_clase"] in ("reposo", "tarea")
