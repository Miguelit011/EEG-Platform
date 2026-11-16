#!/bin/bash
# macOS: con doble clic se abre una ventana de Terminal que instala EEG-Platform (instalar.sh).
cd "$(dirname "$0")" || exit 1
EEG_PLATFORM_PAUSA=1 exec bash ./instalar.sh
