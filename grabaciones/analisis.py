"""
Análisis de una grabación en un proceso aparte.

Este módulo lo importan los procesos hijos del procesador, así que no importa
Django ni los modelos: recibe una ruta y unos parámetros y devuelve un
diccionario con el resultado o con el error. No toca la base de datos.
"""

import contextlib
import io
import json
import warnings


def analizar(ruta, parametros):
    """
    Llama a `analizar_grabacion` de la librería.

    Devuelve `{"ok": True, "resultado": dict}` o
    `{"ok": False, "mensaje": str}`. Nunca lanza: un error en un archivo no debe
    detener el resto. El resultado se comprueba como JSON estricto (sin NaN),
    que es lo que garantiza el contrato con la librería.
    """
    try:
        from eeg_library import analizar_grabacion
        from eeg_library.procesado.batch import ErrorDeFase

        try:
            # La librería escribe un resumen por fase en la salida estándar y
            # MNE avisa de cosas que no afectan al resultado: no interesan aquí.
            with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
                warnings.simplefilter("ignore")
                resultado = analizar_grabacion(ruta, parametros)
        except ErrorDeFase as error:
            return {"ok": False, "mensaje": f"Fase «{error.fase}»: "
                    f"{type(error.original).__name__}: {error.original}"}
        json.dumps(resultado, allow_nan=False)
        return {"ok": True, "resultado": resultado}
    except Exception as error:
        return {"ok": False, "mensaje": f"{type(error).__name__}: {error}"}
