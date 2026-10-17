"""
Genera las mallas del visor 3D y la posición de los electrodos sobre ellas.

    .venv\\Scripts\\python.exe docs\\generar_mallas.py --pial-izq pial_left.gii.gz --pial-der pial_right.gii.gz

Entradas (todas son plantillas públicas, sin datos de participantes):
- Cabeza: `fsaverage-head.fif`, que ya trae MNE en su carpeta `data/fsaverage` (2.033 vértices).
  Se suaviza y se subdivide una vez (subdivisión de Loop) para que no se vea facetada.
- Cerebro: superficie pial de fsaverage5 (10.242 vértices por hemisferio). Son los archivos
  `pial_left.gii.gz` y `pial_right.gii.gz` de `nilearn/datasets/data/fsaverage5` (repositorio de
  nilearn en GitHub).
- Electrodos: posiciones del montaje 10-20 de la librería (`MONTAJE_1020`). Cada una se lleva
  a la superficie de la cabeza siguiendo el rayo desde el centro del cerebro, y se guarda la
  distancia que hubo que moverla.

Salida en `static/models/`: `cabeza.bin`, `cerebro.bin` y `electrodos.json`. Unidades: decímetros
(la cabeza mide ~1,8 dm), ejes x derecha, y frente, z arriba. Las mallas son derivadas
de fsaverage (FreeSurfer, ver `LICENCIA-FreeSurfer.txt`) y se marcan como modificadas.
"""

import argparse
import base64
import gzip
import json
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import mne
import numpy as np
from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.preprocesado.reader import MONTAJE_1020

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "static" / "models"
DM = 10.0  # de metros a decímetros


def leer_gifti(ruta):
    """Vértices (N, 3) y triángulos (M, 3) de un GIFTI (solo hace falta la codificación gzip+base64)."""
    raiz = ET.fromstring(gzip.open(ruta).read())
    vertices = triangulos = None
    for da in raiz.iter("DataArray"):
        dim = [int(da.get(f"Dim{i}")) for i in range(int(da.get("Dimensionality")))]
        crudo = zlib.decompress(base64.b64decode(da.find("Data").text))
        tipo = {"NIFTI_TYPE_FLOAT32": "<f4", "NIFTI_TYPE_INT32": "<i4"}[da.get("DataType")]
        datos = np.frombuffer(crudo, dtype=tipo).reshape(dim)
        if da.get("Intent") == "NIFTI_INTENT_POINTSET":
            vertices = datos.astype(np.float64)
        elif da.get("Intent") == "NIFTI_INTENT_TRIANGLE":
            triangulos = datos.astype(np.int64)
    return vertices, triangulos


def volumen(v, t):
    return np.einsum("ij,ij->i", v[t[:, 0]], np.cross(v[t[:, 1]], v[t[:, 2]])).sum() / 6


def hacia_fuera(v, t):
    """Triángulos orientados con la normal hacia fuera (volumen positivo)."""
    return t if volumen(v, t) > 0 else t[:, ::-1].copy()


def subdividir_loop(v, t):
    """Una pasada de subdivisión de Loop: suaviza y cuadruplica los triángulos."""
    n = len(v)
    aristas = {}
    vecinos = [set() for _ in range(n)]
    opuestos = {}
    for tri in t:
        for k in range(3):
            a, b, c = tri[k], tri[(k + 1) % 3], tri[(k + 2) % 3]
            clave = (min(a, b), max(a, b))
            opuestos.setdefault(clave, []).append(c)
            vecinos[a].add(b)
            vecinos[b].add(a)
    nuevos = []
    for clave, ops in opuestos.items():
        a, b = clave
        if len(ops) == 2:
            p = 3 / 8 * (v[a] + v[b]) + 1 / 8 * (v[ops[0]] + v[ops[1]])
        else:
            p = 0.5 * (v[a] + v[b])
        aristas[clave] = n + len(nuevos)
        nuevos.append(p)
    viejos = np.empty_like(v)
    for i in range(n):
        k = len(vecinos[i])
        beta = 3 / 16 if k == 3 else 3 / (8 * k)
        viejos[i] = (1 - k * beta) * v[i] + beta * v[list(vecinos[i])].sum(axis=0)
    nuevas_t = []
    for a, b, c in t:
        ab, bc, ca = (aristas[(min(x, y), max(x, y))] for x, y in ((a, b), (b, c), (c, a)))
        nuevas_t += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    return np.vstack([viejos, np.array(nuevos)]), np.array(nuevas_t, dtype=np.int64)


def interseccion_rayo(origen, direccion, v, t):
    """Impactos de un rayo con todos los triángulos (Möller–Trumbore): lista de (distancia, índice)."""
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    e1, e2 = b - a, c - a
    h = np.cross(direccion, e2)
    det = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = origen - a
    u = inv * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    w = inv * (q @ direccion)
    dist = inv * np.einsum("ij,ij->i", e2, q)
    bien = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (dist > 0)
    return [(dist[i], i) for i in np.nonzero(bien)[0]]


def escribir_malla(ruta, v, t):
    with open(ruta, "wb") as f:
        f.write(struct.pack("<II", len(v), len(t)))
        f.write(v.astype("<f4").tobytes())
        f.write(t.astype("<u4").tobytes())
    print(f"{ruta.name}: {len(v)} vértices, {len(t)} triángulos, {ruta.stat().st_size // 1024} KB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pial-izq", required=True, type=Path)
    ap.add_argument("--pial-der", required=True, type=Path)
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    # Cabeza de la plantilla fsaverage que trae MNE (en metros).
    ruta_cabeza = Path(mne.__file__).parent / "data" / "fsaverage" / "fsaverage-head.fif"
    sup = mne.read_bem_surfaces(ruta_cabeza, verbose=False)[0]
    cv, ct = sup["rr"], hacia_fuera(sup["rr"], sup["tris"])
    cv, ct = subdividir_loop(cv, ct)
    cv, ct = cv * DM, hacia_fuera(cv * DM, ct)

    # Cerebro: los dos hemisferios (en mm) en una sola malla.
    vi, ti = leer_gifti(args.pial_izq)
    vd, td = leer_gifti(args.pial_der)
    bv = np.vstack([vi, vd]) / 1000 * DM
    bt = np.vstack([hacia_fuera(vi, ti), hacia_fuera(vd, td) + len(vi)])
    centro = bv.mean(axis=0)

    # Electrodos: del montaje de la librería a la superficie de la cabeza, por el rayo desde el centro.
    montaje = mne.channels.make_standard_montage(MONTAJE_1020).get_positions()["ch_pos"]
    canales = {}
    for canal in CANALES_EPOC:
        p = np.asarray(montaje[canal]) * DM
        d = (p - centro) / np.linalg.norm(p - centro)
        impactos = interseccion_rayo(centro, d, cv, ct)
        dist, i = min(impactos, key=lambda x: abs(x[0] - np.linalg.norm(p - centro)))
        s = centro + d * dist
        a, b, c = cv[ct[i]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        canales[canal] = {"pos": [round(float(x), 4) for x in s], "normal": [round(float(x), 4) for x in n],
                          "u": [round(float(x), 4) for x in d],
                          "desvio_mm": round(float(np.linalg.norm(p - s) * 100), 2)}
    escribir_malla(args.salida / "cabeza.bin", cv, ct)
    escribir_malla(args.salida / "cerebro.bin", bv, bt)
    ficha = {"centro": [round(float(x), 4) for x in centro], "montaje": MONTAJE_1020, "unidad": "dm",
             "canales": canales,
             "origen": "Mallas derivadas de la plantilla fsaverage de FreeSurfer (cabeza: MNE-Python; "
                       "cerebro: fsaverage5 de nilearn). Modificadas: subdivididas, unidas y exportadas."}
    (args.salida / "electrodos.json").write_text(json.dumps(ficha, indent=1, ensure_ascii=False), encoding="utf-8")
    desvios = [c["desvio_mm"] for c in canales.values()]
    print(f"electrodos.json: 14 canales, desvío al llevarlos a la cabeza: media {np.mean(desvios):.1f} mm, "
          f"máximo {max(desvios):.1f} mm")


if __name__ == "__main__":
    main()
