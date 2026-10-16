"""Condición de una grabación (OA, OC, STROOP...) a partir del nombre del archivo."""

import re

from django.conf import settings


def condicion_desde_nombre(nombre, patron=None):
    """
    Devuelve la condición que indica el nombre del archivo, o "" si no se reconoce.

    El patrón es una expresión regular (sin distinguir mayúsculas). Si tiene un
    grupo, la condición es ese grupo; si no, toda la coincidencia. Por defecto
    es `settings.PATRON_CONDICION`.
    """
    coincidencia = re.search(patron or settings.PATRON_CONDICION, nombre, re.IGNORECASE)
    if not coincidencia:
        return ""
    texto = coincidencia.group(1) if coincidencia.groups() else coincidencia.group(0)
    return (texto or "").strip().upper()
