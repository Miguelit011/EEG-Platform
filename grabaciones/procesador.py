"""
Procesado en segundo plano: la cola es la propia base de datos.

Un único procesador (`manage.py procesar`) reparte las grabaciones en cola entre
N procesos. Solo este proceso toca la base de datos; los hijos reciben una ruta
y unos parámetros y devuelven el resultado (ver `analisis.py`). Con N = 1 o
N > 1 el resultado de cada grabación es el mismo.
"""

import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool

from django.utils import timezone

from grabaciones.analisis import analizar
from grabaciones.models import Grabacion, Procesador

PERIODO_LATIDO_S = 2.0


class ProcesadorYaEnMarcha(Exception):
    pass


def recuperar_interrumpidas():
    """Las que se estaban procesando cuando el procesador se paró vuelven a la cola."""
    return Grabacion.objects.filter(estado=Grabacion.Estado.PROCESANDO).update(
        estado=Grabacion.Estado.EN_COLA)


def dar_senal(procesos):
    Procesador.objects.update_or_create(
        pk=1, defaults={"pid": os.getpid(), "procesos": procesos,
                        "ultimo_latido": timezone.now()})


def quitar_senal():
    Procesador.objects.filter(pk=1, pid=os.getpid()).delete()


def comprobar_que_no_hay_otro():
    otro = Procesador.activo()
    if otro is not None and otro.pid != os.getpid():
        raise ProcesadorYaEnMarcha(
            f"Ya hay un procesador en marcha (proceso {otro.pid}). Si lo cerraste "
            f"a la fuerza, espera unos segundos y vuelve a intentarlo.")


def _reclamar():
    """Toma la siguiente grabación en cola y la marca como en proceso."""
    grabacion = (Grabacion.objects.filter(estado=Grabacion.Estado.EN_COLA)
                 .select_related("lote").order_by("id").first())
    if grabacion is not None:
        grabacion.estado = Grabacion.Estado.PROCESANDO
        grabacion.mensaje_error = ""
        grabacion.save(update_fields=["estado", "mensaje_error"])
    return grabacion


def _guardar(grabacion, salida):
    if salida["ok"]:
        grabacion.resultado = salida["resultado"]
        grabacion.estado = Grabacion.Estado.PROCESADA
        grabacion.mensaje_error = ""
    else:
        grabacion.estado = Grabacion.Estado.ERROR
        grabacion.mensaje_error = salida["mensaje"]
    grabacion.save(update_fields=["resultado", "estado", "mensaje_error"])


def _marcar_error_si_sigue_procesando(grabacion, mensaje):
    grabacion.refresh_from_db(fields=["estado"])
    if grabacion.estado == Grabacion.Estado.PROCESANDO:
        _guardar(grabacion, {"ok": False, "mensaje": mensaje})


def trabajar(procesos, una_vez=False, espera_s=2.0, informar=lambda texto: None,
             fabrica_ejecutor=ProcessPoolExecutor):
    """
    Procesa la cola con `procesos` procesos hasta que se interrumpe.

    Con `una_vez=True` termina cuando la cola se vacía. Devuelve cuántas
    grabaciones procesó con éxito y cuántas con error.
    """
    comprobar_que_no_hay_otro()
    recuperadas = recuperar_interrumpidas()
    if recuperadas:
        informar(f"{recuperadas} grabaciones que se estaban procesando vuelven a la cola.")

    hechas = {"procesadas": 0, "con_error": 0}
    en_vuelo = {}  # futuro -> grabación
    ejecutor = fabrica_ejecutor(max_workers=procesos)
    ultimo_latido = 0.0
    try:
        while True:
            if time.monotonic() - ultimo_latido >= PERIODO_LATIDO_S:
                dar_senal(procesos)
                ultimo_latido = time.monotonic()

            while len(en_vuelo) < procesos:
                grabacion = _reclamar()
                if grabacion is None:
                    break
                informar(f"Procesando {grabacion.nombre_original}...")
                ruta = grabacion.archivo.path if grabacion.archivo else ""
                try:
                    futuro = ejecutor.submit(analizar, ruta, grabacion.lote.parametros())
                except BrokenProcessPool:
                    grabacion.estado = Grabacion.Estado.EN_COLA
                    grabacion.save(update_fields=["estado"])
                    ejecutor = fabrica_ejecutor(max_workers=procesos)
                    break
                except BaseException:  # p. ej. Ctrl+C justo al repartir: no queda a medias
                    grabacion.estado = Grabacion.Estado.EN_COLA
                    grabacion.save(update_fields=["estado"])
                    raise
                en_vuelo[futuro] = grabacion

            if not en_vuelo:
                if una_vez:
                    break
                time.sleep(espera_s)
                continue

            terminados, _ = wait(en_vuelo, timeout=PERIODO_LATIDO_S, return_when=FIRST_COMPLETED)
            roto = False
            for futuro in terminados:
                grabacion = en_vuelo.pop(futuro)
                try:
                    salida = futuro.result()
                except BrokenProcessPool:
                    roto = True
                    salida = {"ok": False, "mensaje": "El proceso de análisis se interrumpió "
                              "(posible falta de memoria). Puedes reintentarlo."}
                except Exception as error:
                    salida = {"ok": False, "mensaje": f"{type(error).__name__}: {error}"}
                _guardar(grabacion, salida)
                clave = "procesadas" if salida["ok"] else "con_error"
                hechas[clave] += 1
                informar(f"{'OK   ' if salida['ok'] else 'ERROR'} {grabacion.nombre_original}"
                         + ("" if salida["ok"] else f": {salida['mensaje']}"))

            if roto:
                # Un hijo murió: el grupo entero queda inutilizable. Se marcan las que
                # volaban (también se perdieron) y se crea un grupo nuevo.
                for grabacion in en_vuelo.values():
                    _marcar_error_si_sigue_procesando(
                        grabacion, "El proceso de análisis se interrumpió. Puedes reintentarlo.")
                    hechas["con_error"] += 1
                en_vuelo.clear()
                ejecutor.shutdown(wait=False, cancel_futures=True)
                ejecutor = fabrica_ejecutor(max_workers=procesos)
    finally:
        # Lo que estaba a medias vuelve a la cola, para que la próxima vez continúe.
        ejecutor.shutdown(wait=False, cancel_futures=True)
        Grabacion.objects.filter(
            pk__in=[g.pk for g in en_vuelo.values()],
            estado=Grabacion.Estado.PROCESANDO).update(estado=Grabacion.Estado.EN_COLA)
        quitar_senal()
    return hechas
