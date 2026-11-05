"""Ayudas comunes de los tests de las pantallas: el fixture de la Fase 0 y variantes suyas."""

import copy
import json
import re
from pathlib import Path

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.procesado.matrix import REGIONES

from grabaciones.models import Grabacion, Lote

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "analisis_grabacion.json")
                     .read_text(encoding="utf-8"))
MOTIVO = "Amplitud excesiva (z=5.00 > 3.00)"


def variante(descartados=(), car=True, eliminadas=(), referencia="car_condicional",
             banda_hz=None):
    """
    El fixture con otros electrodos descartados, otra CAR, más componentes de ICA u otro
    paso banda. La calidad y la validez de la potencia por electrodo se mantienen
    coherentes; los valores de potencia de los electrodos que siguen siendo buenos son
    los del fixture. Una zona sin electrodos válidos pasa a valores nulos, como en la
    librería.
    """
    r = copy.deepcopy(FIXTURE)
    for canal, datos in r["calidad"].items():
        malo = canal in descartados
        datos["estado"] = "descartado" if malo else "bueno"
        datos["motivo"] = MOTIVO if malo else None
        r["potencia"]["por_canal"][canal]["valido"] = not malo
    for zona, canales in REGIONES.items():
        region = r["potencia"]["por_region"][zona]
        region["n_canales_validos"] = sum(c not in descartados for c in canales)
        if not region["n_canales_validos"]:
            for banda in r["potencia"]["bandas_hz"]:
                region[banda] = {"log10_absoluta_v2": None, "relativa": None}
    r["metadatos"]["n_canales_buenos"] = len(CANALES_EPOC) - len(descartados)
    r["parametros_aplicados"]["car_aplicada"] = car
    r["parametros_aplicados"]["referencia"] = referencia
    r["parametros_aplicados"]["ica"]["componentes_eliminadas"] = list(eliminadas)
    if banda_hz:
        r["parametros_aplicados"]["banda_hz"] = list(banda_hz)
    return r


def grabacion_con(resultado, estado="procesada"):
    lote = Lote.objects.create()
    return Grabacion.objects.create(
        lote=lote, nombre_original="ejemplo_OA.edf", condicion="OA", estado=estado,
        duracion_s=137.0, sfreq_original_hz=256.0, resultado=resultado,
        n_canales_buenos=(resultado or {}).get("metadatos", {}).get("n_canales_buenos"))


def sin_bloque_de_modelos(html):
    """
    La página sin el bloque de modelos. La palabra «fatiga» solo puede aparecer ahí, en el
    aviso fijo que dice que los modelos no la miden, y en el aviso de la pestaña Tiempo en tarea
    («no el nivel de fatiga de la persona»); en cualquier otro sitio está prohibida.
    """
    return re.sub(r'<section class="bloque-modelos" id="modelos".*?</section>', "", html, flags=re.S)


def mapa(html):
    """El primer mapa SVG de la cabeza de la página."""
    return re.search(r'<svg class="mapa-cabeza".*?</svg>', html, re.S).group(0)


def mapas(html):
    """Todos los mapas SVG de la cabeza de la página."""
    return re.findall(r'<svg class="mapa-cabeza".*?</svg>', html, re.S)