"""Geometría del visor: sale del montaje de la librería y es coherente en 2D y 3D."""

import math

import numpy as np
from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.preprocesado.reader import MONTAJE_1020

from grabaciones.geometria import angulo_borde, geometria_visor


def test_los_14_canales_del_epoc_tienen_posicion():
    g = geometria_visor()
    assert list(g["canales"]) == list(CANALES_EPOC)
    for datos in g["canales"].values():
        assert abs(np.linalg.norm(datos["u"]) - 1) < 1e-3     # dirección unitaria


def test_izquierda_y_derecha_siguen_el_montaje():
    c = geometria_visor()["canales"]
    for izq, der in (("F3", "F4"), ("T7", "T8"), ("O1", "O2"), ("AF3", "AF4")):
        assert c[izq]["u"][0] < 0 < c[der]["u"][0]            # x: izquierda negativa
    assert c["AF3"]["u"][1] > 0 > c["O1"]["u"][1]              # y: frente positivo
    assert MONTAJE_1020 in ("standard_1020", "colin27_1020")


def test_proyeccion_2d_dentro_del_disco_y_sin_solaparse():
    c = geometria_visor()["canales"]
    puntos = [d["p2"] for d in c.values()]
    assert all(math.hypot(*p) < 1 for p in puntos)
    for i, a in enumerate(puntos):
        for b in puntos[i + 1:]:
            assert math.dist(a, b) > 0.1                       # ningún par casi encima
    assert angulo_borde() > math.pi / 2                       # el borde pasa del ecuador


def test_mallas_reales_coherentes_con_el_montaje():
    """Las mallas del visor y las posiciones salen de la plantilla y del montaje de la librería."""
    import json
    import struct
    from pathlib import Path

    import mne

    carpeta = Path(__file__).resolve().parents[1] / "static" / "models"
    ficha = json.loads((carpeta / "electrodos.json").read_text(encoding="utf-8"))
    montaje = mne.channels.make_standard_montage(MONTAJE_1020).get_positions()["ch_pos"]
    for canal in CANALES_EPOC:
        c = ficha["canales"][canal]
        assert np.linalg.norm(np.array(c["pos"]) - np.array(montaje[canal]) * 10) < 0.06   # < 6 mm de la posición del montaje
        assert abs(np.linalg.norm(c["normal"]) - 1) < 1e-3
    for nombre, minimo in (("cabeza.bin", 5000), ("cerebro.bin", 15000)):
        datos = (carpeta / nombre).read_bytes()
        nv, nt = struct.unpack("<II", datos[:8])
        assert nv > minimo and len(datos) == 8 + nv * 12 + nt * 12
        indices = np.frombuffer(datos, dtype="<u4", offset=8 + nv * 12)
        assert indices.max() < nv                                   # ningún triángulo apunta fuera
    assert len(datos) < 2_000_000                                    # tamaño razonable para una web local
    # Las plantillas llevan sus licencias al lado.
    assert "have been obtained under license from The General Hospital Corporation" in (
        carpeta / "LICENCIA-FreeSurfer.txt").read_text(encoding="utf-8")
    assert (carpeta / "LICENCIA-MNE-BSD3.txt").exists() and (carpeta / "LICENCIA-nilearn-BSD3.txt").exists()
