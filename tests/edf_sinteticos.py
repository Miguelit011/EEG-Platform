"""EDF sintéticos pequeños para los tests. No hay datos de participantes en el repo."""

import mne
import numpy as np

from eeg_library.preprocesado.quality import CANALES_EPOC


def escribir_edf(ruta, duracion_s=30.0, sfreq=256, canales=None):
    """
    Escribe un EDF con la estructura del Emotiv: los 14 electrodos más sus
    canales de calidad `CQ.*` y algo de telemetría. `canales` permite quitar
    electrodos para probar la validación.
    """
    rng = np.random.default_rng(0)
    n = int(duracion_s * sfreq)
    electrodos = list(CANALES_EPOC if canales is None else canales)
    nombres = electrodos + [f"CQ.{c}" for c in electrodos] + ["Counter", "MOT.AccX"]
    datos = [rng.normal(0, 5e-6, n) if c in electrodos else
             (np.full(n, 4.0) if c.startswith("CQ.") else rng.normal(0, 1.0, n))
             for c in nombres]
    tipos = ["eeg" if c in electrodos else "misc" for c in nombres]
    raw = mne.io.RawArray(np.array(datos), mne.create_info(nombres, sfreq, tipos), verbose=False)
    mne.export.export_raw(str(ruta), raw, fmt="edf", overwrite=True, verbose=False)
    return ruta
