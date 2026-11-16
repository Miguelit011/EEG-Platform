#!/usr/bin/env bash
# Arranca EEG-Platform en Linux o macOS: la web, el procesador en segundo plano y el navegador.
# Hace lo mismo que iniciar.bat en Windows, pero en una sola ventana de terminal: mientras
# esté abierta, la plataforma funciona; al cerrarla (o con Ctrl+C) se para todo.
#   Linux:  bash iniciar.sh            macOS: doble clic en iniciar.command
# Compatible con el bash 3.2 que trae macOS.
set -u
cd "$(dirname "$0")" || exit 1

PY=".venv/bin/python"
URL="http://127.0.0.1:8000/"

pausa() {
    if [ "${EEG_PLATFORM_PAUSA:-0}" = "1" ]; then
        echo
        read -r -p "Pulsa Intro para cerrar esta ventana. " _
    fi
}

error() {
    echo
    echo "[ERROR] $1"
    echo
    pausa
    exit 1
}

abrir_navegador() {
    # El módulo webbrowser de Python usa `open` en macOS y `xdg-open` (o el que haya) en Linux.
    "$PY" -m webbrowser -t "$URL" >/dev/null 2>&1 || true
}

puerto_ocupado() {
    "$PY" -c "import socket, sys
s = socket.socket()
s.settimeout(1)
sys.exit(0 if s.connect_ex(('127.0.0.1', 8000)) == 0 else 1)"
}

if [ ! -x "$PY" ]; then
    error "La plataforma todavía no está instalada. Ejecuta primero instalar.sh (en macOS, instalar.command)."
fi

# --- La base de datos al día (rápido si no hay nada que hacer) ---------------------------
"$PY" manage.py migrate --noinput >/dev/null \
    || error "No se ha podido preparar la base de datos. Ejecuta instalar.sh de nuevo."

# --- ¿Ya está en marcha? -----------------------------------------------------------------
if puerto_ocupado; then
    echo
    echo "Ya hay algo funcionando en el puerto 8000. Si es una copia de EEG-Platform arrancada"
    echo "antes de actualizar, sigue mostrando la versión anterior."
    echo
    respuesta=""
    read -r -p "¿Reiniciarla con la versión actual? [S = sí, N = solo abrir el navegador] " respuesta
    case "$respuesta" in
        [Nn]*)
            abrir_navegador
            echo "Abierto $URL en el navegador."
            exit 0
            ;;
    esac
    echo
    echo "Cerrando la copia anterior..."
    pkill -TERM -f 'manage\.py (procesar|runserver 127\.0\.0\.1:8000)' || true
    sleep 3
fi

echo
echo "Arrancando EEG-Platform..."
echo "Deja esta ventana abierta mientras trabajes; para terminar, ciérrala o pulsa Ctrl+C."
echo

"$PY" manage.py procesar &
PID_PROCESADOR=$!
"$PY" manage.py runserver 127.0.0.1:8000 --noreload &
PID_WEB=$!

parar() {
    trap - EXIT INT TERM HUP
    echo
    echo "Parando EEG-Platform..."
    # El procesador devuelve a la cola lo que estaba a medias (trata esta señal como Ctrl+C).
    kill -TERM "$PID_PROCESADOR" "$PID_WEB" 2>/dev/null
    wait 2>/dev/null
    echo "EEG-Platform parada."
    exit 0
}
trap parar EXIT INT TERM HUP

# --- Esperar a que la web responda (hasta 60 s) y abrir el navegador -------------------------
if ! "$PY" -c "import sys, time, urllib.request
for _ in range(60):
    try:
        urllib.request.urlopen('$URL', timeout=2)
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)"; then
    echo
    echo "[ERROR] La web no ha arrancado. Mira los mensajes de más arriba."
    pausa
    exit 1
fi
abrir_navegador
echo
echo "Listo: la plataforma está en $URL"
echo

wait
