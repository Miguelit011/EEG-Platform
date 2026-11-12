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
    # `grabaciones` va antes de `staticfiles` para que su `runserver` (que desactiva la caché
    # de los archivos estáticos) sustituya al de Django.
    "grabaciones",
    "django.contrib.staticfiles",
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
                "grabaciones.contexto.navegacion",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATOS_DIR / "db.sqlite3",
        # La web y el procesador escriben a la vez en la misma base: WAL deja
        # leer mientras se escribe y el tiempo de espera evita «database is locked».
        "OPTIONS": {
            "timeout": 30,
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}

# EDF subidos y resultados, también fuera del repo.
MEDIA_ROOT = DATOS_DIR / "archivos"
MEDIA_URL = "/archivos/"

# Subida de grabaciones. Un lote puede traer cientos de EDF de una vez.
DATA_UPLOAD_MAX_NUMBER_FILES = 1000

# La condición (OA, OC, STROOP...) se lee del nombre del archivo con este patrón
# (regex, sin distinguir mayúsculas; si tiene un grupo, la condición es el grupo).
# Es un metadato opcional: si no coincide, la condición queda vacía.
PATRON_CONDICION = os.environ.get(
    "EEG_PLATFORM_PATRON_CONDICION",
    r"task-(OA|OC|STROOP|PASAT|PVTB|MSIT|PVSAT)",
)

# Modelos que se muestran en la pantalla de análisis y se exportan al CSV. Para añadir
# uno, copia su ficha .json y su .joblib a la carpeta de modelos (MODELOS_DIR) y añade
# aquí una línea con el nombre de la ficha (ver docs/AÑADIR_UN_MODELO.md). Los tres
# primeros son los del estudio, empaquetados en EEG-Library.
MODELOS = [
    "c1_oa_oc_logistica",
    "c2_reposo_tarea_logistica",
    "c3_tareas_logistica",
]
MODELOS_DIR = DATOS_DIR / "modelos"
MODELOS_DIR.mkdir(parents=True, exist_ok=True)

# Un modelo que contradice la condición del archivo se destaca si su probabilidad para
# la clase predicha es al menos esta.
UMBRAL_DISCREPANCIA = 0.8

# Formato del CSV exportado: el de Excel en español (separador `;`, decimal `,`,
# UTF-8 con BOM para que abra bien las tildes). Si en otro equipo se prefiere el
# formato internacional: CSV_SEPARADOR = ",", CSV_DECIMAL = ".".
CSV_SEPARADOR = ";"
CSV_DECIMAL = ","
CSV_CODIFICACION = "utf-8-sig"

# Procesado en segundo plano (`manage.py procesar`): procesos en paralelo. Si no
# se fija, el procesador lo calcula en cada equipo según sus hilos y su memoria
# libre (ver grabaciones/recursos.py), porque la plataforma se usará en
# portátiles distintos. Con resultados idénticos, medido con 12 EDF reales:
# 1 proceso → 37 s, 2 → 21 s, 4 → 14,5 s, 6 → 12,7 s.
try:
    PROCESOS = int(os.environ.get("EEG_PLATFORM_PROCESOS") or 0) or None
except ValueError:
    PROCESOS = -1   # no es un número: mismo aviso que un valor fuera de rango
if PROCESOS is not None and PROCESOS < 1:
    raise ImproperlyConfigured(
        "EEG_PLATFORM_PROCESOS debe ser un número entero, al menos 1 "
        f"(ahora vale «{os.environ.get('EEG_PLATFORM_PROCESOS')}»).")

# Si el procesador no da señales en estos segundos, la lista avisa de que está parado.
PROCESADOR_LATIDO_CADUCA_S = 15

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# JS y CSS servidos desde static/: la web funciona sin internet.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
