"""
Modelos enchufables: qué modelos se aplican a una grabación y qué predicen.

Cada modelo es un `.joblib` más su ficha `.json` (ver EEG-Library). La lista de
modelos está en `settings.MODELOS`: un nombre sin extensión es un modelo empaquetado en
la librería; un nombre acabado en `.json` es la ficha de un modelo externo, que se busca
en `settings.MODELOS_DIR`. Aquí no hay reglas por modelo: todo se deduce de las fichas
(condiciones aplicables, condiciones por clase, parámetros válidos y columnas).

Los modelos se aplican sobre las `caracteristicas` ya guardadas en el JSON de la
grabación, así que añadir uno que use esas mismas características no obliga a reprocesar.
"""

from pathlib import Path

from django.conf import settings

from eeg_library.modelado.prediccion import cargar_modelo, leer_ficha, predecir

# Aviso fijo que acompaña siempre a los modelos en la pantalla de análisis.
AVISO_FIJO = (
    "Los modelos no miden fatiga ni ningún estado del participante: clasifican la condición "
    "de la grabación (por ejemplo, reposo o tarea). Parte del acierto puede deberse a la "
    "duración de la grabación o al orden de las tareas en el protocolo, no solo a la "
    "actividad cerebral."
)

_cache = {}   # (ficha, firma de los archivos) -> Modelo ya cargado


def limpiar_cache():
    _cache.clear()


def _entrada(nombre):
    """Lo que `leer_ficha` entiende: una id empaquetada o la ruta de una ficha externa."""
    if not nombre.lower().endswith(".json"):
        return nombre
    ruta = Path(nombre)
    return str(ruta if ruta.is_absolute() else Path(settings.MODELOS_DIR) / ruta)


def _mayus(condiciones):
    return {str(c).upper() for c in condiciones}


class ErrorDeModelo(Exception):
    """Un modelo registrado que no se puede cargar; el mensaje va para el investigador."""


def cargar(nombre):
    """
    Carga un modelo registrado (con caché; se recarga si cambian sus archivos).

    Lanza `ErrorDeModelo` si no existe, si su ficha está incompleta o si su `.joblib` no
    es el que describe la ficha.
    """
    try:
        ficha, ruta_ficha = leer_ficha(_entrada(nombre))
        ruta_modelo = ruta_ficha.parent / ficha["archivo"]
        firma = (str(ruta_ficha), ruta_ficha.stat().st_mtime_ns,
                 ruta_modelo.stat().st_mtime_ns if ruta_modelo.exists() else None)
        if firma not in _cache:
            _cache[firma] = cargar_modelo(_entrada(nombre))
        return _cache[firma]
    except FileNotFoundError as error:
        raise ErrorDeModelo(f"No se encuentra el archivo del modelo: {error}") from error
    except Exception as error:
        raise ErrorDeModelo(str(error)) from error


def registrados():
    """`[(nombre, ficha)]` de los modelos registrados cuya ficha se puede leer (sin cargar el .joblib)."""
    salida = []
    for nombre in settings.MODELOS:
        try:
            salida.append((nombre, leer_ficha(_entrada(nombre))[0]))
        except Exception:
            continue
    return salida


# ---------------------------------------------------------------------------
# Textos de la ficha
# ---------------------------------------------------------------------------

def _numero(valor, decimales=3):
    return f"{valor:.{decimales}f}".replace(".", ",")


def _porcentaje(p):
    return f"{p * 100:.1f}".replace(".", ",") + " %"


def texto_parametros(parametros):
    """«CAR condicional · 1–30 Hz · con notch 50 Hz» a partir de los parámetros de procesado."""
    from grabaciones.models import REFERENCIAS
    referencia = dict(REFERENCIAS).get(parametros.get("referencia"), parametros.get("referencia"))
    banda = parametros.get("banda_hz") or ["?", "?"]
    notch = parametros.get("notch_hz")
    return (f"{referencia} · {banda[0]:g}–{banda[1]:g} Hz · "
            + (f"con notch {notch:g} Hz" if notch else "sin notch"))


def _ficha_para_pantalla(ficha):
    test = ficha.get("resultado_test") or {}
    prueba = None
    if test:
        lo, hi = test["ic95"]
        prueba = {
            "metrica": test["metrica"].replace("_", " "),
            "valor": _numero(test["valor"]), "ic": f"{_numero(lo)}–{_numero(hi)}",
            "azar": _numero(test["azar"], 2), "n_personas": test.get("n_personas"),
            "n_grabaciones": test.get("n_grabaciones"), "fuente": test.get("fuente", ""),
            # Posiciones en la escala de 0 a 1 como porcentajes enteros: en un atributo style
            # un decimal saldría con coma. Solo sirven para dibujar la escala.
            "pos_valor": round(test["valor"] * 100), "pos_azar": round(test["azar"] * 100),
            "pos_ic_desde": round(lo * 100), "pos_ic_ancho": max(1, round(hi * 100) - round(lo * 100)),
        }
    entrenamiento = ficha.get("entrenamiento") or {}
    return {
        "test": prueba,
        "avisos": list(ficha.get("avisos") or []),
        "entrenamiento": {"fecha": entrenamiento.get("fecha", ""),
                          "variante": entrenamiento.get("variante", "")},
        "condiciones": ", ".join(ficha["condiciones_aplicables"]),
        "parametros_validos": texto_parametros(ficha["parametros_validos"]),
        "clases": ", ".join(c["nombre"] for c in ficha["clases"]),
    }


# ---------------------------------------------------------------------------
# Qué predice cada modelo
# ---------------------------------------------------------------------------

def _clase_esperada(ficha, condicion):
    """La clase del modelo que corresponde a la condición del archivo, o None."""
    c = condicion.upper()
    for clase, condiciones in (ficha.get("condiciones_por_clase") or {}).items():
        if c in _mayus(condiciones):
            return clase
    if not ficha.get("condiciones_por_clase"):
        return next((x["nombre"] for x in ficha["clases"] if x["nombre"].upper() == c), None)
    return None


def _comparar(ficha, condicion, prediccion):
    esperada = _clase_esperada(ficha, condicion)
    if esperada is None:
        return None
    p = prediccion["probabilidades"][prediccion["clase"]]
    if prediccion["clase"] == esperada:
        return {"coincide": True, "alta_confianza": False,
                "texto": f"Coincide con la condición del archivo ({condicion})."}
    alta = p >= settings.UMBRAL_DISCREPANCIA
    return {"coincide": False, "alta_confianza": alta, "texto": (
        f"No coincide con la condición del archivo ({condicion}): el modelo esperaba "
        f"«{esperada}» y predice «{prediccion['clase']}» con una probabilidad de "
        f"{_porcentaje(p)}. " + ("Con esta confianza conviene revisar la etiqueta o la "
                                "grabación." if alta else "La confianza es baja.")
    )}


def _tarjeta(nombre, modelo, resultado, origen, condicion):
    """Aplica un modelo a una grabación y lo deja listo para mostrar y exportar."""
    ficha = modelo.ficha
    tarjeta = {
        "nombre": nombre, "id": ficha["id"], "titulo": ficha.get("titulo", ficha["id"]),
        "que_predice": ficha["que_predice"], "origen": origen, "estado": "ok",
        "ficha": _ficha_para_pantalla(ficha), "clase": None, "probabilidades": [],
        "comparacion": None, "motivo": "", "requeridos": "",
    }
    try:
        prediccion = predecir(modelo, resultado["caracteristicas"], resultado["parametros_aplicados"])
    except Exception as error:
        tarjeta.update(estado="error", motivo=f"No se pudo aplicar el modelo: {error}")
        return tarjeta, None
    if not prediccion["disponible"]:
        tarjeta.update(estado="no_disponible",
                       motivo="No disponible con estos parámetros de procesado.",
                       requeridos=texto_parametros(prediccion["parametros_requeridos"]))
        return tarjeta, None
    tarjeta["clase"] = prediccion["clase"]
    tarjeta["probabilidades"] = [
        {"nombre": clase, "p": p, "texto": _porcentaje(p), "ancho": round(p * 100),   # entero: en el atributo style un decimal saldría con coma
         "ganadora": clase == prediccion["clase"]}
        for clase, p in prediccion["probabilidades"].items()]
    if origen == "conocida" and condicion:
        tarjeta["comparacion"] = _comparar(ficha, condicion, prediccion)
    return tarjeta, prediccion


def aplicar(resultado, condicion):
    """
    Los modelos que corresponden a una grabación y sus predicciones.

    - Condición conocida: los modelos cuya ficha la incluye, comparando con la etiqueta.
    - Condición desconocida: el modelo que cubre todas las condiciones decide a qué grupo
      pertenece (en c2, reposo o tarea) y se aplican los modelos de ese grupo, marcados
      como «condición estimada».

    Devuelve `{"tarjetas": [...], "mensajes": [...]}`; las tarjetas de modelos que no se
    pueden cargar van al final, con su error. Nunca lanza por un modelo roto.
    """
    condicion = (condicion or "").strip()
    resultado = resultado or {}
    cargados, errores = [], []
    for nombre in settings.MODELOS:
        try:
            cargados.append((nombre, cargar(nombre)))
        except ErrorDeModelo as error:
            errores.append({"nombre": nombre, "id": nombre, "titulo": nombre, "estado": "error",
                            "origen": "", "motivo": f"No se pudo cargar el modelo: {error}",
                            "probabilidades": [], "ficha": None, "comparacion": None,
                            "clase": None, "que_predice": "", "requeridos": ""})

    tarjetas, mensajes = [], []
    universo = set()
    for _, modelo in cargados:
        universo |= _mayus(modelo.ficha["condiciones_aplicables"])

    if condicion:
        aplicables = [(n, m) for n, m in cargados
                      if condicion.upper() in _mayus(m.ficha["condiciones_aplicables"])]
        # Primero el que cubre todas las condiciones (reposo/tarea) y luego el de su grupo.
        aplicables.sort(key=lambda par: _mayus(par[1].ficha["condiciones_aplicables"]) != universo)
        for nombre, modelo in aplicables:
            tarjetas.append(_tarjeta(nombre, modelo, resultado, "conocida", condicion)[0])
        if not aplicables:
            mensajes.append(f"Ningún modelo registrado se aplica a la condición «{condicion}».")
    else:
        universales = [(n, m) for n, m in cargados
                       if universo and _mayus(m.ficha["condiciones_aplicables"]) == universo
                       and m.ficha.get("condiciones_por_clase")]
        if not universales:
            mensajes.append("La condición de la grabación no se conoce y ningún modelo sirve "
                            "para estimarla. Indícala en la lista para ver los modelos.")
        mostrados = set()
        for nombre, modelo in universales:
            tarjeta, prediccion = _tarjeta(nombre, modelo, resultado, "estimadora", "")
            tarjetas.append(tarjeta)
            mostrados.add(nombre)
            if prediccion is None:
                mensajes.append("No se puede estimar la condición con este modelo, así que "
                                "no se muestran los demás.")
                continue
            grupo = _mayus(modelo.ficha["condiciones_por_clase"].get(prediccion["clase"], []))
            for otro, m in cargados:
                condiciones = _mayus(m.ficha["condiciones_aplicables"])
                if otro in mostrados or not condiciones or not condiciones <= grupo:
                    continue
                mostrados.add(otro)
                tarjetas.append(_tarjeta(otro, m, resultado, "estimada", "")[0])
            if grupo:
                mensajes.append(f"Condición estimada por «{tarjeta['titulo']}»: "
                                f"{prediccion['clase']}.")
    return {"tarjetas": tarjetas + errores, "mensajes": mensajes}


# ---------------------------------------------------------------------------
# Pantalla «Modelos»: los modelos y sus resultados, sin elegir una grabación
# ---------------------------------------------------------------------------

LIMITE_FILAS = 100   # grabaciones más recientes que se muestran en la tabla de predicciones


def resumen_modelos():
    """
    Un elemento por modelo registrado, con su ficha lista para mostrar. Un modelo que no se
    puede cargar sale con su error y no tumba la pantalla.
    """
    salida = []
    for nombre in settings.MODELOS:
        try:
            modelo = cargar(nombre)
        except ErrorDeModelo as error:
            salida.append({"nombre": nombre, "id": nombre, "titulo": nombre, "estado": "error",
                           "motivo": f"No se pudo cargar el modelo: {error}",
                           "que_predice": "", "ficha": None})
            continue
        ficha = modelo.ficha
        salida.append({"nombre": nombre, "id": ficha["id"], "titulo": ficha.get("titulo", ficha["id"]),
                       "estado": "ok", "motivo": "", "que_predice": ficha["que_predice"],
                       "ficha": _ficha_para_pantalla(ficha)})
    return salida


def _celda(tarjeta):
    """Lo que se muestra de un modelo en la fila de una grabación."""
    if tarjeta is None:
        return {"estado": "no_aplica"}
    if tarjeta["estado"] != "ok":
        return {"estado": tarjeta["estado"], "motivo": tarjeta["motivo"]}
    ganadora = next(p for p in tarjeta["probabilidades"] if p["ganadora"])
    comparacion = tarjeta["comparacion"]
    return {"estado": "ok", "clase": tarjeta["clase"], "probabilidad": ganadora["texto"],
            "origen": tarjeta["origen"],
            "coincide": None if comparacion is None else comparacion["coincide"],
            "alta_confianza": bool(comparacion and comparacion["alta_confianza"])}


def tabla_predicciones(grabaciones, columnas):
    """
    Predicción de cada modelo para cada grabación procesada (las mismas que en su pantalla de
    análisis: se aplican `aplicar` sobre las características guardadas, sin reprocesar).
    `columnas` son los modelos que se pudieron cargar (`resumen_modelos`).
    """
    ids = [c["id"] for c in columnas]
    filas = []
    for grabacion in grabaciones:
        if not (grabacion.resultado or {}).get("caracteristicas"):
            continue
        por_id = {t["id"]: t for t in aplicar(grabacion.resultado, grabacion.condicion)["tarjetas"]}
        filas.append({"grabacion": grabacion, "celdas": [_celda(por_id.get(i)) for i in ids]})
    return filas

