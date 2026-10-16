import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from grabaciones.models import Grabacion, Lote
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB


@pytest.fixture(scope="module")
def bytes_edf(tmp_path_factory):
    return escribir_edf(tmp_path_factory.mktemp("edf") / "base.edf", duracion_s=25).read_bytes()


@pytest.fixture(scope="module")
def bytes_edf_128(tmp_path_factory):
    return escribir_edf(tmp_path_factory.mktemp("edf") / "128.edf", duracion_s=25,
                        sfreq=128).read_bytes()


def _subir(client, archivos, **parametros):
    datos = {"referencia": "car_condicional", "banda": "1-30", "notch": "on", **parametros}
    datos = {k: v for k, v in datos.items() if v is not None}
    datos["archivos"] = [SimpleUploadedFile(n, c) for n, c in archivos]
    return client.post(reverse("grabaciones:subir"), datos, follow=True)


def test_subir_un_archivo(client, bytes_edf, settings):
    respuesta = _subir(client, [("sub-C1F081_ses-M2_task-OA_eeg.edf", bytes_edf)])
    assert respuesta.status_code == 200
    g = Grabacion.objects.get()
    assert g.estado == Grabacion.Estado.EN_COLA
    assert g.condicion == "OA" and g.origen_condicion == "nombre"
    assert g.duracion_s == pytest.approx(25, abs=1)
    assert g.remuestreada is False
    assert g.resultado is None
    # El EDF se guarda en la carpeta de datos, no en el repo.
    assert settings.MEDIA_ROOT in __import__("pathlib").Path(g.archivo.path).parents
    html = respuesta.content.decode()
    assert "sub-C1F081_ses-M2_task-OA_eeg.edf" in html and "En cola" in html


def test_subir_veinte_de_golpe(client, bytes_edf):
    archivos = [(f"sub-C1F{i:03d}_ses-M2_task-OC_eeg.edf", bytes_edf) for i in range(20)]
    respuesta = _subir(client, archivos)
    assert Lote.objects.count() == 1
    assert Grabacion.objects.filter(estado="en_cola").count() == 20
    assert respuesta.content.decode().count("sub-C1F0") >= 20


def test_un_corrupto_solo_marca_ese_archivo(client, bytes_edf):
    archivos = [
        ("bueno_1_task-OA.edf", bytes_edf),
        ("roto_task-OC.edf", b"esto no es un edf"),
        ("bueno_2_task-STROOP.edf", bytes_edf),
    ]
    respuesta = _subir(client, archivos)
    estados = {g.nombre_original: g for g in Grabacion.objects.all()}
    assert estados["bueno_1_task-OA.edf"].estado == "en_cola"
    assert estados["bueno_2_task-STROOP.edf"].estado == "en_cola"
    roto = estados["roto_task-OC.edf"]
    assert roto.estado == "error" and "No se puede leer" in roto.mensaje_error
    assert not roto.archivo  # no se conserva un archivo inválido
    html = respuesta.content.decode()
    assert "No se puede leer" in html and "1 archivos con error" in html


def test_extension_que_no_es_edf(client, bytes_edf):
    _subir(client, [("notas.txt", b"hola")])
    g = Grabacion.objects.get()
    assert g.estado == "error" and "No es un archivo .edf" in g.mensaje_error


def test_128_hz_se_indica_en_la_lista(client, bytes_edf_128):
    respuesta = _subir(client, [("a_task-OA.edf", bytes_edf_128)])
    g = Grabacion.objects.get()
    assert g.estado == "en_cola" and g.remuestreada and g.sfreq_original_hz == 128
    assert "128 Hz → 256 Hz (remuestreada)" in respuesta.content.decode()


def test_sin_archivos_no_crea_lote(client):
    respuesta = _subir(client, [])
    assert Lote.objects.count() == 0
    assert "Elige al menos un archivo EDF" in respuesta.content.decode()


def test_parametros_por_defecto_son_los_del_estudio(client):
    html = client.get("/").content.decode()
    assert '<option value="car_condicional" selected>' in html
    assert '<option value="1-30" selected>' in html
    assert 'name="notch" id="id_notch" checked' in html


def test_parametros_del_lote(client, bytes_edf):
    _subir(client, [("a.edf", bytes_edf)], referencia="original", banda="3-30", notch=None)
    lote = Lote.objects.get()
    assert lote.parametros() == {"referencia": "original", "banda_hz": [3.0, 30.0],
                                 "notch_hz": None}
    assert not lote.con_parametros_del_estudio


def test_parametros_por_defecto_del_lote_coinciden_con_la_libreria():
    from eeg_library.procesado.parametros import normalizar_parametros
    assert Lote().parametros() == normalizar_parametros()
    assert Lote().con_parametros_del_estudio


def test_parametro_fuera_de_las_opciones_se_rechaza(client, bytes_edf):
    respuesta = _subir(client, [("a.edf", bytes_edf)], banda="5-40")
    assert Lote.objects.count() == 0 and Grabacion.objects.count() == 0
    assert respuesta.status_code == 200


def test_editar_condicion(client, bytes_edf):
    _subir(client, [("sin_condicion.edf", bytes_edf)])
    g = Grabacion.objects.get()
    assert g.condicion == "" and g.origen_condicion == "vacia"

    client.post(reverse("grabaciones:condicion", args=[g.pk]), {"condicion": " stroop "})
    g.refresh_from_db()
    assert g.condicion == "STROOP" and g.origen_condicion == "manual"

    client.post(reverse("grabaciones:condicion", args=[g.pk]), {"condicion": ""})
    g.refresh_from_db()
    assert g.condicion == "" and g.origen_condicion == "vacia"


def test_condicion_de_grabacion_inexistente(client):
    assert client.post(reverse("grabaciones:condicion", args=[999]),
                       {"condicion": "OA"}).status_code == 404

