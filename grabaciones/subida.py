"""Guardado y validación de los EDF de un lote."""

import os

from django import forms

from grabaciones.condicion import condicion_desde_nombre
from grabaciones.models import Grabacion, Lote
from grabaciones.validacion import ErrorDeValidacion, validar_edf


class LoteForm(forms.ModelForm):
    """Parámetros de procesado del lote: opciones cerradas, por defecto las del estudio."""

    class Meta:
        model = Lote
        fields = ["referencia", "banda", "notch"]
        labels = {"referencia": "Referencia", "banda": "Paso banda",
                  "notch": "Filtro notch a 50 Hz"}


def guardar_grabacion(lote, archivo):
    """
    Guarda y valida un archivo subido. Un archivo inválido queda con estado
    `error` y su mensaje, sin archivo en disco, y no afecta a los demás.
    """
    nombre = os.path.basename(archivo.name)
    condicion = condicion_desde_nombre(nombre)
    grabacion = Grabacion(
        lote=lote,
        nombre_original=nombre,
        condicion=condicion,
        origen_condicion=(Grabacion.OrigenCondicion.NOMBRE if condicion
                          else Grabacion.OrigenCondicion.VACIA),
    )
    try:
        if not nombre.lower().endswith(".edf"):
            raise ErrorDeValidacion("No es un archivo .edf.")
        grabacion.archivo.save(nombre, archivo, save=False)
        info = validar_edf(grabacion.archivo.path)
        grabacion.duracion_s = info.duracion_s
        grabacion.sfreq_original_hz = info.sfreq_original_hz
        grabacion.remuestreada = info.remuestreada
        grabacion.estado = Grabacion.Estado.EN_COLA
    except ErrorDeValidacion as error:
        grabacion.mensaje_error = str(error)
    except Exception as error:  # p. ej. disco lleno: que no tumbe al resto del lote
        grabacion.mensaje_error = f"No se pudo guardar el archivo: {error}"
    if grabacion.mensaje_error:
        if grabacion.archivo:
            grabacion.archivo.delete(save=False)
        grabacion.estado = Grabacion.Estado.ERROR
    grabacion.save()
    return grabacion


def guardar_lote(lote, archivos):
    """Guarda todos los archivos del lote y devuelve las grabaciones creadas."""
    return [guardar_grabacion(lote, archivo) for archivo in archivos]
