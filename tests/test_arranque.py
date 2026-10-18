"""La web arranca y muestra la pantalla Grabaciones vacía, sin recursos externos."""

import re

from django.conf import settings
from django.urls import reverse

from tests.conftest import USA_LA_WEB

pytestmark = USA_LA_WEB


def test_grabaciones_vacia(client):
    respuesta = client.get(reverse("grabaciones:lista"))
    assert respuesta.status_code == 200
    nombres = [t.name for t in respuesta.templates]
    assert "base.html" in nombres and "grabaciones/lista.html" in nombres
    html = respuesta.content.decode()
    assert "<h1>Grabaciones</h1>" in html
    assert "Todavía no hay grabaciones." in html


def test_navegacion_a_las_tres_pantallas(client):
    html = client.get("/grabaciones/").content.decode()
    assert 'aria-current="page">Grabaciones' in html
    # Calidad, Análisis y Modelos son de una grabación, pero la barra siempre funciona: sin
    # ninguna procesada llevan a una pantalla que lo explica.
    for ruta, texto in (("/calidad/", "Calidad"), ("/analisis/", "Análisis"), ("/modelos/", "Modelos")):
        assert re.search(rf'<a href="{ruta}"\s*>{texto}</a>', html), texto
        assert "Todavía no hay ninguna grabación para ver" in client.get(ruta).content.decode()
    assert "desactivado" not in html.split("<main")[0]


def test_css_servido_desde_static(client):
    html = client.get("/grabaciones/").content.decode()
    assert '/static/css/estilos.css' in html


def test_plantillas_sin_recursos_externos():
    # Sin CDN: la web debe funcionar sin internet.
    externos = re.compile(r'(src|href)\s*=\s*["\'](https?:)?//', re.IGNORECASE)
    plantillas = list((settings.BASE_DIR / "templates").rglob("*.html"))
    assert plantillas
    for ruta in plantillas:
        assert not externos.search(ruta.read_text(encoding="utf-8")), ruta


def test_ningun_texto_menciona_fatiga(client):
    assert "fatiga" not in client.get("/").content.decode().lower()



def test_runserver_propio_y_estaticos_sin_cache():
    """Al actualizar, el navegador no debe mezclar una página nueva con CSS o JS antiguos."""
    from django.core.management import get_commands
    from django.test import RequestFactory

    from grabaciones.management.commands.runserver import Command, StaticFilesSinCache

    assert get_commands()["runserver"] == "grabaciones"     # el nuestro sustituye al de Django
    manejador = Command().get_handler(use_static_handler=True, insecure_serving=True)
    assert isinstance(manejador, StaticFilesSinCache)
    respuesta = manejador.get_response(RequestFactory().get("/static/css/estilos.css"))
    assert respuesta.status_code == 200 and respuesta["Cache-Control"] == "no-cache"
    respuesta.close()


def test_portada_en_la_raiz(client):
    respuesta = client.get("/")
    html = respuesta.content.decode()
    assert respuesta.status_code == 200 and "inicio.html" in [t.name for t in respuesta.templates]
    assert 'id="escena"' in html and 'models/electrodos.json' in html
    assert 'href="/grabaciones/"' in html
    assert "fatiga" not in html.lower()


def test_portada_respaldo_webp_claro_y_oscuro(client):
    """Sin WebGL o con movimiento reducido la portada muestra una imagen fija, en cada tema."""
    html = client.get("/").content.decode()
    for modo in ("claro", "oscuro"):
        assert f"img/portada-{modo}.webp" in html
        assert (settings.BASE_DIR / "static" / "img" / f"portada-{modo}.webp").stat().st_size > 1000
