#!/bin/bash
# macOS: con doble clic se abre una ventana de Terminal que arranca EEG-Platform (iniciar.sh).
# Deja la ventana abierta mientras trabajes; para terminar, ciérrala.
cd "$(dirname "$0")" || exit 1
EEG_PLATFORM_PAUSA=1 exec bash ./iniciar.sh
