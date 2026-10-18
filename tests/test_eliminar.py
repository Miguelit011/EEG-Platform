"""Eliminar grabaciones y lotes de la plataforma: se borran el registro y la copia, nunca el original."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from grabaciones import procesador
from grabaciones.models import Grabacion, Lote
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB


@pytest.fixture(scope="module")
def bytes_edf(tmp_path_factory):
    return escribir_edf(tmp_path_factory.mktemp("edf") / "base.edf", duracion_s=15).read_bytes()


def subir(client, contenido, n=1):
    client.post(reverse("grabaciones:subir"), {
        "referencia": "car_condicional", "banda": "1-30", "notch": "on",
        "archivos": [SimpleUploadedFile(f"sub-T1F{i:03d}_task-OA.edf", contenido) for i in range(n)]})
    return Lote.objects.order_by("-pk").first()


def copia(grabacion):
    return Path(grabacion.archivo.path)


# ---------------------------------------------------------------------------
# Confirmación
# ---------------------------------------------------------------------------

def test_la_confirmacion_no_borra_nada_y_avisa_del_original(client, bytes_edf):
    g = subir(client, bytes_edf).grabaciones.get()
    respuesta = client.get(reverse("grabaciones:eliminar_grabacion", args=[g.pk]))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "No se toca el archivo original" in html and g.nombre_original in html
    assert Grabacion.objects.filter(pk=g.pk).exists() and copia(g).exists()


def test_la_confirmacion_del_lote_lista_sus_grabaciones(client, bytes_edf):
    lote = subir(client, bytes_edf, n=3)
    html = client.get(reverse("grabaciones:eliminar_lote", args=[lote.pk])).content.decode()
    assert f"lote {lote.pk}" in html and "3 grabaciones" in html
    assert Grabacion.objects.count() == 3


def test_ofrece_descargar_el_csv_antes_solo_si_hay_procesadas(client, bytes_edf):
    g = subir(client, bytes_edf).grabaciones.get()
    url = reverse("grabaciones:eliminar_grabacion", args=[g.pk])
    assert "Descargar el CSV antes" not in client.get(url).content.decode()
    Grabacion.objects.filter(pk=g.pk).update(estado=Grabacion.Estado.PROCESADA)
    assert "Descargar el CSV antes" in client.get(url).content.decode()


@pytest.mark.parametrize("nombre", ["eliminar_grabacion", "eliminar_lote"])
def test_eliminar_algo_que_no_existe_da_404(client, nombre):
    assert client.get(reverse(f"grabaciones:{nombre}", args=[999])).status_code == 404
    assert client.post(reverse(f"grabaciones:{nombre}", args=[999])).status_code == 404


# ---------------------------------------------------------------------------
# Eliminar una grabación
# ---------------------------------------------------------------------------

def test_eliminar_una_grabacion_borra_registro_y_copia_pero_no_las_demas(client, bytes_edf):
    lote = subir(client, bytes_edf, n=2)
    a, b = list(lote.grabaciones.order_by("pk"))
    ruta_a, ruta_b = copia(a), copia(b)
    respuesta = client.post(reverse("grabaciones:eliminar_grabacion", args=[a.pk]), follow=True)
    assert "Grabación eliminada de la plataforma" in respuesta.content.decode()
    assert not Grabacion.objects.filter(pk=a.pk).exists() and not ruta_a.exists()
    assert Grabacion.objects.filter(pk=b.pk).exists() and ruta_b.exists()
    assert Lote.objects.filter(pk=lote.pk).exists()       # el lote sigue mientras le queden grabaciones


def test_eliminar_la_ultima_grabacion_elimina_el_lote_y_su_carpeta(client, bytes_edf):
    lote = subir(client, bytes_edf)
    g = lote.grabaciones.get()
    carpeta = copia(g).parent
    client.post(reverse("grabaciones:eliminar_grabacion", args=[g.pk]))
    assert not Lote.objects.filter(pk=lote.pk).exists() and not carpeta.exists()


def test_una_grabacion_con_error_y_sin_archivo_se_elimina(client):
    lote = Lote.objects.create()
    g = Grabacion.objects.create(lote=lote, nombre_original="malo.edf", estado=Grabacion.Estado.ERROR,
                                 mensaje_error="No es un EDF")
    client.post(reverse("grabaciones:eliminar_grabacion", args=[g.pk]))
    assert not Grabacion.objects.filter(pk=g.pk).exists()


def test_solo_se_borra_con_post(client, bytes_edf):
    g = subir(client, bytes_edf).grabaciones.get()
    client.get(reverse("grabaciones:eliminar_grabacion", args=[g.pk]))
    assert Grabacion.objects.filter(pk=g.pk).exists() and copia(g).exists()


# ---------------------------------------------------------------------------
# Eliminar un lote
# ---------------------------------------------------------------------------

def test_eliminar_un_lote_borra_todas_sus_grabaciones_y_copias(client, bytes_edf):
    otro = subir(client, bytes_edf)
    lote = subir(client, bytes_edf, n=3)
    rutas = [copia(g) for g in lote.grabaciones.all()]
    ruta_otro = copia(otro.grabaciones.get())
    respuesta = client.post(reverse("grabaciones:eliminar_lote", args=[lote.pk]), follow=True)
    assert f"Lote {lote.pk} eliminado de la plataforma" in respuesta.content.decode()
    assert not Lote.objects.filter(pk=lote.pk).exists() and not Grabacion.objects.filter(lote_id=lote.pk).exists()
    assert not any(r.exists() for r in rutas)
    assert Lote.objects.filter(pk=otro.pk).exists() and ruta_otro.exists()


# ---------------------------------------------------------------------------
# Lo que se está procesando no se puede eliminar
# ---------------------------------------------------------------------------

def test_no_se_elimina_una_grabacion_que_se_esta_procesando(client, bytes_edf):
    g = subir(client, bytes_edf).grabaciones.get()
    Grabacion.objects.filter(pk=g.pk).update(estado=Grabacion.Estado.PROCESANDO)
    url = reverse("grabaciones:eliminar_grabacion", args=[g.pk])
    assert "se está procesando" in client.get(url).content.decode()
    respuesta = client.post(url)
    assert Grabacion.objects.filter(pk=g.pk).exists() and copia(g).exists()
    assert "No se puede eliminar mientras se procesa" in respuesta.content.decode()


def test_un_lote_con_una_grabacion_procesandose_no_se_elimina_entero(client, bytes_edf):
    lote = subir(client, bytes_edf, n=3)
    primera = lote.grabaciones.order_by("pk").first()
    Grabacion.objects.filter(pk=primera.pk).update(estado=Grabacion.Estado.PROCESANDO)
    client.post(reverse("grabaciones:eliminar_lote", args=[lote.pk]))
    assert Grabacion.objects.filter(lote=lote).count() == 3
    assert all(copia(g).exists() for g in lote.grabaciones.all())


def test_el_procesador_no_falla_si_eliminan_la_grabacion_mientras_se_procesa(client, bytes_edf):
    g = subir(client, bytes_edf).grabaciones.get()
    Grabacion.objects.filter(pk=g.pk).delete()
    procesador._guardar(g, {"ok": False, "mensaje": "x"})             # no lanza
    assert not Grabacion.objects.filter(pk=g.pk).exists()


def test_el_procesador_pasa_a_la_siguiente_si_eliminan_la_que_iba_a_reclamar(client, bytes_edf, monkeypatch):
    lote = subir(client, bytes_edf, n=2)
    primera, segunda = list(lote.grabaciones.order_by("pk"))
    for g in (primera, segunda):
        Grabacion.objects.filter(pk=g.pk).update(estado=Grabacion.Estado.EN_COLA)
    original = procesador._guardar_si_existe
    estado = {"borrada": False}

    def borrando_antes(grabacion, campos):
        if not estado["borrada"]:                  # justo después de elegirla, otro proceso la elimina
            estado["borrada"] = True
            Grabacion.objects.filter(pk=grabacion.pk).delete()
        return original(grabacion, campos)

    monkeypatch.setattr(procesador, "_guardar_si_existe", borrando_antes)
    reclamada = procesador._reclamar()
    assert reclamada is not None and reclamada.pk == segunda.pk
    assert Grabacion.objects.get(pk=segunda.pk).estado == Grabacion.Estado.PROCESANDO


# ---------------------------------------------------------------------------
# El original y lo que está fuera de la carpeta de datos no se tocan
# ---------------------------------------------------------------------------

def test_el_archivo_original_no_se_toca(client, bytes_edf, tmp_path):
    original = tmp_path / "originales" / "sub-T1F000_task-OA.edf"
    original.parent.mkdir()
    original.write_bytes(bytes_edf)
    client.post(reverse("grabaciones:subir"), {
        "referencia": "car_condicional", "banda": "1-30", "notch": "on",
        "archivos": [SimpleUploadedFile(original.name, original.read_bytes())]})
    g = Grabacion.objects.get()
    client.post(reverse("grabaciones:eliminar_grabacion", args=[g.pk]))
    assert not Grabacion.objects.exists()
    assert original.exists() and original.read_bytes() == bytes_edf


def test_un_archivo_fuera_de_la_carpeta_de_datos_no_se_borra(client, tmp_path):
    ajeno = tmp_path / "ajeno" / "importante.edf"
    ajeno.parent.mkdir()
    ajeno.write_bytes(b"no tocar")
    lote = Lote.objects.create()
    g = Grabacion.objects.create(lote=lote, nombre_original="x.edf", estado=Grabacion.Estado.ERROR)
    Grabacion.objects.filter(pk=g.pk).update(archivo=str(ajeno))       # ruta corrupta: absoluta y ajena
    respuesta = client.post(reverse("grabaciones:eliminar_grabacion", args=[g.pk]), follow=True)
    assert ajeno.exists() and ajeno.read_bytes() == b"no tocar"
    assert not Grabacion.objects.filter(pk=g.pk).exists()              # el registro sí se elimina
    assert "Una copia del EDF no se pudo borrar" in respuesta.content.decode()


# ---------------------------------------------------------------------------
# La lista ofrece la opción
# ---------------------------------------------------------------------------

def test_la_lista_ofrece_eliminar_en_cada_grabacion_y_en_cada_lote(client, bytes_edf):
    lote = subir(client, bytes_edf, n=2)
    primera, segunda = list(lote.grabaciones.order_by("pk"))
    Grabacion.objects.filter(pk=primera.pk).update(estado=Grabacion.Estado.PROCESADA)
    Grabacion.objects.filter(pk=segunda.pk).update(estado=Grabacion.Estado.PROCESANDO)
    html = client.get(reverse("grabaciones:lista")).content.decode()
    assert reverse("grabaciones:eliminar_lote", args=[lote.pk]) in html
    assert reverse("grabaciones:eliminar_grabacion", args=[primera.pk]) in html       # procesada
    assert reverse("grabaciones:eliminar_grabacion", args=[segunda.pk]) not in html   # procesando


def test_la_lista_ofrece_eliminar_en_las_grabaciones_en_cola_y_con_error(client, bytes_edf):
    lote = subir(client, bytes_edf)
    g = lote.grabaciones.get()
    for estado in (Grabacion.Estado.EN_COLA, Grabacion.Estado.ERROR):
        Grabacion.objects.filter(pk=g.pk).update(estado=estado)
        assert reverse("grabaciones:eliminar_grabacion", args=[g.pk]) in client.get(
            reverse("grabaciones:lista")).content.decode()
