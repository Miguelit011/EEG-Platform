"""
Pestaña «Modelos» y navegación por la grabación activa.

Calidad, Análisis y Modelos son pantallas de una grabación; la barra de navegación recuerda la
última abierta y lleva siempre a algún sitio, y la cabecera permite cambiar de grabación sin
salir de la pantalla.
"""

import re

import pytest
from django.urls import reverse
from eeg_library.modelado.prediccion import leer_ficha

from grabaciones import modelos
from grabaciones.models import Grabacion, Lote
from tests.auxiliar import FIXTURE, grabacion_con, variante
from tests.conftest import USA_LA_WEB

pytestmark = USA_LA_WEB

C1, C2, C3 = "c1_oa_oc_logistica", "c2_reposo_tarea_logistica", "c3_tareas_logistica"
SECCIONES = {"calidad": "grabaciones:calidad", "analisis": "grabaciones:analisis",
             "modelos": "grabaciones:modelos_grabacion"}


@pytest.fixture(autouse=True)
def _modelos_del_estudio(settings, tmp_path):
    settings.MODELOS = [C1, C2, C3]
    settings.MODELOS_DIR = tmp_path / "modelos"
    settings.MODELOS_DIR.mkdir()
    modelos.limpiar_cache()
    yield
    modelos.limpiar_cache()


def procesada(nombre="a_OA.edf", condicion="OA", resultado=FIXTURE, lote=None):
    lote = lote or Lote.objects.create()
    return Grabacion.objects.create(
        lote=lote, nombre_original=nombre, condicion=condicion, estado="procesada",
        duracion_s=137.0, sfreq_original_hz=256.0, resultado=resultado,
        n_canales_buenos=resultado["metadatos"]["n_canales_buenos"])


def coma(x, decimales=3):
    return f"{x:.{decimales}f}".replace(".", ",")


def pagina(client, ruta):
    respuesta = client.get(ruta)
    assert respuesta.status_code == 200
    return respuesta.content.decode()


# ---------------------------------------------------------------------------
# La grabación activa y la barra de navegación
# ---------------------------------------------------------------------------

def test_sin_grabaciones_las_pestanas_llevan_a_una_pantalla_que_lo_explica(client):
    for ruta in ("/calidad/", "/analisis/", "/modelos/"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200 and "Subir grabaciones" in respuesta.content.decode()


def test_las_pestanas_apuntan_a_la_ultima_grabacion_procesada_por_defecto(client):
    primera, ultima = procesada("uno_OA.edf"), procesada("dos_OA.edf")
    html = pagina(client, "/grabaciones/")
    for nombre in SECCIONES.values():
        assert f'href="{reverse(nombre, args=[ultima.pk])}"' in html
        assert f'href="{reverse(nombre, args=[primera.pk])}"' not in html.split("<main")[0]


def test_los_atajos_redirigen_a_la_grabacion_activa(client):
    g = procesada()
    for seccion, nombre in SECCIONES.items():
        respuesta = client.get(f"/{seccion}/")
        assert respuesta.status_code == 302 and respuesta.url == reverse(nombre, args=[g.pk])


def test_se_recuerda_la_ultima_grabacion_abierta_en_cualquier_pantalla(client):
    primera, ultima = procesada("uno_OA.edf"), procesada("dos_OA.edf")
    client.get(reverse("grabaciones:analisis", args=[primera.pk]))
    assert client.cookies["grabacion_activa"].value == str(primera.pk)
    html = pagina(client, "/grabaciones/")                                   # en la lista, la activa es la recordada
    assert f'href="{reverse("grabaciones:calidad", args=[primera.pk])}"' in html
    assert client.get("/modelos/").url == reverse("grabaciones:modelos_grabacion", args=[primera.pk])
    assert ultima.pk != primera.pk


def test_una_cookie_de_una_grabacion_que_ya_no_existe_no_rompe_nada(client):
    g = procesada()
    client.cookies["grabacion_activa"] = "99999"
    assert client.get("/analisis/").url == reverse("grabaciones:analisis", args=[g.pk])
    client.cookies["grabacion_activa"] = "no-es-un-numero"
    assert client.get("/analisis/").url == reverse("grabaciones:analisis", args=[g.pk])


def test_el_aria_current_marca_la_pestana(client):
    g = procesada()
    for seccion, nombre in SECCIONES.items():
        html = pagina(client, reverse(nombre, args=[g.pk]))
        etiqueta = {"calidad": "Calidad", "analisis": "Análisis", "modelos": "Modelos"}[seccion]
        assert f'aria-current="page">{etiqueta}</a>' in html


# ---------------------------------------------------------------------------
# El selector de grabación, anterior y siguiente
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seccion", list(SECCIONES))
def test_el_selector_lista_las_procesadas_por_lote_con_su_condicion_y_marca_la_actual(client, seccion):
    lote1, lote2 = Lote.objects.create(), Lote.objects.create()
    a, b = procesada("a_OA.edf", lote=lote1), procesada("b_OC.edf", "OC", lote=lote1)
    c = procesada("c_OA.edf", lote=lote2)
    Grabacion.objects.create(lote=lote2, nombre_original="en_cola.edf", estado="en_cola")
    html = pagina(client, reverse(SECCIONES[seccion], args=[b.pk]))
    barra = re.search(r'<div class="barra-grabacion".*?<span class="posicion', html, re.S).group(0)
    assert "<select" not in html and 'class="selector-grabacion"' in barra          # selector propio, no el del navegador
    assert barra.count('class="grupo-lote"') == 2 and "en_cola.edf" not in barra
    # Cada grabación es un enlace a esa misma sección; la actual va marcada.
    for g in (a, b, c):
        assert f'<a href="{reverse(SECCIONES[seccion], args=[g.pk])}" data-texto=' in barra
    assert re.search(rf'href="{reverse(SECCIONES[seccion], args=[b.pk])}"[^>]*aria-current="true"', barra)
    assert 'data-texto="b_oc.edf oc"' in barra and '<span class="chip">OC</span>' in barra
    assert barra.count('aria-current="true"') == 1
    assert 'rel="prev"' in barra and 'rel="next"' in barra and "2 de 3" in html
    assert 'type="search"' in barra and "hidden" in barra                             # el buscador lo activa el script


def test_en_la_primera_y_en_la_ultima_no_hay_anterior_ni_siguiente(client):
    a, b = procesada("a_OA.edf"), procesada("b_OA.edf")
    primera = pagina(client, reverse("grabaciones:analisis", args=[a.pk]))
    assert 'rel="prev"' not in primera and 'rel="next"' in primera
    ultima = pagina(client, reverse("grabaciones:analisis", args=[b.pk]))
    assert 'rel="prev"' in ultima and 'rel="next"' not in ultima


def test_el_selector_funciona_sin_javascript_y_con_el_script_en_static(client):
    """Es una lista de enlaces dentro de un <details>; el script solo añade buscador y teclado."""
    from django.contrib.staticfiles import finders
    g = procesada()
    html = pagina(client, reverse("grabaciones:analisis", args=[g.pk]))
    assert "<details" in html and "<summary" in html and "/static/js/barra.js" in html
    assert finders.find("js/barra.js")


def test_las_direcciones_del_selector_siguen_la_pantalla_en_la_que_se_esta(client):
    a, b = procesada("a_OA.edf"), procesada("b_OA.edf")
    for nombre in SECCIONES.values():
        html = pagina(client, reverse(nombre, args=[a.pk]))
        assert f'<a href="{reverse(nombre, args=[b.pk])}" data-texto=' in html


def test_la_lista_que_se_refresca_sola_no_calcula_la_navegacion(client):
    procesada()
    html = client.get(reverse("grabaciones:lista_parcial"), HTTP_X_REQUESTED_WITH="fetch").content.decode()
    assert "barra-grabacion" not in html and html.lstrip().startswith('<div id="lista-viva"')


# ---------------------------------------------------------------------------
# La pestaña Modelos de una grabación
# ---------------------------------------------------------------------------

def test_modelos_de_una_grabacion_con_su_resultado_en_el_test_y_el_azar(client):
    g = procesada()          # OA: c1 y c2 se aplican; c3 no
    html = pagina(client, reverse("grabaciones:modelos_grabacion", args=[g.pk]))
    assert modelos.AVISO_FIJO in html.replace("\n", " ") or "no miden" in html
    esperado = {t["id"]: t for t in modelos.aplicar(FIXTURE, "OA")["tarjetas"]}
    assert set(esperado) == {"c1_oa_oc_logistica", "c2_reposo_tarea_logistica"}
    for nombre in (C1, C2):
        ficha = leer_ficha(nombre)[0]
        test = ficha["resultado_test"]
        lo, hi = test["ic95"]
        assert ficha["titulo"] in html and esperado[ficha["id"]]["clase"] in html
        assert coma(test["valor"]) in html and f"{coma(lo)}–{coma(hi)}" in html
        assert f"azar {coma(test['azar'], 2)}" in html
    assert leer_ficha(C3)[0]["titulo"] not in html           # no se aplica a OA
    # La escala se dibuja con porcentajes enteros: un decimal con coma rompería el atributo style.
    for estilo in re.findall(r'style="([^"]*%[^"]*)"', html):
        assert re.fullmatch(r"(left|width): \d+%(; (left|width): \d+%)?", estilo), estilo


def test_las_cifras_de_la_escala_coinciden_con_la_ficha():
    for m in modelos.resumen_modelos():
        t = m["ficha"]["test"]
        ficha = leer_ficha(m["nombre"])[0]["resultado_test"]
        assert t["pos_valor"] == round(ficha["valor"] * 100)
        assert t["pos_azar"] == round(ficha["azar"] * 100)
        assert 0 <= t["pos_ic_desde"] <= t["pos_valor"] <= t["pos_ic_desde"] + t["pos_ic_ancho"] <= 100


def test_analisis_ya_no_lleva_el_bloque_de_modelos_pero_enlaza_a_su_pestana(client):
    g = procesada()
    html = pagina(client, reverse("grabaciones:analisis", args=[g.pk]))
    assert 'id="modelos"' not in html and "fatiga" not in html.lower()
    assert reverse("grabaciones:modelos_grabacion", args=[g.pk]) in html


def test_modelos_de_una_grabacion_sin_procesar_lo_explica(client):
    g = Grabacion.objects.create(lote=Lote.objects.create(), nombre_original="x.edf", estado="en_cola")
    html = pagina(client, reverse("grabaciones:modelos_grabacion", args=[g.pk]))
    assert "todavía no se ha procesado" in html and 'id="modelos"' not in html


def test_con_otros_parametros_los_modelos_no_predicen(client):
    g = procesada(resultado=variante(banda_hz=[3.0, 30.0]))
    assert "No disponible con estos parámetros" in pagina(
        client, reverse("grabaciones:modelos_grabacion", args=[g.pk]))


def test_un_modelo_roto_no_tumba_la_pestana(client, settings):
    settings.MODELOS = [C1, "no_existe.json"]
    modelos.limpiar_cache()
    g = procesada()
    html = pagina(client, reverse("grabaciones:modelos_grabacion", args=[g.pk]))
    assert "No se pudo cargar el modelo" in html and leer_ficha(C1)[0]["titulo"] in html


# ---------------------------------------------------------------------------
# Resumen de todas las grabaciones
# ---------------------------------------------------------------------------

def test_resumen_sin_grabaciones_lo_dice(client):
    html = pagina(client, reverse("grabaciones:modelos_resumen"))
    assert "Todavía no hay grabaciones procesadas." in html and "<table" not in html


def test_resumen_con_las_mismas_predicciones_que_la_pestana_de_cada_grabacion(client):
    g = procesada()
    html = pagina(client, reverse("grabaciones:modelos_resumen"))
    assert g.nombre_original in html and reverse("grabaciones:modelos_grabacion", args=[g.pk]) in html
    fila = re.search(r"<tbody>(.*?)</tbody>", html, re.S).group(1)
    for tarjeta in modelos.aplicar(FIXTURE, "OA")["tarjetas"]:
        assert tarjeta["clase"] in fila
    assert fila.count("coincide") >= 2 and "—" in fila        # c3 no se aplica a OA
    assert 'aria-current="page">Modelos</a>' in html


def test_resumen_con_otros_parametros(client):
    procesada(resultado=variante(banda_hz=[3.0, 30.0]))
    assert "no disponible con estos parámetros" in pagina(client, reverse("grabaciones:modelos_resumen"))


def test_resumen_muestra_solo_las_mas_recientes(client, monkeypatch):
    monkeypatch.setattr(modelos, "LIMITE_FILAS", 2)
    lote = Lote.objects.create()
    for i in range(3):
        procesada(f"g{i}_OA.edf", lote=lote)
    html = pagina(client, reverse("grabaciones:modelos_resumen"))
    assert html.count("_OA.edf") >= 2 and "g0_OA.edf</span></a></th>" not in html
    assert "Se muestran las 2 grabaciones procesadas más recientes de 3" in html
