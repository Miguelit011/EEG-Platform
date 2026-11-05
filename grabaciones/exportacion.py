"""
Exportación a CSV: una fila por grabación procesada.

Las columnas y sus valores salen de un único sitio (`_celdas`), así que el
encabezado, las filas y `docs/COLUMNAS_CSV.md` no pueden desincronizarse. Los
valores son los mismos que se ven en pantalla: salen de `resumen_analisis` y
`resumen_calidad`, no se recalculan.

Formato pensado para Excel en España (`settings.CSV_*`): separador `;`, decimal
`,` y UTF-8 con BOM, para que Excel abra bien las tildes sin asistente.
"""

import csv
import io
import re
from collections import namedtuple

from django.conf import settings

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.procesado.bands import BANDAS_DEFECTO
from eeg_library.procesado.matrix import REGIONES

from grabaciones import modelos, tiempo_en_tarea
from grabaciones.analisis_espectral import resumen_analisis
from grabaciones.calidad import resumen_calidad

Columna = namedtuple("Columna", "nombre seccion descripcion unidad")

BANDAS = list(BANDAS_DEFECTO)
DECIMALES_REL = 6
DECIMALES_LOGABS = 4
DECIMALES_DURACION = 2


def _numero(valor, decimales):
    """Número con el decimal de `settings.CSV_DECIMAL`; vacío si no hay dato."""
    if valor is None:
        return ""
    return f"{valor:.{decimales}f}".replace(".", settings.CSV_DECIMAL)


def _texto(valor):
    """
    Texto seguro para una hoja de cálculo: si empieza por un carácter que Excel
    toma por una fórmula (nombres de archivo o condiciones escritas por el usuario),
    se antepone una comilla.
    """
    valor = "" if valor is None else str(valor)
    return "'" + valor if valor[:1] in ("=", "+", "-", "@", "\t", "\r") else valor


def _nombre_de_columna(texto):
    """Un nombre de clase como parte de un nombre de columna (sin tildes ni espacios)."""
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_") or "clase"


def _booleano(valor):
    return "" if valor is None else ("1" if valor else "0")


def _celdas(grabacion=None):
    """
    Genera `(Columna, valor ya formateado)` en el orden del CSV. Sin grabación,
    los valores van vacíos: sirve para conocer las columnas.
    """
    g = grabacion
    resultado = g.resultado if g is not None else None
    analisis = resumen_analisis(resultado) if resultado else None
    calidad = resumen_calidad(resultado) if resultado else None
    metadatos = (resultado or {}).get("metadatos", {})
    parametros = (resultado or {}).get("parametros_aplicados", {})
    banda = parametros.get("banda_hz") or [None, None]
    eliminadas = (parametros.get("ica") or {}).get("componentes_eliminadas")

    def col(nombre, seccion, descripcion, unidad, valor=""):
        return Columna(nombre, seccion, descripcion, unidad), valor

    ident = "Identificación"
    yield col("archivo", ident, "Nombre del archivo EDF subido", "texto",
              _texto(g.nombre_original) if g else "")
    yield col("lote", ident, "Número del lote en que se subió", "número", g.lote_id if g else "")
    yield col("condicion", ident, "Condición de la grabación (vacía si no se conoce)", "texto",
              _texto(g.condicion) if g else "")
    yield col("origen_condicion", ident,
              "De dónde sale la condición: nombre (del nombre del archivo), manual o vacia",
              "texto", g.origen_condicion if g else "")
    yield col("duracion_s", ident, "Duración del registro, antes de recortar los márgenes",
              "segundos", _numero(metadatos.get("duracion_s"), DECIMALES_DURACION))
    yield col("n_epocas", ident, "Ventanas (épocas) analizadas", "número",
              metadatos.get("n_epocas", ""))
    yield col("frecuencia_original_hz", ident, "Frecuencia de muestreo del archivo original",
              "Hz", _numero(metadatos.get("sfreq_original_hz"), 0))
    yield col("remuestreada", ident, "1 si el archivo se remuestreó a 256 Hz; 0 si no",
              "1/0", _booleano(metadatos.get("resampleado")) if metadatos else "")

    cal = "Calidad y procesado aplicado"
    yield col("electrodos_buenos", cal, "Electrodos buenos de los 14 del Emotiv", "número",
              calidad["n_buenos"] if calidad else "")
    yield col("electrodos_descartados", cal,
              "Electrodos descartados, separados por «|» (vacío si no hay ninguno)", "texto",
              "|".join(e["canal"] for e in calidad["electrodos"] if not e["bueno"])
              if calidad else "")
    yield col("referencia", cal, "Referencia pedida: car_condicional u original", "texto",
              parametros.get("referencia", ""))
    yield col("car_aplicada", cal, "1 si se aplicó la CAR; 0 si no (referencia original o "
              "menos de 6 electrodos buenos)", "1/0", _booleano(parametros.get("car_aplicada"))
              if parametros else "")
    yield col("banda_min_hz", cal, "Inicio del paso banda", "Hz", _numero(banda[0], 0))
    yield col("banda_max_hz", cal, "Fin del paso banda", "Hz", _numero(banda[1], 0))
    yield col("notch_hz", cal, "Frecuencia del filtro notch (vacío si no se aplicó)", "Hz",
              _numero(parametros.get("notch_hz"), 0))
    yield col("ica_n_componentes_eliminadas", cal,
              "Componentes de ICA eliminadas (artefactos oculares)", "número",
              "" if eliminadas is None else len(eliminadas))
    yield col("ica_componentes_eliminadas", cal,
              "Números de las componentes eliminadas, separados por «|»", "texto",
              "" if eliminadas is None else "|".join(str(c) for c in eliminadas))

    cab = "Toda la cabeza"
    for b in BANDAS:
        yield col(f"cabeza_{b}_rel", cab,
                  f"Potencia relativa en {b}: media de los electrodos válidos",
                  "proporción 0–1", _numero(analisis["cabeza"][b], DECIMALES_REL)
                  if analisis else "")

    zon = "Por zona"
    for zona in REGIONES:
        z = next((z for z in analisis["zonas"] if z["clave"] == zona), None) if analisis else None
        for b in BANDAS:
            yield col(f"zona_{zona}_{b}_rel", zon,
                      f"Potencia relativa en {b}, zona {zona} (vacío si no hay electrodos válidos)",
                      "proporción 0–1", _numero(z["relativa"][b], DECIMALES_REL) if z else "")
        for b in BANDAS:
            yield col(f"zona_{zona}_{b}_logabs", zon,
                      f"Potencia absoluta en {b}, zona {zona}", "log10 de V²",
                      _numero(z["log_abs"][b], DECIMALES_LOGABS) if z else "")

    ele = "Por electrodo"
    for canal in CANALES_EPOC:
        e = next((e for e in analisis["electrodos"] if e["canal"] == canal), None) \
            if analisis else None
        for b in BANDAS:
            yield col(f"rel_{canal}_{b}", ele,
                      f"Potencia relativa en {b}, electrodo {canal} (vacío si está descartado)",
                      "proporción 0–1", _numero(e["relativa"][b], DECIMALES_REL) if e else "")
        for b in BANDAS:
            yield col(f"logabs_{canal}_{b}", ele,
                      f"Potencia absoluta en {b}, electrodo {canal} (vacío si está descartado)",
                      "log10 de V²", _numero(e["log_abs"][b], DECIMALES_LOGABS) if e else "")

    tra = "Trazabilidad"
    yield col("version_eeg_library", tra, "Versión de EEG-Library que procesó la grabación",
              "texto", (metadatos.get("versiones") or {}).get("eeg_library", ""))
    yield col("fecha_analisis", tra, "Fecha y hora del procesado", "texto",
              metadatos.get("fecha_analisis", ""))

    # Modelos (al final, para no mover las columnas anteriores). Las celdas van vacías si
    # el modelo no se aplica a esta grabación o no está disponible con sus parámetros.
    mod = "Modelos"
    tarjetas = ({t["nombre"]: t for t in modelos.aplicar(resultado, g.condicion)["tarjetas"]}
                if g is not None and resultado else {})
    for nombre, ficha in modelos.registrados():
        t = tarjetas.get(nombre)
        activo = bool(t) and t["estado"] == "ok"
        titulo = ficha.get("titulo", ficha["id"])
        yield col(f"{ficha['id']}_clase", mod,
                  f"{titulo}: clase predicha (vacía si el modelo no se aplica a la grabación)",
                  "texto", t["clase"] if activo else "")
        probabilidades = {p["nombre"]: p["p"] for p in t["probabilidades"]} if activo else {}
        for clase in ficha["clases"]:
            yield col(f"{ficha['id']}_p_{_nombre_de_columna(clase['nombre'])}", mod,
                      f"{titulo}: probabilidad de la clase {clase['nombre']}", "proporción 0–1",
                      _numero(probabilidades.get(clase["nombre"]), DECIMALES_REL))
        yield col(f"{ficha['id']}_condicion_estimada", mod,
                  f"{titulo}: 1 si se aplicó porque la condición de la grabación no se conocía "
                  f"y se estimó; 0 si se conocía (vacía si el modelo no se aplica)", "1/0",
                  _booleano(t["origen"] in ("estimada", "estimadora")) if activo else "")

    # Tiempo en tarea (solo PASAT y PVTB). Son los valores de la librería, sin el suavizado de la
    # pantalla: la ρ y el veredicto de tercios son los mismos cálculos que la cifra del test.
    tt = "Tiempo en tarea"
    p = tiempo_en_tarea.para_csv(g) if g is not None else None
    tercios = p["tercios"] if p else {}
    yield col("tiempo_en_tarea_rho", tt,
              "Tendencia a lo largo de la grabación: correlación de Spearman entre la puntuación "
              "de cada ventana y su momento (vacía si no es PASAT ni PVTB)", "−1 a 1",
              _numero(p["rho"], DECIMALES_REL) if p else "")
    yield col("tiempo_en_tarea_p_primer_tercio", tt,
              "Probabilidad de «último tercio» que el modelo da a la media del primer tercio",
              "proporción 0–1", _numero(tercios.get("p_primero"), DECIMALES_REL))
    yield col("tiempo_en_tarea_p_ultimo_tercio", tt,
              "Probabilidad de «último tercio» que el modelo da a la media del último tercio",
              "proporción 0–1", _numero(tercios.get("p_ultimo"), DECIMALES_REL))
    yield col("tiempo_en_tarea_final_mayor", tt,
              "1 si el último tercio se parece más al final de la tarea que el primero; 0 si no "
              "(vacía si empatan o no se aplica)", "1/0",
              _booleano(tercios["final_mayor"]) if p and tercios["final_mayor"] is not None else "")
    e = tiempo_en_tarea.para_csv(g, modelo="eegnet") if g is not None else None
    yield col("tiempo_en_tarea_eegnet_rho", tt,
              "Lo mismo que tiempo_en_tarea_rho, con la red neuronal EEGNet (vacía si no es PASAT ni "
              "PVTB, o si la grabación se procesó antes de que la plataforma incluyera EEGNet)",
              "−1 a 1", _numero(e["rho"], DECIMALES_REL) if e else "")
    yield col("tiempo_en_tarea_eegnet_final_mayor", tt,
              "1 si, según EEGNet, el último tercio se parece más al final de la tarea que el "
              "primero; 0 si no (vacía si empatan o no se aplica)", "1/0",
              _booleano(e["tercios"]["final_mayor"]) if e and e["tercios"]["final_mayor"] is not None else "")


def columnas():
    """Las columnas del CSV, en orden."""
    return [c for c, _ in _celdas()]


def csv_de(grabaciones):
    """El CSV (bytes, con la codificación de `settings.CSV_CODIFICACION`) de las grabaciones."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=settings.CSV_SEPARADOR, lineterminator="\r\n")
    escritor.writerow(c.nombre for c in columnas())
    for g in grabaciones:
        escritor.writerow(valor for _, valor in _celdas(g))
    return salida.getvalue().encode(settings.CSV_CODIFICACION)


def nombre_de_archivo_seguro(texto):
    """Nombre de archivo válido en Windows y sin caracteres raros en la cabecera HTTP."""
    limpio = "".join(c if c.isalnum() and c.isascii() or c in "-_." else "_" for c in texto)
    return limpio.strip("._") or "grabacion"


def documentacion_markdown():
    """Contenido de `docs/COLUMNAS_CSV.md`, generado a partir de las columnas."""
    lineas = [
        "# Columnas del CSV",
        "",
        "Generado con `manage.py documentar_csv`; no se edita a mano. Un test comprueba que "
        "coincide con las columnas que exporta la plataforma.",
        "",
        "## Formato",
        "",
        "- Una fila por grabación procesada. El CSV de una grabación y el de un lote tienen "
        "las mismas columnas.",
        "- Separador de columnas `;`, decimal `,`, codificación UTF-8 con BOM y saltos de "
        "línea de Windows: es lo que Excel en español abre directamente. Se cambia en "
        "`settings` (`CSV_SEPARADOR`, `CSV_DECIMAL`, `CSV_CODIFICACION`).",
        "- Una celda vacía significa «sin dato»: electrodo descartado, zona sin electrodos "
        "válidos o parámetro que no se aplicó. Nunca se escribe un cero en su lugar.",
        "- Los nombres de columna no llevan tildes ni espacios, para que SPSS y R los "
        "acepten como nombres de variable. Son estables: no cambian entre versiones.",
        "- Los valores de potencia son los mismos que se ven en pantalla. La potencia "
        "**relativa** es la proporción (de 0 a 1) de la potencia total de 1 a 30 Hz que "
        "cae en la banda; la **absoluta** va en log10 de V².",
        "- «Toda la cabeza» es la media de la potencia relativa de los electrodos válidos.",
        "- Los electrodos descartados no tienen valor de potencia: se calculó con señal que "
        "no pasó por CAR ni ICA y no es comparable.",
        "- Bandas: " + ", ".join(f"`{b}` ({r[0]:g}–{r[1]:g} Hz)" for b, r in BANDAS_DEFECTO.items())
        + ". Zonas: " + ", ".join(f"`{z}`" for z in REGIONES) + ".",
        "",
        f"Total: {len(columnas())} columnas.",
    ]
    seccion = None
    for c in columnas():
        if c.seccion != seccion:
            seccion = c.seccion
            lineas += ["", f"## {seccion}", "", "| Columna | Significado | Unidad |", "|---|---|---|"]
        descripcion = c.descripcion.replace("|", "\\|")   # la barra rompería la tabla
        lineas.append(f"| `{c.nombre}` | {descripcion} | {c.unidad} |")
    return "\n".join(lineas) + "\n"
