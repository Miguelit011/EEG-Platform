"""
Pantalla de análisis: potencia por banda, por zona y por electrodo, a partir del JSON guardado.

Solo usa el JSON que devolvió `analizar_grabacion`. La web no calcula potencia: lo
único que hace es presentar lo que viene de la librería y la media simple de
los electrodos válidos para «toda la cabeza» (la librería solo agrega por zona).
Los electrodos descartados no se colorean ni cuentan: su potencia se calculó con
señal que no pasó por CAR ni ICA y no es comparable.
"""

import math

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.procesado.matrix import REGIONES

from grabaciones.calidad import POSICIONES, nivel_de_fiabilidad, punto_svg

NOMBRE_BANDA = {"delta": "Delta", "theta": "Theta", "alfa": "Alfa", "beta": "Beta"}
BANDA_POR_DEFECTO = "alfa"

# Colores de las series de la gráfica (paleta de Okabe-Ito, apta para daltonismo).
COLOR_CABEZA = "#444444"
COLOR_ZONA = {"frontal": "#0072B2", "frontocentral": "#E69F00",
              "temporal": "#009E73", "posterior": "#CC79A7"}

# Escala del mapa: viridis (perceptualmente uniforme, legible con daltonismo).
ESCALA = ("#440154", "#3b528b", "#21908d", "#5dc863", "#fde725")


def _rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def color_de_escala(t):
    """Color de la escala para t entre 0 y 1."""
    t = min(1.0, max(0.0, t)) * (len(ESCALA) - 1)
    i = min(int(t), len(ESCALA) - 2)
    a, b = _rgb(ESCALA[i]), _rgb(ESCALA[i + 1])
    mezcla = [round(x + (y - x) * (t - i)) for x, y in zip(a, b)]
    return "#%02x%02x%02x" % tuple(mezcla)


def _luminancia(hexa):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in _rgb(hexa))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def color_de_texto(fondo):
    """Blanco o negro, el que más contraste da sobre `fondo` (WCAG)."""
    contraste_blanco = 1.05 / (_luminancia(fondo) + 0.05)
    contraste_negro = (_luminancia(fondo) + 0.05) / 0.05
    return "#ffffff" if contraste_blanco >= contraste_negro else "#000000"


def _numero(valor, decimales=1):
    """Número con coma decimal, como se escribe en español."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def _porcentaje(relativa, decimales=1):
    return "—" if relativa is None else _numero(relativa * 100, decimales)


def _log10(absoluta):
    return None if not absoluta or absoluta <= 0 else math.log10(absoluta)


def _media(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def _zona_de(canal):
    return next((z for z, canales in REGIONES.items() if canal in canales), None)


def resumen_analisis(resultado):
    """Datos de la pantalla de análisis, o None si el JSON no trae potencia."""
    potencia = (resultado or {}).get("potencia")
    if not potencia or not potencia.get("por_canal"):
        return None

    bandas = [{"clave": b, "nombre": NOMBRE_BANDA.get(b, b.capitalize()),
               "rango": f"{rango[0]:g}–{rango[1]:g} Hz"}
              for b, rango in potencia["bandas_hz"].items()]
    claves = [b["clave"] for b in bandas]
    por_canal = potencia["por_canal"]
    por_region = potencia.get("por_region", {})

    # --- Electrodos ---------------------------------------------------------
    electrodos = []
    for canal in CANALES_EPOC:
        if canal not in por_canal or canal not in POSICIONES:
            continue
        datos = por_canal[canal]
        valido = bool(datos.get("valido"))
        electrodos.append({
            "canal": canal, "zona": _zona_de(canal), "valido": valido,
            "relativa": {b: datos[b]["relativa"] if valido else None for b in claves},
            "log_abs": {b: _log10(datos[b]["absoluta_v2"]) if valido else None for b in claves},
        })
    validos = [e for e in electrodos if e["valido"]]

    # --- Toda la cabeza y zonas ----------------------------------------------
    cabeza = {b: _media([e["relativa"][b] for e in validos]) for b in claves}
    zonas = []
    for zona, canales in REGIONES.items():
        datos = por_region.get(zona, {})
        zonas.append({
            "clave": zona, "nombre": zona.capitalize(),
            "n_validos": datos.get("n_canales_validos", 0), "n_total": len(canales),
            "relativa": {b: (datos.get(b) or {}).get("relativa") for b in claves},
            "log_abs": {b: (datos.get(b) or {}).get("log10_absoluta_v2") for b in claves},
        })

    # Textos para las tablas (coma decimal; «—» donde no hay dato).
    for fila in electrodos + zonas:
        fila["rel_texto"] = [_porcentaje(fila["relativa"][b]) for b in claves]
        fila["abs_texto"] = [("—" if fila["log_abs"][b] is None else _numero(fila["log_abs"][b], 2))
                             for b in claves]
    cabeza_texto = [_porcentaje(cabeza[b]) for b in claves]

    # --- Gráfica -------------------------------------------------------------
    def serie(nombre, color, valores):
        return {"etiqueta": nombre, "color": color,
                "valores": [None if valores[b] is None else round(valores[b] * 100, 2)
                            for b in claves]}
    grafica = {
        "bandas": [b["nombre"] for b in bandas],
        "series": [serie("Toda la cabeza (media de los electrodos válidos)", COLOR_CABEZA, cabeza)]
                  + [serie(z["nombre"], COLOR_ZONA.get(z["clave"], "#888888"), z["relativa"])
                     for z in zonas],
    }

    # --- Mapas, uno por banda ------------------------------------------------
    mapas = []
    for banda in bandas:
        b = banda["clave"]
        valores = [e["relativa"][b] for e in validos if e["relativa"][b] is not None]
        minimo, maximo = (min(valores), max(valores)) if valores else (None, None)
        puntos = []
        for e in electrodos:
            cx, cy = punto_svg(e["canal"])
            punto = {"canal": e["canal"], "cx": cx, "cy": cy}
            valor = e["relativa"][b]
            if valor is None:
                punto.update(forma="rombo", clase="descartado", simbolo="✖",
                             titulo=f"{e['canal']}: descartado, sin dato")
            else:
                t = 0.5 if maximo == minimo else (valor - minimo) / (maximo - minimo)
                fondo = color_de_escala(t)
                punto.update(
                    forma="circulo", clase="valor", simbolo=_numero(valor * 100),
                    relleno=fondo, texto_color=color_de_texto(fondo),
                    titulo=f"{e['canal']}: {_numero(valor * 100)} % de la potencia "
                           f"({banda['nombre'].lower()})")
            puntos.append(punto)
        mapas.append({
            "banda": banda, "puntos": puntos,
            "minimo": None if minimo is None else _numero(minimo * 100),
            "maximo": None if maximo is None else _numero(maximo * 100),
            "degradado": "linear-gradient(to right, " + ", ".join(ESCALA) + ")",
        })

    # --- Avisos --------------------------------------------------------------
    metadatos = resultado.get("metadatos", {})
    parametros = resultado.get("parametros_aplicados", {})
    avisos = []
    nivel, texto = nivel_de_fiabilidad(metadatos.get("n_canales_buenos"))
    if texto:
        avisos.append({"nivel": nivel, "texto": texto})
    paso_banda = parametros.get("banda_hz")
    inicio_delta = potencia["bandas_hz"].get("delta", [None])[0]
    if paso_banda and inicio_delta is not None and paso_banda[0] > inicio_delta:
        avisos.append({"nivel": "aviso", "texto":
                       f"El paso banda empieza en {paso_banda[0]:g} Hz, por encima del inicio "
                       f"de delta ({inicio_delta:g} Hz): la potencia delta queda casi eliminada "
                       f"por el propio filtro. Es lo esperable."})
    sin_electrodos = [z["nombre"] for z in zonas if not z["n_validos"]]
    if sin_electrodos:
        avisos.append({"nivel": "aviso", "texto":
                       "Sin electrodos válidos en: " + ", ".join(sin_electrodos) +
                       ". No hay valor para esa zona."})

    return {
        "bandas": bandas,
        "banda_inicial": BANDA_POR_DEFECTO if BANDA_POR_DEFECTO in claves else claves[0],
        "electrodos": electrodos, "zonas": zonas, "cabeza": cabeza,
        "cabeza_texto": cabeza_texto,
        "grafica": grafica, "mapas": mapas, "avisos": avisos,
        "n_validos": len(validos), "n_total": len(electrodos),
    }
