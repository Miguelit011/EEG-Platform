"""Validación de un EDF al subirlo. Solo lee la cabecera: no carga la señal."""

import inspect
import warnings
from dataclasses import dataclass

import mne

from eeg_library.preprocesado.filtering import recortar_registro
from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.preprocesado.reader import MIN_SFREQ, TARGET_SFREQ
from eeg_library.procesado.epoching import crear_epocas


def _por_defecto(funcion, parametro):
    """Valor por defecto de un argumento de la librería (no se copia aquí)."""
    return inspect.signature(funcion).parameters[parametro].default


# Duración mínima para obtener al menos una época: lo que recorta la librería
# por cada extremo más una ventana de epocado.
DURACION_MINIMA_S = (_por_defecto(recortar_registro, "inicio")
                     + _por_defecto(recortar_registro, "fin")
                     + _por_defecto(crear_epocas, "duracion"))


class ErrorDeValidacion(Exception):
    """El archivo no se puede procesar; el mensaje va dirigido al investigador."""


@dataclass(frozen=True)
class InfoEdf:
    """Datos básicos de un EDF válido, leídos de su cabecera."""

    duracion_s: float
    sfreq_original_hz: float
    remuestreada: bool


def validar_edf(ruta):
    """
    Comprueba que `ruta` es un EDF utilizable y devuelve sus datos básicos.

    Reglas, las mismas que aplica la librería al cargar: frecuencia de muestreo
    de al menos `MIN_SFREQ` (por debajo se rechaza; si no es `TARGET_SFREQ`, la
    librería la remuestrea), los 14 canales del Emotiv y una duración mínima
    (`DURACION_MINIMA_S`) para que sobreviva al recorte y dé al menos una época.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = mne.io.read_raw_edf(ruta, preload=False, verbose=False)
    except Exception as error:
        raise ErrorDeValidacion(
            "No se puede leer como EDF (el archivo está dañado o no es un EDF)."
        ) from error

    sfreq = float(raw.info["sfreq"])
    if sfreq < MIN_SFREQ:
        raise ErrorDeValidacion(
            f"Frecuencia de muestreo insuficiente: {sfreq:g} Hz "
            f"(se requieren al menos {MIN_SFREQ:g} Hz)."
        )

    faltan = [canal for canal in CANALES_EPOC if canal not in raw.ch_names]
    if faltan:
        raise ErrorDeValidacion(
            f"Faltan {len(faltan)} de los {len(CANALES_EPOC)} canales del Emotiv EPOC X: "
            + ", ".join(faltan) + "."
        )

    duracion = float(raw.n_times / sfreq)
    if duracion < DURACION_MINIMA_S:
        raise ErrorDeValidacion(
            f"Grabación demasiado corta: {duracion:.1f} s "
            f"(mínimo {DURACION_MINIMA_S:g} s)."
        )

    return InfoEdf(duracion_s=duracion, sfreq_original_hz=sfreq,
                   remuestreada=sfreq != TARGET_SFREQ)
