"""Configuración: datos fuera del repo, lectura de .env y EEG-Library instalada."""

import os
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.settings import carpeta_de_datos, leer_env

BASE = settings.BASE_DIR


# ---------------------------------------------------------------------------
# Carpeta de datos
# ---------------------------------------------------------------------------

def test_por_defecto_al_lado_del_repo():
    assert carpeta_de_datos("", BASE) == (BASE.parent / "EEG-Platform-datos").resolve()


def test_carpeta_configurada(tmp_path):
    assert carpeta_de_datos(str(tmp_path), BASE) == tmp_path.resolve()


@pytest.mark.parametrize("dentro", [".", "datos", "grabaciones/subidas"])
def test_carpeta_dentro_del_repo_no_arranca(dentro):
    with pytest.raises(ImproperlyConfigured, match="dentro del repositorio"):
        carpeta_de_datos(str(BASE / dentro), BASE)


def test_base_de_datos_y_archivos_fuera_del_repo():
    for ruta in (Path(settings.DATABASES["default"]["NAME"]), Path(settings.MEDIA_ROOT)):
        assert settings.DATOS_DIR in ruta.parents
        assert BASE not in ruta.resolve().parents


# ---------------------------------------------------------------------------
# .env
# ---------------------------------------------------------------------------

def test_leer_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# comentario\n\nPRUEBA_A=uno\nPRUEBA_B = \"dos con espacios\"\n"
        "PRUEBA_C=ya_definida\nlinea sin igual\n", encoding="utf-8")
    for clave in ("PRUEBA_A", "PRUEBA_B"):
        monkeypatch.delenv(clave, raising=False)
    monkeypatch.setenv("PRUEBA_C", "del_entorno")
    leer_env(env)
    assert os.environ["PRUEBA_A"] == "uno"
    assert os.environ["PRUEBA_B"] == "dos con espacios"
    # El entorno manda sobre el archivo.
    assert os.environ["PRUEBA_C"] == "del_entorno"
    for clave in ("PRUEBA_A", "PRUEBA_B"):
        monkeypatch.delenv(clave)


def test_leer_env_sin_archivo(tmp_path):
    leer_env(tmp_path / "no_existe.env")


# ---------------------------------------------------------------------------
# EEG-Library
# ---------------------------------------------------------------------------

def test_eeg_library_instalada_en_editable():
    import eeg_library
    ruta = Path(eeg_library.__file__).resolve()
    assert (BASE.parent / "EEG-Library" / "src") in ruta.parents


def test_modelos_disponibles():
    from eeg_library import listar_modelos
    assert listar_modelos() == ["c1_oa_oc_logistica", "c2_reposo_tarea_logistica",
                                "c3_tareas_logistica"]
