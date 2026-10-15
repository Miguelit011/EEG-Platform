"""
Configuración de EEG-Platform.

Uso local en un solo equipo: sin login, sin servidor externo, sin CDN.

Los datos (base SQLite, EDF subidos y resultados) viven en una carpeta
**fuera del repo**, porque son de participantes menores de edad y nunca deben
llegar a git. Se configura con `EEG_PLATFORM_DATOS` en `.env` o en el entorno.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def leer_env(ruta):
    """
    Lee un archivo `.env` sencillo (líneas `CLAVE=valor`, `#` comenta).

    Las variables ya definidas en el entorno tienen prioridad. Se hace a mano
    para no añadir una dependencia por diez líneas.
    """
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def carpeta_de_datos(valor, base_dir):
    """
    Resuelve la carpeta de datos y comprueba que está fuera del repo.

    Un valor vacío usa la carpeta `EEG-Platform-datos` al lado del repo.
    """
    carpeta = Path(valor) if valor else base_dir.parent / "EEG-Platform-datos"
    carpeta = carpeta.resolve()
    if carpeta == base_dir or base_dir in carpeta.parents:
        raise ImproperlyConfigured(
            f"La carpeta de datos ({carpeta}) está dentro del repositorio. "
            f"Los datos de participantes no pueden ir a git: configura "
            f"EEG_PLATFORM_DATOS con una carpeta fuera de {base_dir}."
        )
    return carpeta


leer_env(BASE_DIR / ".env")

DATOS_DIR = carpeta_de_datos(os.environ.get("EEG_PLATFORM_DATOS", ""), BASE_DIR)
DATOS_DIR.mkdir(parents=True, exist_ok=True)

# Solo uso local: la clave no protege nada expuesto a la red.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-uso-local-cambiar-si-se-expone")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Sin admin ni auth: login y usuarios están fuera de alcance.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "grabaciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATOS_DIR / "db.sqlite3",
    }
}

# EDF subidos y resultados, también fuera del repo.
MEDIA_ROOT = DATOS_DIR / "archivos"
MEDIA_URL = "/archivos/"

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# JS y CSS servidos desde static/: la web funciona sin internet.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
