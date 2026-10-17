"""
Geometría del visor: posición de los 14 electrodos sobre la cabeza y el cerebro reales.

Las mallas (cabeza y cerebro de la plantilla fsaverage) y la posición de cada electrodo sobre
ellas las genera `docs/generar_mallas.py` en `static/models/`. Las posiciones salen del montaje
10-20 de EEG-Library (`MONTAJE_1020`): cada una se lleva a la superficie de la cabeza por el rayo
desde el centro del cerebro (desvío medio 2 mm). Es solo geometría de presentación: no interviene
en ningún cálculo de potencia.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

from eeg_library.preprocesado.quality import CANALES_EPOC

CARPETA_MODELOS = Path(__file__).resolve().parents[1] / "static" / "models"

# Ángulo mínimo desde el vértice que llega al borde del mapa 2D de respaldo (sin WebGL).
ANGULO_BORDE_MINIMO = math.radians(100)


@lru_cache(maxsize=1)
def _ficha():
    return json.loads((CARPETA_MODELOS / "electrodos.json").read_text(encoding="utf-8"))


def angulo_borde():
    """Ángulo del borde del mapa 2D de respaldo: deja dentro al electrodo más bajo, con margen."""
    mas_bajo = max(math.acos(max(-1.0, min(1.0, c["u"][2]))) for c in _ficha()["canales"].values())
    return max(ANGULO_BORDE_MINIMO, mas_bajo + 0.2)


def proyeccion_2d(u):
    """
    Vista desde arriba (equidistante acimutal desde el vértice), con la nariz hacia +y.
    Devuelve (x, y) en el disco unidad; el borde del dibujo es `angulo_borde()`.
    """
    theta = math.acos(max(-1.0, min(1.0, float(u[2]))))
    horizontal = math.hypot(u[0], u[1])
    if horizontal == 0:
        return 0.0, 0.0
    r = theta / angulo_borde()
    return float(u[0] / horizontal * r), float(u[1] / horizontal * r)


def geometria_visor():
    """Centro del cerebro y, por canal, posición sobre la cabeza, normal, dirección y proyección 2D (en dm)."""
    ficha = _ficha()
    canales = {}
    for canal in CANALES_EPOC:
        c = ficha["canales"][canal]
        x2, y2 = proyeccion_2d(c["u"])
        canales[canal] = {"pos": c["pos"], "normal": c["normal"], "u": c["u"],
                          "p2": [round(x2, 4), round(y2, 4)]}
    return {"centro": ficha["centro"], "borde_2d": round(angulo_borde(), 4), "canales": canales}
