"""Pantalla de análisis: potencia por banda, zona y electrodo, a partir del JSON guardado."""

import copy
import json
import re

import pytest
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.procesado.matrix import REGIONES

from grabaciones.analisis_espectral import (
    ESCALA, color_de_escala, color_de_texto, resumen_analisis)
from grabaciones.models import Grabacion
from tests.auxiliar import FIXTURE, grabacion_con, mapa, mapas, sin_bloque_de_modelos, variante
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB

BANDAS = ["delta", "theta", "alfa", "beta"]
DESCARTADOS_FIXTURE = {"F7", "F3"}


def url(g):
    return reverse("grabaciones:analisis", args=[g.pk])


def contraste(a, b):
    """Contraste WCAG entre dos colores #rrggbb, calculado aquí de forma independiente."""
    def lum(h):
        v = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    claro, oscuro = sorted((lum(a), lum(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


# ---------------------------------------------------------------------------
# Datos de la pantalla (función pura)
# ---------------------------------------------------------------------------

def test_con_el_fixture():
    r = resumen_analisis(FIXTURE)
    assert [b["clave"] for b in r["bandas"]] == BANDAS
    assert [b["nombre"] for b in r["bandas"]] == ["Delta", "Theta", "Alfa", "Beta"]
    assert r["bandas"][0]["rango"] == "1–4 Hz" and r["bandas"][3]["rango"] == "13–30 Hz"
    assert r["n_validos"] == 12 and r["n_total"] == 14
    assert [e["canal"] for e in r["electrodos"]] == CANALES_EPOC
    assert [z["clave"] for z in r["zonas"]] == list(REGIONES)
    assert r["banda_inicial"] == "alfa" and r["avisos"] == []


def test_los_valores_son_los_de_la_libreria():
    r = resumen_analisis(FIXTURE)
    por_canal = FIXTURE["potencia"]["por_canal"]
    for e in r["electrodos"]:
        if e["valido"]:
            for b in BANDAS:
                assert e["relativa"][b] == por_canal[e["canal"]][b]["relativa"]
    por_region = FIXTURE["potencia"]["por_region"]
    for z in r["zonas"]:
        assert z["n_validos"] == por_region[z["clave"]]["n_canales_validos"]
        for b in BANDAS:
            assert z["relativa"][b] == por_region[z["clave"]][b]["relativa"]
            assert z["log_abs"][b] == por_region[z["clave"]][b]["log10_absoluta_v2"]


def test_toda_la_cabeza_es_la_media_de_los_electrodos_validos():
    r = resumen_analisis(FIXTURE)
    por_canal = FIXTURE["potencia"]["por_canal"]
    validos = [c for c in CANALES_EPOC if c not in DESCARTADOS_FIXTURE]
    for b in BANDAS:
        esperado = sum(por_canal[c][b]["relativa"] for c in validos) / len(validos)
        assert r["cabeza"][b] == pytest.approx(esperado)
        # Con los descartados la media sería otra: no cuentan.
        con_todos = sum(por_canal[c][b]["relativa"] for c in CANALES_EPOC) / 14
        assert r["cabeza"][b] != pytest.approx(con_todos)


def test_los_descartados_no_tienen_dato():
    r = resumen_analisis(FIXTURE)
    for e in r["electrodos"]:
        if e["canal"] in DESCARTADOS_FIXTURE:
            assert not e["valido"]
            assert all(v is None for v in e["relativa"].values())
            assert all(v is None for v in e["log_abs"].values())
            assert e["rel_texto"] == ["—"] * 4


def test_textos_con_coma_decimal():
    r = resumen_analisis(FIXTURE)
    assert r["zonas"][0]["rel_texto"] == ["47,4", "19,8", "22,7", "10,1"]
    assert all("." not in t for t in r["cabeza_texto"])


def test_datos_de_la_grafica():
    g = resumen_analisis(FIXTURE)["grafica"]
    assert g["bandas"] == ["Delta", "Theta", "Alfa", "Beta"]
    assert [s["etiqueta"] for s in g["series"]][1:] == [z.capitalize() for z in REGIONES]
    assert g["series"][0]["etiqueta"].startswith("Toda la cabeza")
    # En porcentaje, con la relativa de la librería (zona frontal del fixture).
    assert g["series"][1]["valores"] == [47.38, 19.8, 22.73, 10.09]
    assert len({s["color"] for s in g["series"]}) == 5   # colores distintos


def test_mapa_de_cada_banda_y_escala():
    r = resumen_analisis(FIXTURE)
    assert [m["banda"]["clave"] for m in r["mapas"]] == BANDAS
    por_canal = FIXTURE["potencia"]["por_canal"]
    for m in r["mapas"]:
        b = m["banda"]["clave"]
        validos = {p["canal"]: por_canal[p["canal"]][b]["relativa"]
                   for p in m["puntos"] if p["clase"] == "valor"}
        assert len(validos) == 12
        # La escala va del mínimo al máximo de esta banda.
        assert m["minimo"] == f"{min(validos.values()) * 100:.1f}".replace(".", ",")
        assert m["maximo"] == f"{max(validos.values()) * 100:.1f}".replace(".", ",")
        por_punto = {p["canal"]: p for p in m["puntos"]}
        assert por_punto[min(validos, key=validos.get)]["relleno"] == ESCALA[0]
        assert por_punto[max(validos, key=validos.get)]["relleno"] == ESCALA[-1]
        # Valor escrito en cada círculo y legible sobre su color.
        for canal, valor in validos.items():
            p = por_punto[canal]
            assert p["simbolo"] == f"{valor * 100:.1f}".replace(".", ",")
            assert contraste(p["relleno"], p["texto_color"]) >= 4.5, (b, canal)


def test_electrodo_descartado_en_el_mapa():
    for m in resumen_analisis(FIXTURE)["mapas"]:
        for p in m["puntos"]:
            if p["canal"] in DESCARTADOS_FIXTURE:
                assert (p["forma"], p["clase"], p["simbolo"]) == ("cruz", "descartado", "")
                assert "relleno" not in p and p["titulo"] == f"{p['canal']}: descartado, sin dato"


def test_valores_iguales_no_dividen_por_cero():
    r = copy.deepcopy(FIXTURE)
    for canal in CANALES_EPOC:
        r["potencia"]["por_canal"][canal]["alfa"]["relativa"] = 0.25
    m = next(m for m in resumen_analisis(r)["mapas"] if m["banda"]["clave"] == "alfa")
    assert m["minimo"] == m["maximo"] == "25,0"
    assert {p["relleno"] for p in m["puntos"] if p["clase"] == "valor"} == {color_de_escala(0.5)}


def test_escala_de_color_y_texto():
    assert color_de_escala(0) == ESCALA[0] and color_de_escala(1) == ESCALA[-1]
    assert color_de_escala(-3) == ESCALA[0] and color_de_escala(7) == ESCALA[-1]
    assert color_de_texto("#440154") == "#ffffff" and color_de_texto("#fde725") == "#000000"
    for t in [i / 40 for i in range(41)]:
        fondo = color_de_escala(t)
        assert contraste(fondo, color_de_texto(fondo)) >= 4.5, t


def test_zona_sin_electrodos_validos():
    r = resumen_analisis(variante(["P7", "P8", "O1", "O2"]))
    posterior = next(z for z in r["zonas"] if z["clave"] == "posterior")
    assert posterior["n_validos"] == 0 and posterior["rel_texto"] == ["—"] * 4
    assert posterior["abs_texto"] == ["—"] * 4
    assert any("Sin electrodos válidos en: Posterior" in a["texto"] for a in r["avisos"])
    # En la gráfica queda como sin dato, no como cero.
    assert next(s for s in r["grafica"]["series"] if s["etiqueta"] == "Posterior")["valores"] \
        == [None] * 4


def test_aviso_del_paso_banda_3_30():
    r = resumen_analisis(variante(banda_hz=[3.0, 30.0]))
    textos = [a["texto"] for a in r["avisos"]]
    assert any("empieza en 3 Hz" in t and "delta" in t and "casi eliminada" in t for t in textos)
    assert resumen_analisis(variante(banda_hz=[1.0, 30.0]))["avisos"] == []


def test_aviso_con_pocos_electrodos_buenos():
    r = resumen_analisis(variante(CANALES_EPOC[5:], car=False))
    assert r["avisos"][0] == {
        "nivel": "critico",
        "texto": "Solo 5 electrodos buenos: resultados no fiables (mínimo recomendado: 6)."}


def test_resumen_sin_potencia():
    assert resumen_analisis(None) is None and resumen_analisis({}) is None
    assert resumen_analisis({"potencia": {"por_canal": {}}}) is None


# ---------------------------------------------------------------------------
# Vista
# ---------------------------------------------------------------------------

def test_pantalla_con_el_fixture(client):
    respuesta = client.get(url(grabacion_con(FIXTURE)))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Análisis espectral" in html and "ejemplo_OA.edf" in html
    assert "Toda la cabeza" in html and "12 de 14" in html
    # Tabla zona × banda con los valores de la librería.
    assert re.search(r"<th scope=\"row\">Frontal</th>\s*<td>4 de 6</td>\s*"
                     r"<td class=\"num\">47,4</td>\s*<td class=\"num\">19,8</td>", html)
    for b in ("Delta", "Theta", "Alfa", "Beta"):
        assert f"{b} <span" in html
    assert "no fiables" not in html and "casi eliminada" not in html


def test_grafica_con_chart_js_local(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    assert '<canvas id="grafica-bandas"' in html and 'aria-label="Gráfica de barras' in html
    datos = json.loads(re.search(
        r'<script id="datos-grafica" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert datos["bandas"] == ["Delta", "Theta", "Alfa", "Beta"] and len(datos["series"]) == 5
    assert '/static/vendor/chart.umd.js' in html and '/static/js/analisis.js' in html
    # Chart.js se sirve desde static/, con su licencia: la web funciona sin internet.
    assert finders.find("vendor/chart.umd.js") and finders.find("vendor/chart.LICENSE.md")
    assert finders.find("js/analisis.js")


def test_visor_recibe_los_datos_de_la_libreria(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    datos = json.loads(re.search(
        r'<script id="datos-visor" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert [b["clave"] for b in datos["bandas"]] == BANDAS and datos["banda_inicial"] == "alfa"
    assert len(datos["electrodos"]) == 14 and len(datos["geometria"]["canales"]) == 14
    por_canal = {e["canal"]: e for e in datos["electrodos"]}
    for canal in DESCARTADOS_FIXTURE:       # un descartado no lleva valor en ninguna banda
        assert not por_canal[canal]["valido"]
        assert all(v is None for v in por_canal[canal]["rel"].values())
        assert all(v is None for v in por_canal[canal]["log_abs"].values())
    assert por_canal["AF3"]["valido"] and abs(por_canal["AF3"]["rel"]["alfa"] - 0.287) < 0.0005


def test_visor_sin_cdn_y_con_respaldo_sin_js(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    assert '<script type="importmap">' in html and "/static/vendor/three/three.module.min.js" in html
    assert 'type="module" src="/static/js/visor.js"' in html
    assert "http://" not in html and "https://" not in html.replace("https://claude.com", "")
    for ruta in ("models/cabeza.bin", "models/cerebro.bin", "models/electrodos.json", "models/LEEME.txt",
                 "models/LICENCIA-FreeSurfer.txt", "models/LICENCIA-MNE-BSD3.txt", "models/LICENCIA-nilearn-BSD3.txt",
                 "vendor/three/three.module.min.js", "vendor/three/controls/OrbitControls.js",
                 "vendor/three/LICENCIA-three-MIT.txt", "js/visor.js", "js/visor3d.js",
                 "js/visor-comun.js", "fonts/plex-sans-latin-400.woff2",
                 "fonts/plex-sans-latin-700.woff2", "fonts/plex-mono-latin-400.woff2",
                 "fonts/plex-mono-latin-700.woff2", "fonts/LICENCIA-IBMPlex-OFL.txt"):
        assert finders.find(ruta), ruta
    # Sin JavaScript quedan los cuatro mapas con el valor de cada sensor.
    assert "<noscript>" in html and len(mapas(html)) == 4


def test_el_visor_avisa_de_que_es_orientativo(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    assert "Interpolación orientativa" in html
    assert "no se puede localizar la actividad dentro del cerebro" in html
    assert "fatiga" not in html.split('id="modelos"')[0].lower()


def test_mapas_con_valores_y_descartados(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    for svg in mapas(html):
        assert svg.count("<circle cx=") == 12 and svg.count("cruz-raya") == 4   # 2 descartados, 2 rayas cada uno
        assert svg.count('style="fill: #') >= 12            # círculos coloreados por potencia
        for canal in DESCARTADOS_FIXTURE:
            assert f"<title>{canal}: descartado, sin dato</title>" in svg
    assert "<title>AF3: 28,7 % de la potencia (alfa)</title>" in html
    # Leyenda con la escala de cada banda, y la aclaración de que no hay interpolación.
    assert html.count('class="barra-escala"') == 4
    assert "17,4 %" in html and "49,4 %" in html
    assert "sin interpolar" in html


def test_los_descartados_no_aparecen_en_las_tablas_con_valor(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    assert html.count("</svg> Descartado: sin dato") == 4        # F7 y F3, en dos tablas por electrodo
    assert "Potencia relativa por electrodo" in html
    assert "Potencia absoluta por zona" in html and "Potencia absoluta por electrodo" in html


def test_sin_descartados_no_hay_cruces(client):
    html = client.get(url(grabacion_con(variante()))).content.decode()
    assert all("cruz-raya" not in svg for svg in mapas(html))
    assert "14 de 14" in html


def test_avisos_en_la_pantalla(client):
    html = client.get(url(grabacion_con(variante(
        CANALES_EPOC[5:], car=False, banda_hz=[3.0, 30.0])))).content.decode()
    assert "resultados no fiables" in html and "casi eliminada por el propio filtro" in html
    assert "Sin electrodos válidos en" in html


def test_zona_sin_validos_en_la_tabla(client):
    html = client.get(url(grabacion_con(variante(["T7", "T8"])))).content.decode()
    assert re.search(r'<th scope="row">Temporal</th>\s*<td>0 de 2</td>\s*'
                     r'<td class="num">—</td>', html)


def test_svg_sin_decimales_con_coma(client):
    html = client.get(url(grabacion_con(FIXTURE))).content.decode()
    for svg in mapas(html):
        assert not re.search(r'\b(cx|cy|x|y)="[^"]*,', svg)


@pytest.mark.parametrize("estado, texto", [
    ("en_cola", "todavía no se ha procesado (en cola)"),
    ("procesando", "todavía no se ha procesado (procesando)"),
    ("error", "no se pudo procesar"),
])
def test_grabacion_sin_procesar(client, estado, texto):
    g = grabacion_con(None, estado=estado)
    g.mensaje_error = "fallo de prueba"
    g.save()
    respuesta = client.get(url(g))
    assert respuesta.status_code == 200 and texto in respuesta.content.decode()
    assert "chart.umd.js" not in respuesta.content.decode()


def test_grabacion_inexistente(client):
    assert client.get(reverse("grabaciones:analisis", args=[999])).status_code == 404


def test_navegacion_y_enlaces(client):
    g = grabacion_con(FIXTURE)
    html = client.get(url(g)).content.decode()
    assert re.search(r'<a href="[^"]+analisis/"\s+aria-current="page">Análisis', html)
    assert reverse("grabaciones:calidad", args=[g.pk]) in html
    lista = client.get("/").content.decode()
    assert f'href="{url(g)}">Análisis</a>' in lista


def test_sin_recursos_externos_ni_fatiga(client):
    for resultado in (FIXTURE, variante(), variante(CANALES_EPOC[5:], car=False)):
        html = client.get(url(grabacion_con(resultado))).content.decode()
        assert not re.search(r'(src|href)\s*=\s*["\'](https?:)?//', html, re.I)
        assert "fatiga" not in sin_bloque_de_modelos(html).lower()


def test_grabacion_procesada_de_verdad(client, tmp_path):
    from grabaciones import procesador
    from tests.test_procesador import EjecutorSincrono

    datos = {"referencia": "car_condicional", "banda": "3-30", "notch": "on",
             "archivos": [SimpleUploadedFile(
                 "sub-T1F001_task-OC.edf", escribir_edf(tmp_path / "a.edf", 30).read_bytes())]}
    client.post(reverse("grabaciones:subir"), datos)
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())

    g = Grabacion.objects.get()
    html = client.get(url(g)).content.decode()
    assert len(mapas(html)) == 4 and "casi eliminada" in html     # banda 3–30 Hz
    # Cada electrodo válido lleva su valor en cada mapa.
    n = g.n_canales_buenos
    assert all(svg.count("<circle cx=") == n for svg in mapas(html))
