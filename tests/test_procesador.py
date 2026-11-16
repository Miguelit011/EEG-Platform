"""Procesado en segundo plano: cola, worker, reanudación, reintentos y aviso en la lista."""

import inspect
import json
import multiprocessing
import os
import signal
import sys
import time
from concurrent.futures import Future
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from grabaciones import procesador
from grabaciones.management.commands import procesar as comando_procesar
from grabaciones.models import Grabacion, Lote, Procesador
from grabaciones.recursos import lanzador
from tests.conftest import USA_LA_WEB
from tests.edf_sinteticos import escribir_edf

pytestmark = USA_LA_WEB


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

class EjecutorSincrono:
    """Ejecuta cada trabajo en el momento, en este proceso: tests rápidos y sin spawn."""

    def __init__(self, interrumpir_en=None):
        self.interrumpir_en = interrumpir_en
        self.enviados = 0

    def __call__(self, max_workers):
        return self

    def submit(self, funcion, *args):
        self.enviados += 1
        if self.interrumpir_en is not None and self.enviados >= self.interrumpir_en:
            raise KeyboardInterrupt
        futuro = Future()
        futuro.set_result(funcion(*args))
        return futuro

    def shutdown(self, wait=True, cancel_futures=False):
        pass


@pytest.fixture(scope="module")
def bytes_edf(tmp_path_factory):
    return escribir_edf(tmp_path_factory.mktemp("edf") / "base.edf", duracion_s=30).read_bytes()


@pytest.fixture(scope="module")
def bytes_edf_corto(tmp_path_factory):
    # 15 s: lo mínimo que procesa la librería (14 s); acelera los lotes grandes.
    return escribir_edf(tmp_path_factory.mktemp("edf") / "corto.edf", duracion_s=15).read_bytes()


def subir(client, contenidos, **parametros):
    datos = {"referencia": "car_condicional", "banda": "1-30", "notch": "on", **parametros}
    datos = {k: v for k, v in datos.items() if v is not None}
    datos["archivos"] = [SimpleUploadedFile(f"sub-T1F{i:03d}_task-OA.edf", c)
                         for i, c in enumerate(contenidos)]
    client.post(reverse("grabaciones:subir"), datos)


def sin_fecha(resultado):
    resultado = json.loads(json.dumps(resultado))
    resultado["metadatos"].pop("fecha_analisis")
    return resultado


# ---------------------------------------------------------------------------
# Procesado
# ---------------------------------------------------------------------------

def test_procesa_un_edf_pequeno_y_guarda_el_contrato(client, bytes_edf):
    subir(client, [bytes_edf])
    hechas = procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    assert hechas == {"procesadas": 1, "con_error": 0}

    g = Grabacion.objects.get()
    assert g.estado == "procesada" and g.mensaje_error == ""
    r = g.resultado
    assert set(r) >= {"metadatos", "parametros_aplicados", "calidad", "potencia",
                      "caracteristicas"}
    assert len(r["caracteristicas"]) == 70
    assert set(r["calidad"]) >= {"AF3", "O1"} and len(r["calidad"]) == 14
    assert r["metadatos"]["resampleado"] is False
    # Se aplicaron los parámetros del lote.
    assert r["parametros_aplicados"]["referencia"] == "car_condicional"
    assert r["parametros_aplicados"]["banda_hz"] == [1.0, 30.0]
    assert r["parametros_aplicados"]["notch_hz"] == 50.0
    # JSON estricto y sin sugerir fatiga en ninguna clave ni valor.
    assert "fatiga" not in json.dumps(r, allow_nan=False).lower()


def test_se_aplican_los_parametros_del_lote(client, bytes_edf):
    subir(client, [bytes_edf], referencia="original", banda="3-30", notch=None)
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    aplicados = Grabacion.objects.get().resultado["parametros_aplicados"]
    assert aplicados["referencia"] == "original"
    assert aplicados["banda_hz"] == [3.0, 30.0] and aplicados["notch_hz"] is None


def test_un_error_no_detiene_el_resto(client, bytes_edf):
    subir(client, [bytes_edf, bytes_edf, bytes_edf])
    segunda = Grabacion.objects.order_by("id")[1]
    # Pasó la validación al subir, pero el archivo se estropea antes de procesarlo.
    with open(segunda.archivo.path, "wb") as f:
        f.write(b"datos estropeados")
    hechas = procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    assert hechas == {"procesadas": 2, "con_error": 1}
    estados = [g.estado for g in Grabacion.objects.order_by("id")]
    assert estados == ["procesada", "error", "procesada"]
    segunda.refresh_from_db()
    assert segunda.mensaje_error and segunda.resultado is None


def test_reanuda_lo_que_quedo_a_medias(client, bytes_edf):
    subir(client, [bytes_edf, bytes_edf])
    # El procesador murió con una grabación a medias.
    Grabacion.objects.filter(pk=Grabacion.objects.first().pk).update(estado="procesando")
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    assert set(Grabacion.objects.values_list("estado", flat=True)) == {"procesada"}


def test_parar_y_volver_a_lanzar_continua_donde_iba(client, bytes_edf_corto):
    subir(client, [bytes_edf_corto] * 4)
    # Se interrumpe (Ctrl+C) al repartir la tercera.
    with pytest.raises(KeyboardInterrupt):
        procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono(interrumpir_en=3))
    estados = list(Grabacion.objects.order_by("id").values_list("estado", flat=True))
    assert estados == ["procesada", "procesada", "en_cola", "en_cola"]
    primeros = [g.resultado for g in Grabacion.objects.order_by("id")[:2]]
    assert not Procesador.objects.exists()  # al parar, retira su señal

    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    assert set(Grabacion.objects.values_list("estado", flat=True)) == {"procesada"}
    # Las dos primeras no se repitieron.
    assert [g.resultado for g in Grabacion.objects.order_by("id")[:2]] == primeros


def test_no_se_lanzan_dos_procesadores(client):
    Procesador.objects.create(pid=999999, procesos=1, ultimo_latido=timezone.now())
    with pytest.raises(procesador.ProcesadorYaEnMarcha):
        procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())


def test_una_senal_caducada_no_bloquea(client, settings):
    Procesador.objects.create(
        pid=999999, procesos=1,
        ultimo_latido=timezone.now() - timedelta(seconds=settings.PROCESADOR_LATIDO_CADUCA_S + 5))
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    assert Procesador.activo() is None


# ---------------------------------------------------------------------------
# Windows, Linux y macOS: cómo se crean los hijos y cómo se para
# ---------------------------------------------------------------------------

class EjecutorQueNoTermina(EjecutorSincrono):
    """Cada análisis queda en curso para siempre, como un EDF largo a medio procesar."""

    def submit(self, funcion, *args):
        return Future()


def test_los_hijos_se_crean_con_spawn_en_todos_los_sistemas(monkeypatch):
    # En Linux el defecto sería fork, que copiaría Django y la conexión a SQLite en cada hijo.
    creados = []
    monkeypatch.setattr(procesador, "ProcessPoolExecutor", lambda **kw: creados.append(kw))
    procesador.ejecutor_spawn(3)
    assert creados[0]["max_workers"] == 3
    assert creados[0]["mp_context"].get_start_method() == "spawn"
    assert inspect.signature(procesador.trabajar).parameters["fabrica_ejecutor"].default \
        is procesador.ejecutor_spawn


def test_parar_a_mitad_de_un_archivo_termina_los_hijos(client, bytes_edf, monkeypatch):
    subir(client, [bytes_edf])
    terminados = []
    monkeypatch.setattr(procesador, "_terminar_hijos", lambda: terminados.append(True))

    def llega_ctrl_c(*args, **kwargs):   # la señal llega mientras se espera al análisis
        raise KeyboardInterrupt
    monkeypatch.setattr(procesador, "wait", llega_ctrl_c)

    with pytest.raises(KeyboardInterrupt):
        procesador.trabajar(1, fabrica_ejecutor=EjecutorQueNoTermina())
    assert terminados == [True]
    assert Grabacion.objects.get().estado == "en_cola"
    assert not Procesador.objects.exists()


def test_sin_nada_en_curso_no_se_termina_ningun_hijo(client, bytes_edf, monkeypatch):
    subir(client, [bytes_edf])
    monkeypatch.setattr(procesador, "_terminar_hijos", lambda: pytest.fail("nada que terminar"))
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())


def test_terminar_hijos_mata_los_procesos_de_analisis():
    hijo = multiprocessing.get_context("spawn").Process(target=time.sleep, args=(60,))
    hijo.start()
    procesador._terminar_hijos()
    hijo.join(timeout=30)
    assert not hijo.is_alive()


def test_la_senal_de_terminar_para_como_ctrl_c(monkeypatch, capsys):
    vistas = {}

    def trabajar(procesos, **kw):
        vistas.update({s: signal.getsignal(s) for s in comando_procesar.SENALES_DE_PARADA})
        comando_procesar.parar(signal.SIGTERM, None)   # lo que hace Python al recibirla
    monkeypatch.setattr("grabaciones.procesador.trabajar", trabajar)
    antes = {s: signal.getsignal(s) for s in comando_procesar.SENALES_DE_PARADA}

    call_command("procesar", "--procesos", "1")
    assert signal.SIGTERM in vistas and all(h is comando_procesar.parar for h in vistas.values())
    assert "Procesador detenido" in capsys.readouterr().out
    # Al acabar, las señales vuelven a como estaban.
    assert {s: signal.getsignal(s) for s in comando_procesar.SENALES_DE_PARADA} == antes


@pytest.mark.skipif(sys.platform == "win32", reason="señales POSIX: Linux y macOS")
@pytest.mark.parametrize("nombre", ["SIGTERM", "SIGHUP"])
def test_cerrar_la_terminal_para_el_procesador_en_orden(monkeypatch, capsys, nombre):
    def trabajar(procesos, **kw):
        os.kill(os.getpid(), getattr(signal, nombre))
        time.sleep(10)
        pytest.fail("la señal no paró el procesador")
    monkeypatch.setattr("grabaciones.procesador.trabajar", trabajar)
    call_command("procesar", "--procesos", "1")
    assert "Procesador detenido" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Paralelismo (procesos reales) y lote de 20
# ---------------------------------------------------------------------------

def test_mismo_resultado_con_1_y_con_varios_procesos(client, bytes_edf):
    subir(client, [bytes_edf, bytes_edf, bytes_edf])
    call_command("procesar", "--una-vez", "--procesos", "1")
    con_uno = [sin_fecha(g.resultado) for g in Grabacion.objects.order_by("id")]
    assert all(g.estado == "procesada" for g in Grabacion.objects.all())

    Grabacion.objects.update(estado="en_cola", resultado=None)
    call_command("procesar", "--una-vez", "--procesos", "2")
    con_dos = [sin_fecha(g.resultado) for g in Grabacion.objects.order_by("id")]
    assert con_dos == con_uno


def test_lote_de_veinte_se_procesa_entero(client, bytes_edf_corto):
    subir(client, [bytes_edf_corto] * 20)
    call_command("procesar", "--una-vez", "--procesos", "2")
    assert Grabacion.objects.filter(estado="procesada").count() == 20
    assert not Procesador.objects.exists()


# ---------------------------------------------------------------------------
# Reintentar y reprocesar
# ---------------------------------------------------------------------------

def test_reintentar_una_fallida(client, bytes_edf):
    subir(client, [bytes_edf])
    g = Grabacion.objects.get()
    Grabacion.objects.filter(pk=g.pk).update(estado="error", mensaje_error="fallo")
    client.post(reverse("grabaciones:encolar", args=[g.pk]))
    g.refresh_from_db()
    assert g.estado == "en_cola" and g.mensaje_error == ""


def test_reintentar_va_en_la_columna_de_acciones(client, bytes_edf):
    subir(client, [bytes_edf])
    g = Grabacion.objects.get()
    Grabacion.objects.filter(pk=g.pk).update(estado="error", mensaje_error="fallo")
    html = client.get("/grabaciones/").content.decode()
    fila = html[html.index('data-etiqueta="Estado"'):]
    assert ">Reintentar<" not in fila[:fila.index('data-etiqueta="Acciones"')]
    assert ">Reintentar<" in fila[fila.index('data-etiqueta="Acciones"'):]


def test_reprocesar_conserva_el_resultado_hasta_el_nuevo(client, bytes_edf):
    subir(client, [bytes_edf])
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    g = Grabacion.objects.get()
    anterior = g.resultado
    client.post(reverse("grabaciones:encolar", args=[g.pk]))
    g.refresh_from_db()
    assert g.estado == "en_cola" and g.resultado == anterior
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    g.refresh_from_db()
    assert g.estado == "procesada" and sin_fecha(g.resultado) == sin_fecha(anterior)


def test_no_se_reintenta_lo_rechazado_al_subir(client):
    subir(client, [b"esto no es un edf"])
    g = Grabacion.objects.get()
    assert g.estado == "error" and not g.reintentable
    client.post(reverse("grabaciones:encolar", args=[g.pk]))
    g.refresh_from_db()
    assert g.estado == "error"
    assert "Reintentar" not in client.get("/grabaciones/").content.decode()


def test_reintentar_las_fallidas_del_lote(client, bytes_edf):
    subir(client, [bytes_edf, bytes_edf, b"esto no es un edf"])
    validas = list(Grabacion.objects.exclude(archivo=""))
    Grabacion.objects.filter(pk=validas[0].pk).update(estado="error", mensaje_error="fallo")
    Grabacion.objects.filter(pk=validas[1].pk).update(estado="procesada")
    lote = Lote.objects.get()
    client.post(reverse("grabaciones:reintentar_lote", args=[lote.pk]))
    estados = {g.nombre_original: g.estado for g in Grabacion.objects.all()}
    assert estados["sub-T1F000_task-OA.edf"] == "en_cola"
    assert estados["sub-T1F001_task-OA.edf"] == "procesada"
    assert estados["sub-T1F002_task-OA.edf"] == "error"  # rechazada al subir: sin archivo


# ---------------------------------------------------------------------------
# Lista: progreso, aviso y actualización
# ---------------------------------------------------------------------------

def test_aviso_si_hay_cola_y_no_hay_procesador(client, bytes_edf):
    subir(client, [bytes_edf])
    html = client.get("/grabaciones/").content.decode()
    assert "el procesador no está en marcha" in html
    # Nombra el lanzador del sistema en que se usa (iniciar.bat en Windows) y no habla de terminales.
    assert lanzador() in html and "terminal" not in html


def test_sin_aviso_si_el_procesador_da_senales(client, bytes_edf):
    subir(client, [bytes_edf])
    Procesador.objects.create(pid=1234, procesos=3, ultimo_latido=timezone.now())
    html = client.get("/grabaciones/").content.decode()
    assert "no está en marcha" not in html
    assert "Procesando en segundo plano con 3 proceso(s)" in html


def test_aviso_si_las_senales_caducan(client, bytes_edf, settings):
    subir(client, [bytes_edf])
    Procesador.objects.create(
        pid=1234, procesos=3,
        ultimo_latido=timezone.now() - timedelta(seconds=settings.PROCESADOR_LATIDO_CADUCA_S + 1))
    assert "el procesador no está en marcha" in client.get("/grabaciones/").content.decode()


def test_sin_cola_no_hay_aviso(client, bytes_edf):
    subir(client, [bytes_edf])
    procesador.trabajar(1, una_vez=True, fabrica_ejecutor=EjecutorSincrono())
    html = client.get("/grabaciones/").content.decode()
    assert "no está en marcha" not in html and 'data-activo="0"' in html


def test_progreso_del_lote(client, bytes_edf):
    subir(client, [bytes_edf, bytes_edf, bytes_edf, b"esto no es un edf"])
    Grabacion.objects.filter(pk=Grabacion.objects.first().pk).update(estado="procesada")
    html = client.get("/grabaciones/").content.decode()
    assert "1 de 4 procesadas" in html and "1 con error" in html
    assert 'title="2 pendientes"' in html          # los pendientes van en el tooltip del contador, no en el texto
    assert Lote.objects.get().progreso == {
        "total": 4, "procesadas": 1, "con_error": 1, "pendientes": 2}


def test_lista_parcial_para_actualizar_sola(client, bytes_edf):
    subir(client, [bytes_edf])
    respuesta = client.get(reverse("grabaciones:lista_parcial"))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert html.lstrip().startswith('<div id="lista-viva"') and "<html" not in html
    assert 'data-activo="1"' in html and "sub-T1F000_task-OA.edf" in html
