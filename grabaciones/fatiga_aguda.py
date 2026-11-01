"""
Pestaña «Fatiga aguda»: cómo cambia el EEG a lo largo de una tarea PASAT o PVTB.

Todo lo que se calcula sale de EEG-Library (`puntuar_fatiga_aguda` y la ficha del modelo):
la puntuación de cada ventana, la ρ, el veredicto de tercios y los pesos. Aquí solo se
prepara para pintar:

- **Suavizado de presentación.** La cinta y el cerebro animado usan una media móvil centrada
  de `VENTANAS_SUAVIZADO` ventanas (≈ 30 s), truncada en los extremos. Una ventana suelta de
  4 s apenas dice nada (AUC ≈ 0,58), y sin suavizar la animación solo enseñaría ruido. El
  veredicto y la ρ no se suavizan: son los de la librería, los mismos cálculos que dieron
  la cifra del test.
- **Escala fija** en toda la grabación (por banda, percentiles 2–98 de los electrodos válidos),
  para que el cambio se vea al reproducir y un electrodo extremo no aplane el resto.
"""

import numpy as np

from eeg_library.modelado.fatiga_aguda import (
    BANDAS,
    CONDICIONES,
    leer_ficha_fatiga_aguda,
    puntuar,
)

from grabaciones.analisis_espectral import NOMBRE_BANDA
from grabaciones.geometria import geometria_visor
from grabaciones.modelos import _ficha_para_pantalla

VENTANAS_SUAVIZADO = 15    # ventanas cada 2 s: ≈ 30 s
BANDA_INICIAL = "beta"     # la firma confirmada en PVTB (H3 de la línea)

AVISO_FIJO = (
    "Mide el cambio del EEG con el tiempo en tarea, no el nivel de fatiga de la persona. "
    "Una ventana suelta de 4 s apenas dice nada: lo fiable es la tendencia de la grabación "
    "entera. Parte del cambio puede deberse al asentamiento del casco, que también se ve en "
    "reposo, y el orden de las tareas del protocolo es fijo."
)


def suavizar(valores, n=VENTANAS_SUAVIZADO):
    """Media móvil centrada de `n` ventanas; en los extremos promedia las que hay."""
    v = np.asarray(valores, dtype=float)
    mitad = n // 2
    acumulada = np.concatenate([[0.0], np.cumsum(v)])
    desde = np.clip(np.arange(len(v)) - mitad, 0, len(v))
    hasta = np.clip(np.arange(len(v)) + mitad + 1, 0, len(v))
    return (acumulada[hasta] - acumulada[desde]) / (hasta - desde)


def _mmss(segundos):
    s = int(round(segundos))
    return f"{s // 60}:{s % 60:02d}"


def _bandas(resultado):
    rangos = ((resultado or {}).get("potencia") or {}).get("bandas_hz") or {}
    return [{"clave": b, "nombre": NOMBRE_BANDA.get(b, b.capitalize()),
             "rango": f"{rangos[b][0]:g}–{rangos[b][1]:g} Hz" if b in rangos else ""}
            for b in BANDAS]


def para_csv(grabacion):
    """Lo que exporta el CSV: la salida de la librería sin suavizar, o None si no se aplica."""
    condicion = (grabacion.condicion or "").strip().upper()
    if grabacion.estado != "procesada" or not grabacion.resultado or condicion not in CONDICIONES:
        return None
    p = puntuar(grabacion.resultado, condicion)
    return p if p["disponible"] else None


def resumen_fatiga_aguda(grabacion):
    """
    Datos de la pestaña para una grabación.

    Devuelve `{"estado": ..., ...}` con estado:
    - `sin_procesar`: todavía no hay resultado.
    - `sin_condicion` o `otra_condicion`: el modelo solo existe para PASAT y PVTB.
    - `no_disponible`: la librería no puede puntuarla (`motivo`); `reprocesar` dice si se
      arregla volviendo a procesar.
    - `ok`: todo lo de la pantalla, con `visor` y `fatiga` listos para `json_script`.
    """
    condicion = (grabacion.condicion or "").strip().upper()
    if grabacion.estado != "procesada" or not grabacion.resultado:
        return {"estado": "sin_procesar"}
    if not condicion:
        return {"estado": "sin_condicion", "condiciones": CONDICIONES}
    if condicion not in CONDICIONES:
        return {"estado": "otra_condicion", "condicion": condicion, "condiciones": CONDICIONES}

    resultado = grabacion.resultado
    p = puntuar(resultado, condicion)
    if not p["disponible"]:
        return {"estado": "no_disponible", "motivo": p["motivo"],
                "reprocesar": not resultado.get("por_ventana")}

    ficha = leer_ficha_fatiga_aguda(condicion)
    pv = resultado["por_ventana"]
    instantes = np.asarray(p["instante_s"])
    puntuacion = suavizar(p["puntuacion"])
    escala_cinta = float(np.max(np.abs(puntuacion))) or 1.0

    # Potencia relativa suavizada por canal y banda, en % y con 2 decimales (es para pintar).
    canales = list(pv["pot_rel"])
    validos = [c for c in canales if pv["canal_valido"].get(c)]
    # «Cambio»: diferencia, en puntos porcentuales, con la media del electrodo en el primer
    # tercio. Es lo que se ve cambiar al reproducir: las diferencias entre electrodos son mucho
    # mayores que el cambio de cada uno con el tiempo y, en «valor», lo tapan.
    primero = instantes <= instantes[-1] / 3
    fotogramas, cambios, rangos, rangos_cambio = {}, {}, {}, {}
    for b in BANDAS:
        serie = {c: suavizar(pv["pot_rel"][c][b]) * 100 for c in canales}
        fotogramas[b] = {c: np.round(v, 2).tolist() for c, v in serie.items()}
        cambios[b] = {c: np.round(v - v[primero].mean(), 2).tolist() for c, v in serie.items()}
        todos = np.concatenate([serie[c] for c in validos]) if validos else np.array([0.0, 1.0])
        # Percentiles 2–98: un solo electrodo extremo no aplana el color del resto del cerebro.
        rangos[b] = [float(np.percentile(todos, 2)), float(np.percentile(todos, 98))]
        dif = np.concatenate([np.abs(cambios[b][c]) for c in validos]) if validos else np.array([1.0])
        tope = max(float(np.percentile(dif, 90)), 0.1)   # lo que pase de aquí satura el color
        rangos_cambio[b] = [-tope, tope]

    calidad = resultado.get("calidad") or {}
    electrodos = [{"canal": c, "zona": (calidad.get(c) or {}).get("region"),
                   "valido": bool(pv["canal_valido"].get(c)),
                   "rel": {b: fotogramas[b][c][0] / 100 for b in BANDAS},
                   "cambio": {b: cambios[b][c][0] for b in BANDAS},
                   "log_abs": {b: None for b in BANDAS}} for c in canales]
    visor = {"geometria": geometria_visor(), "bandas": _bandas(resultado),
             "banda_inicial": BANDA_INICIAL, "electrodos": electrodos, "rango_fijo": rangos,
             "rango_cambio": rangos_cambio, "metrica_inicial": "cambio"}

    final = p["tercios"]["final_mayor"]
    # Los tercios se cortan como en la librería: por el inicio de la ventana, frente al de la última.
    ultima = float(instantes[-1])
    duracion = ultima + resultado["parametros_aplicados"]["epocado"]["duracion_s"]
    return {
        "estado": "ok",
        "condicion": condicion,
        "titulo": ficha.get("titulo", ficha["id"]),
        "final_mayor": final,
        "veredicto": (
            "El último tercio de esta grabación se parece más al final de la tarea que el primero."
            if final else
            "En esta grabación no se aprecia el cambio: el último tercio no se parece más al "
            "final de la tarea que el primero." if final is False else
            "En esta grabación el primer y el último tercio puntúan igual."),
        "rho": p["rho"],
        "rho_texto": "—" if p["rho"] is None else f"{p['rho']:+.2f}".replace(".", ","),
        "rho_test": f"{ficha['resultado_test_rho']['valor']:+.2f}".replace(".", ","),
        "ficha": _ficha_para_pantalla(ficha),
        "acierto_texto": f"{ficha['resultado_test']['valor'] * 100:.0f} %",
        "duracion_texto": _mmss(duracion),
        "n_ventanas": p["n_ventanas"],
        "visor": visor,
        "fatiga": {
            "instante_s": instantes.tolist(),
            "puntuacion": np.round(puntuacion / escala_cinta, 4).tolist(),
            "duracion_s": duracion,
            "tercios_s": [ultima / 3, 2 * ultima / 3],
            "fotogramas": fotogramas,
            "cambios": cambios,
        },
    }
