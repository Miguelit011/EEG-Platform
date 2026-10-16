import pytest

from grabaciones.condicion import condicion_desde_nombre


@pytest.mark.parametrize("nombre, esperada", [
    ("sub-C4F123_ses-M5_task-STROOP_eeg.edf", "STROOP"),
    ("sub-C1F081_ses-M2_task-OA_eeg.edf", "OA"),
    ("sub-C1F081_ses-M2_task-oc_eeg.edf", "OC"),          # sin distinguir mayúsculas
    ("sub-C1F081_ses-M2_task-PVSAT_eeg.edf", "PVSAT"),
    ("grabacion_juan.edf", ""),                           # nombre sin condición
    ("sub-C1F081_ses-M2_task-DESCONOCIDA_eeg.edf", ""),   # condición fuera del patrón
    ("", ""),
])
def test_patron_por_defecto(nombre, esperada):
    assert condicion_desde_nombre(nombre) == esperada


def test_patron_configurable_con_grupo():
    assert condicion_desde_nombre("p01_correr_pre.edf", r"_(correr|andar)_") == "CORRER"


def test_patron_configurable_sin_grupo():
    assert condicion_desde_nombre("p01_pre.edf", r"pre|post") == "PRE"


def test_el_patron_sale_de_settings(settings):
    settings.PATRON_CONDICION = r"cond(\d)"
    assert condicion_desde_nombre("a_cond3.edf") == "3"
