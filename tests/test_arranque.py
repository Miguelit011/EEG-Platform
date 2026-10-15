"""La web arranca y muestra la pantalla Grabaciones vacía, sin recursos externos."""

import re

from django.conf import settings
from django.urls import reverse


def test_grabaciones_vacia(client):
    respuesta = client.get(reverse("grabaciones:lista"))
    assert respuesta.status_code == 200
    nombres = [t.name for t in respuesta.templates]
    assert "base.html" in nombres and "grabaciones/lista.html" in nombres
    html = respuesta.content.decode()
    assert "<h1>Grabaciones</h1>" in html
    assert "Todavía no hay grabaciones." in html


def test_navegacion_a_las_tres_pantallas(client):
    html = client.get("/").content.decode()
    assert 'aria-current="page">Grabaciones' in html
    # Calidad y Análisis son de una grabación: sin elegir una, desactivadas.
    assert re.search(r'class="desactivado"[^>]*>Calidad<', html)
    assert re.search(r'class="desactivado"[^>]*>Análisis<', html)


def test_css_servido_desde_static(client):
    html = client.get("/").content.decode()
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
