#!/usr/bin/env bash
# Instala EEG-Platform en Linux o macOS: entorno de Python, dependencias, configuración y
# base de datos. Hace lo mismo que instalar.bat en Windows.
# Se ejecuta una sola vez (y de nuevo si se actualiza la plataforma). Necesita internet.
#   Linux:  bash instalar.sh            macOS: doble clic en instalar.command
set -u
cd "$(dirname "$0")" || exit 1

pausa() {
    # Con doble clic en macOS la ventana se quedaría sin que dé tiempo a leerla.
    if [ "${EEG_PLATFORM_PAUSA:-0}" = "1" ]; then
        echo
        read -r -p "Pulsa Intro para cerrar esta ventana. " _
    fi
}

fallo() {
    echo
    echo "============================================================"
    echo "  La instalación no se ha podido completar."
    echo "  Lee el mensaje de error de más arriba. Si no lo entiendes,"
    echo "  guarda lo que sale en esta ventana y consúltalo."
    echo "============================================================"
    pausa
    exit 1
}

echo
echo "============================================================"
echo "  Instalación de EEG-Platform"
echo "============================================================"
echo

# --- 1. La librería EEG-Library debe estar al lado -----------------------------------
if [ ! -f "../EEG-Library/pyproject.toml" ]; then
    echo "[ERROR] No encuentro la carpeta EEG-Library al lado de EEG-Platform."
    echo
    echo "  Las dos carpetas tienen que estar juntas, por ejemplo:"
    echo "      TFG/EEG-Library"
    echo "      TFG/EEG-Platform"
    fallo
fi

# --- 2. Python 3.10 ------------------------------------------------------------------
es_310() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 10) else 1)' >/dev/null 2>&1
}
PY=""
for candidato in python3.10 \
                 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 \
                 /opt/homebrew/bin/python3.10 /usr/local/bin/python3.10 \
                 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 && es_310 "$candidato"; then
        PY="$candidato"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[ERROR] No encuentro Python 3.10, que es la versión que necesita la plataforma."
    echo "        Puede convivir con otras versiones de Python que ya tengas."
    echo
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "  1. Descarga el instalador de Python 3.10.11 para macOS (64-bit universal2) de"
        echo "     https://www.python.org/downloads/release/python-31011/"
        echo "  2. Instálalo y vuelve a abrir instalar.command."
    else
        echo "  Instálalo con el gestor de paquetes de tu distribución y vuelve a ejecutar"
        echo "  bash instalar.sh. Por ejemplo:"
        echo "    Ubuntu 22.04:          sudo apt install python3.10 python3.10-venv"
        echo "    Ubuntu 24.04 o más:    sudo add-apt-repository ppa:deadsnakes/ppa"
        echo "                           sudo apt install python3.10 python3.10-venv"
        echo "    Fedora:                sudo dnf install python3.10"
    fi
    fallo
fi
echo "[1/5] Python 3.10 encontrado ($PY)."

# --- 3. Entorno virtual --------------------------------------------------------------
if [ -x ".venv/bin/python" ]; then
    echo "[2/5] El entorno de Python ya existe."
else
    # En Debian y Ubuntu el módulo que crea entornos va en un paquete aparte.
    if ! "$PY" -c "import ensurepip, venv" >/dev/null 2>&1; then
        echo "[ERROR] A este Python 3.10 le falta el módulo para crear entornos (venv)."
        echo
        echo "  En Ubuntu o Debian instálalo con:  sudo apt install python3.10-venv"
        echo "  y vuelve a ejecutar bash instalar.sh."
        fallo
    fi
    echo "[2/5] Creando el entorno de Python..."
    "$PY" -m venv .venv || fallo
fi

# --- 4. Dependencias -----------------------------------------------------------------
echo "[3/5] Instalando las dependencias (la primera vez tarda unos minutos)..."
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt || fallo

# --- 5. Configuración y base de datos ------------------------------------------------
if [ -f ".env" ]; then
    echo "[4/5] El archivo de configuración .env ya existe; no se toca."
else
    cp ".env.example" ".env" || fallo
    echo "[4/5] Creado el archivo de configuración .env."
fi
echo "[5/5] Preparando la base de datos..."
.venv/bin/python manage.py migrate --noinput >/dev/null || fallo

echo
echo "Comprobando la instalación..."
if [ ! -f "static/models/cabeza.bin" ] || [ ! -f "static/models/cerebro.bin" ]; then
    echo
    echo "[ERROR] Faltan los archivos de la cabeza y el cerebro 3D (carpeta static/models)."
    echo "        Vuelve a descargar o clonar EEG-Platform completa: no se han copiado todos"
    echo "        los archivos."
    fallo
fi
.venv/bin/python manage.py check || fallo
.venv/bin/python manage.py comprobar_modelos || fallo

echo
echo "============================================================"
echo "  Instalación terminada. Para usar la plataforma, abre"
echo "  iniciar.command (macOS) o ejecuta bash iniciar.sh (Linux)."
echo
echo "  Si ya tenías la plataforma abierta, ciérrala (cierra su"
echo "  ventana de terminal) y ábrela otra vez para usar la versión nueva."
echo "============================================================"
pausa
exit 0
