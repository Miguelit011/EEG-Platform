"""
¿Da la plataforma el mismo resultado en Windows, Linux y macOS? (Fase 12)

Procesa un EDF con la misma función que usa el procesador (`grabaciones.analisis.analizar`) y
los parámetros del estudio, y guarda el resultado en un JSON. Después compara dos de esos JSON,
hechos en sistemas distintos, número a número.

Sin argumento `--edf` usa un EDF **sintético** (ruido con semilla fija, el de los tests): es
anónimo y sale idéntico en cualquier equipo, así que el JSON se puede mover entre equipos. Con
`--edf` se puede usar un EDF real, pero su JSON es de un participante: no va a git ni sale del equipo.

Desde la carpeta EEG-Platform:

    .venv/bin/python docs/comparar_sistemas.py generar resultado_macos.json            (Linux y macOS)
    .venv\\Scripts\\python.exe docs\\comparar_sistemas.py generar resultado_windows.json   (Windows)
    .venv\\Scripts\\python.exe docs\\comparar_sistemas.py comparar resultado_windows.json resultado_macos.json
"""

import argparse
import json
import platform
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DURACION_SINTETICO_S = 60


def generar(salida, edf=None):
    sys.path.insert(0, str(RAIZ))
    from eeg_library.procesado.parametros import normalizar_parametros
    from grabaciones.analisis import analizar

    with tempfile.TemporaryDirectory() as carpeta:
        if edf is None:
            from tests.edf_sinteticos import escribir_edf
            edf = escribir_edf(Path(carpeta) / "sintetico.edf", duracion_s=DURACION_SINTETICO_S)
        salida_analisis = analizar(str(edf), normalizar_parametros())
    if not salida_analisis["ok"]:
        sys.exit(f"El análisis falló: {salida_analisis['mensaje']}")
    resultado = salida_analisis["resultado"]
    resultado["metadatos"].pop("fecha_analisis", None)
    resultado["metadatos"].pop("archivo", None)
    sistema = {"sistema": platform.system(), "version": platform.release(),
               "maquina": platform.machine(), "python": platform.python_version()}
    import numpy
    sistema["blas"] = _blas(numpy)
    Path(salida).write_text(json.dumps({"sistema": sistema, "resultado": resultado}, indent=1),
                            encoding="utf-8")
    print(f"Guardado {salida} ({sistema['sistema']} {sistema['maquina']}, BLAS: {sistema['blas']}).")


def _blas(numpy):
    try:
        info = numpy.show_config(mode="dicts")["Build Dependencies"]["blas"]
        return f"{info.get('name')} {info.get('version', '')}".strip()
    except Exception:
        return "desconocido"


def _hojas(valor, ruta=""):
    """Pares (ruta, valor) de todas las hojas del JSON."""
    if isinstance(valor, dict):
        for clave, sub in valor.items():
            yield from _hojas(sub, f"{ruta}/{clave}")
    elif isinstance(valor, list):
        for i, sub in enumerate(valor):
            yield from _hojas(sub, f"{ruta}[{i}]")
    else:
        yield ruta, valor


def comparar(a, b):
    datos_a = json.loads(Path(a).read_text(encoding="utf-8"))
    datos_b = json.loads(Path(b).read_text(encoding="utf-8"))
    for datos, nombre in ((datos_a, a), (datos_b, b)):
        s = datos["sistema"]
        print(f"{nombre}: {s['sistema']} {s['version']} {s['maquina']}, Python {s['python']}, "
              f"BLAS {s['blas']}")
    hojas_a, hojas_b = dict(_hojas(datos_a["resultado"])), dict(_hojas(datos_b["resultado"]))
    solo = sorted(set(hojas_a) ^ set(hojas_b))
    distintas, versiones, max_abs, max_rel, peor = [], [], 0.0, 0.0, None
    for ruta in sorted(set(hojas_a) & set(hojas_b)):
        x, y = hojas_a[ruta], hojas_b[ruta]
        if ruta.startswith("/metadatos/versiones/"):
            # Informativo: p. ej. Python 3.10.11 en Windows y 3.10.22 en Ubuntu no es un resultado.
            if x != y:
                versiones.append((ruta, x, y))
            continue
        numeros = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y))
        if numeros:
            d = abs(x - y)
            rel = d / max(abs(x), abs(y)) if d else 0.0
            if d > max_abs:
                max_abs = d
            if rel > max_rel:
                max_rel, peor = rel, ruta
        elif x != y:
            distintas.append((ruta, x, y))

    print(f"\nValores comparados: {len(set(hojas_a) & set(hojas_b))}")
    print(f"Diferencia máxima: {max_abs:.3g} absoluta, {max_rel:.3g} relativa"
          + (f" (en {peor})" if peor else ""))
    for ruta, x, y in versiones:
        print(f"Versión distinta (informativo): {ruta.rsplit('/', 1)[-1]}: {x} y {y}")
    for ruta, x, y in distintas:
        print(f"Distinto: {ruta}: {x!r} ≠ {y!r}")
    for ruta in solo:
        print(f"Solo en uno de los dos: {ruta}")
    identicos = max_abs == 0 and not distintas and not solo
    print("\nResultado: " + ("IDÉNTICOS." if identicos else
                             "iguales salvo redondeo." if max_rel < 1e-6 and not distintas and not solo
                             else "DIFERENTES: revisar."))
    return 0 if (max_rel < 1e-6 and not distintas and not solo) else 1


def main():
    analizador = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ordenes = analizador.add_subparsers(dest="orden", required=True)
    g = ordenes.add_parser("generar", help="procesa el EDF y guarda el resultado en un JSON")
    g.add_argument("salida")
    g.add_argument("--edf", help="EDF real (por defecto, uno sintético y anónimo)")
    c = ordenes.add_parser("comparar", help="compara dos JSON hechos con «generar»")
    c.add_argument("a")
    c.add_argument("b")
    args = analizador.parse_args()
    if args.orden == "generar":
        generar(args.salida, args.edf)
    else:
        sys.exit(comparar(args.a, args.b))


if __name__ == "__main__":
    main()
