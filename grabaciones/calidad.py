"""
Pantalla de calidad: convierte el JSON guardado de una grabación en lo que se dibuja.

Solo usa el JSON que devolvió `analizar_grabacion` (no toca la base de datos ni
la librería), así que se prueba con el fixture de la Fase 0.
"""

import re

from eeg_library.preprocesado.quality import CANALES_EPOC

from grabaciones.geometria import geometria_visor

# Umbrales de aviso. Son los de la librería, que no los expone como constantes:
# `aplicar_car` omite la CAR con menos de 6 canales buenos y avisa por debajo de
# 8 (referencing.py), y `evaluar_calidad` los repite como «resultados no
# fiables (mínimo recomendado: 6)» y «se recomiendan al menos 8». La librería
# solo avisa: no descarta la grabación. Un test comprueba que siguen coincidiendo.
MINIMO_FIABLE = 6
RECOMENDADOS = 8

# Posición de cada electrodo en el mapa, vista desde arriba, nariz hacia arriba.
# x: -1 izquierda … +1 derecha; y: +1 frente … -1 nuca (cabeza = círculo de radio 1).
POSICIONES = {
    "AF3": (-0.30, 0.70), "AF4": (0.30, 0.70),
    "F7": (-0.70, 0.46), "F8": (0.70, 0.46),
    "F3": (-0.34, 0.40), "F4": (0.34, 0.40),
    "FC5": (-0.56, 0.20), "FC6": (0.56, 0.20),
    "T7": (-0.82, 0.00), "T8": (0.82, 0.00),
    "P7": (-0.62, -0.45), "P8": (0.62, -0.45),
    "O1": (-0.28, -0.80), "O2": (0.28, -0.80),
}

# Geometría del dibujo SVG (viewBox 0 0 400 440). Los electrodos (radio ~20 px) no se tocan.
CENTRO = (200, 235)
RADIO = 165

_AYUDA_MOTIVO = (
    ("CQ medio bajo", "El casco indicó mal contacto del electrodo durante la grabación. En la próxima, "
                      "comprueba que apoya bien y que su fieltro está húmedo."),
    ("Exceso de muestras malas", "Durante más de una quinta parte del registro el casco "
                                 "marcó el contacto como malo. Conviene revisar su colocación."),
    ("Señal plana", "El electrodo no registró señal (desconectado o sin contacto). "
                    "Comprueba que está bien enchufado."),
    ("Amplitud excesiva", "La señal tiene mucha más amplitud que la de los demás "
                          "electrodos (ruido o artefactos). Suele deberse a movimiento o a mal contacto."),
)


def nivel_de_fiabilidad(n_buenos):
    """
    Nivel de aviso según los electrodos buenos, igual que en la librería.

    Devuelve `(nivel, texto)`: `normal` (8 o más, sin texto), `aviso` (6–7) o
    `critico` (menos de 6).
    """
    if n_buenos is None:
        return "normal", ""
    if n_buenos < MINIMO_FIABLE:
        return "critico", (f"Solo {n_buenos} electrodos buenos: resultados no fiables "
                           f"(mínimo recomendado: {MINIMO_FIABLE}).")
    if n_buenos < RECOMENDADOS:
        return "aviso", (f"{n_buenos} electrodos buenos "
                         f"(se recomiendan al menos {RECOMENDADOS}).")
    return "normal", ""


def _coma(texto):
    """Coma decimal en los números de un texto de la librería («z=19.84» pasa a «z=19,84»)."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", texto or "")


def _ayuda(motivo):
    for inicio, texto in _AYUDA_MOTIVO:
        if motivo and motivo.startswith(inicio):
            return texto
    return ""


def punto_svg(canal):
    """Píxeles del SVG, enteros: con la localización en español un decimal saldría con coma."""
    x, y = POSICIONES[canal]
    return round(CENTRO[0] + x * RADIO), round(CENTRO[1] - y * RADIO)


def _referencia_texto(parametros):
    if parametros.get("referencia") == "original":
        return "Original del casco (sin re-referenciar)"
    return "CAR condicional"


def _car_texto(parametros):
    if parametros.get("car_aplicada"):
        return "Sí, aplicada"
    if parametros.get("referencia") == "original":
        return "No (referencia original elegida para el lote)"
    return ("No: con menos de %d electrodos buenos la librería omite la CAR."
            % MINIMO_FIABLE)


def _ica_texto(ica):
    eliminadas = ica.get("componentes_eliminadas") or []
    if not eliminadas:
        return "ninguna eliminada"
    lista = ", ".join(str(c) for c in eliminadas)
    return f"{len(eliminadas)} {'eliminada' if len(eliminadas) == 1 else 'eliminadas'} (nº {lista})"


def _epocas_texto(metadatos, parametros):
    n = metadatos.get("n_epocas", "—")
    duracion = parametros.get("epocado", {}).get("duracion_s")
    return f"{n} ventanas de {duracion:g} s" if duracion else str(n)


def resumen_calidad(resultado):
    """
    Datos de la pantalla de calidad a partir del JSON de una grabación, o None
    si el JSON no trae calidad por canal.
    """
    calidad = (resultado or {}).get("calidad")
    if not calidad:
        return None

    electrodos = []
    for canal in CANALES_EPOC:
        if canal not in calidad or canal not in POSICIONES:
            continue
        datos = calidad[canal]
        bueno = datos.get("estado") == "bueno"
        cx, cy = punto_svg(canal)
        electrodos.append({
            "canal": canal,
            "zona": (datos.get("region") or "").capitalize() or "—",
            "bueno": bueno,
            "estado": "Bueno" if bueno else "Descartado",
            "motivo": _coma(datos.get("motivo")),
            "ayuda": "" if bueno else _ayuda(datos.get("motivo")),
            "cx": cx, "cy": cy,
            # Para el mapa (plantilla reutilizable): forma y símbolo, además del color.
            "forma": "circulo" if bueno else "rombo",
            "clase": "bueno" if bueno else "descartado",
            "simbolo": "✔" if bueno else "✖",
            "titulo": (f"{canal}: bueno" if bueno else
                       f"{canal}: descartado. {_coma(datos.get('motivo'))}".strip()),
        })

    n_total = len(electrodos)
    n_buenos = sum(e["bueno"] for e in electrodos)
    descartados = [e["canal"] for e in electrodos if not e["bueno"]]
    nivel, aviso = nivel_de_fiabilidad(n_buenos)
    if not descartados:
        frase = f"Los {n_total} electrodos son aprovechables."
    elif len(descartados) == 1:
        frase = f"Se ha descartado 1 electrodo: {descartados[0]}."
    else:
        frase = f"Se han descartado {len(descartados)} electrodos: {', '.join(descartados)}."

    metadatos = resultado.get("metadatos", {})
    parametros = resultado.get("parametros_aplicados", {})
    banda = parametros.get("banda_hz")
    notch = parametros.get("notch_hz")
    pipeline = [
        ("Referencia", _referencia_texto(parametros)),
        ("CAR", _car_texto(parametros)),
        ("ICA", f"{parametros.get('ica', {}).get('n_componentes', '—')} componentes ajustadas, "
                f"{_ica_texto(parametros.get('ica', {}))}"),
        ("Paso banda", f"{banda[0]:g}–{banda[1]:g} Hz" if banda else "—"),
        ("Notch", f"{notch:g} Hz" if notch else "No aplicado"),
        ("Épocas analizadas", _epocas_texto(metadatos, parametros)),
    ]

    # Datos del mapa con el cerebro real (se pinta en el navegador; el SVG queda de respaldo).
    mapa_real = {
        "geometria": geometria_visor(),
        "titular": f"{n_buenos} de {n_total} electrodos buenos",
        "electrodos": [{"canal": e["canal"], "bueno": e["bueno"]} for e in electrodos],
    }

    return {
        "mapa_real": mapa_real,
        "electrodos": electrodos,
        "n_buenos": n_buenos,
        "n_total": n_total,
        "titular": f"{n_buenos} de {n_total} electrodos buenos",
        "frase": frase,
        "nivel": nivel,
        "aviso": aviso,
        "pipeline": pipeline,
        "car_omitida": (parametros.get("referencia") == "car_condicional"
                        and not parametros.get("car_aplicada")),
    }
