# Prueba en Linux y macOS (Fase 12)

Qué se ha comprobado de la plataforma fuera de Windows, y la lista que se sigue en cada sistema.
Como en [`PRUEBA_LOTE_REAL.md`](PRUEBA_LOTE_REAL.md), no incluye nombres de archivo ni de participantes.

## Estado

| Sistema | Estado |
|---|---|
| Windows 11 (x86_64) | **Probado**: es el sistema en que se desarrolló y se hizo la prueba con un lote real |
| Linux: Ubuntu 26.04 en WSL 2 (x86_64) | **Probado** (2026-11-16): los 9 puntos de la lista, con EDF reales |
| macOS | Pendiente |

## Lo que se sabe sin probar

- **Dependencias.** Todos los paquetes de `requirements.txt`, en sus versiones fijadas, tienen
  paquete precompilado para Python 3.10 en Linux (x86_64 y ARM, glibc ≥ 2.28) y en macOS (Intel y
  Apple Silicon, macOS ≥ 13). Comprobado el 2026-11-16 con
  `pip download --only-binary=:all: --python-version 3.10 --platform …`. El límite de macOS 13 lo
  pone `onnxruntime`; el de glibc 2.28, `onnxruntime` y `pyarrow`.
- **Cálculo numérico.** numpy y scipy usan OpenBLAS en Windows y Linux. En macOS con Apple Silicon
  usan Accelerate (de Apple), así que puede haber diferencias en los últimos decimales. Lo mide
  `docs/comparar_sistemas.py`.

## Lista de comprobación

Desde una copia limpia de `EEG-Library` y `EEG-Platform` (sin `.venv`, `.env` ni
`EEG-Platform-datos`), una al lado de la otra.

1. **Python 3.10.** Sin instalar, `instalar.sh` (o `instalar.command`) se para y explica cómo
   conseguirlo. Con Python 3.10 instalado, sigue.
2. **Instalar.** `bash instalar.sh` en Linux, o doble clic en `instalar.command` en macOS: termina
   con «Instalación terminada» y `comprobar_modelos` da por buenos los modelos.
3. **Tests.** `.venv/bin/python -m pytest`: pasan todos.
4. **Arrancar.** `bash iniciar.sh` en Linux, o doble clic en `iniciar.command` en macOS: se abre el
   navegador en <http://127.0.0.1:8000/> (en WSL, abrirlo a mano desde Windows).
5. **Usar.** Subir varios EDF en un lote, ver cómo pasan a «procesada» (el aviso de la lista dice
   cuántos procesos usa), abrir Calidad, Análisis (con el cerebro 3D), Modelos y Tiempo en tarea de
   una grabación, y descargar el CSV del lote.
6. **Volver a arrancar.** Con la plataforma abierta, lanzar otra vez `iniciar.sh`: pregunta si
   reiniciar. Con `S`, cierra la anterior y arranca la nueva.
7. **Parar a medias.** Con grabaciones procesándose, cerrar la ventana de la terminal (o Ctrl+C).
   No queda ningún proceso de la plataforma (`ps aux | grep manage.py`) ni el puerto 8000 ocupado.
   Al arrancar de nuevo, lo que estaba a medias se procesa.
8. **Aviso sin procesador.** Arrancar solo la web (`.venv/bin/python manage.py runserver`) con
   grabaciones en cola: el aviso naranja nombra `iniciar.sh` (Linux) o `iniciar.command` (macOS).
9. **Mismo resultado que en Windows.**
   `.venv/bin/python docs/comparar_sistemas.py generar resultado_<sistema>.json`, y comparar con el
   de Windows con `… comparar resultado_windows.json resultado_<sistema>.json`.

## Resultados

### Linux: Ubuntu 26.04 en WSL 2 (2026-11-16)

**Cómo se hizo.** Equipo: el mismo Ryzen 5 5600G de [`PRUEBA_LOTE_REAL.md`](PRUEBA_LOTE_REAL.md)
(12 hilos; WSL con 7 GB libres), Ubuntu 26.04.1 LTS (glibc 2.43), Python 3.10.22 del PPA
deadsnakes. Se partió de un `git clone` de los dos repositorios (commit `29b973d` de EEG-Platform),
sin `.venv`, `.env` ni datos. Los pasos 4–8 se automatizaron: subidas por HTTP como el navegador
y, para cerrar la ventana y pulsar Ctrl+C, una terminal virtual (`script`) a la que se le cuelga la
línea o se le manda la señal de interrupción, igual que hace un emulador de terminal.

**EDF reales**, todos de sujetos de entrenamiento y validación (`splits.csv`; ninguno de los 28 del
test), elegidos con semilla fija y leídos de `EEG-Data` sin modificarlos: 14 EDF (dos sujetos ×
7 condiciones) y dos lotes de 40 (seis sujetos más). Al terminar se borraron la carpeta de datos de
la prueba y todos los resultados intermedios.

| Punto | Resultado |
|---|---|
| 1. Sin Python 3.10 | `instalar.sh` para, explica cómo instalarlo (en Ubuntu, el PPA deadsnakes) y no crea nada |
| 2. Instalar | 42 s, con las versiones fijadas exactas; `comprobar_modelos`: los 3 modelos, bien |
| 3. Tests | **313 pasan** y 1 se salta porque necesita `EEG-Data` al lado; con `EEG_DATA` apuntando a los datos, también pasa. Incluye los que solo corren fuera de Windows (señales de parada y sintaxis de los scripts) |
| 4. Arrancar | `iniciar.sh` arranca la web y el procesador; el procesador elige **4 procesos** por sí solo (12 hilos, memoria leída de `/proc/meminfo`) |
| 5. Usar | 14 EDF en 0,7 s de subida y 25 s de procesado; 108 grabaciones en total sin ningún error; **478 páginas** (Calidad, Análisis, Modelos, Tiempo en tarea y CSV de cada grabación, portada, lista, resumen y archivos estáticos) sin un fallo; CSV de cada lote con todas sus filas y 188 columnas |
| 6. Volver a arrancar | Pregunta si reiniciar; con `S` cierra la copia anterior y arranca la nueva (otro procesador); ante otra respuesta vuelve a preguntar, y sin teclado no cierra nada (`N`) |
| 7. Parar a medias | Con 4 análisis en curso, tanto **al cerrar la ventana** como **con Ctrl+C**: los 4 vuelven a «en cola», se borra el latido, no queda ningún proceso (ni hijos de análisis) y el puerto 8000 queda libre. Al arrancar otra vez, termina el lote sin repetir lo hecho |
| 8. Aviso sin procesador | Nombra `iniciar.sh` |
| 9. Mismo resultado que en Windows | Ver abajo |

**Mismo resultado que en Windows** (`docs/comparar_sistemas.py`), con el EDF sintético y 7 reales
(uno por condición):

| | |
|---|---|
| Valores comparados | 29 587 (8 EDF) |
| Diferencia relativa máxima | **1,1·10⁻¹³** (el último decimal de un número en coma flotante doble) |
| Valores no numéricos distintos (calidad, electrodos descartados, épocas…) | **Ninguno** |
| Predicciones de c1, c2 y c3 | **Las mismas en los 8**; probabilidades con una diferencia máxima de 1,6·10⁻¹⁴ |
| Tiempo en tarea (logística y EEGNet, PASAT y PVTB) | Diferencia máxima de 3,3·10⁻¹³ |

Las dos usan OpenBLAS; la única diferencia en los metadatos es la versión de Python (3.10.11 en
Windows, 3.10.22 en Ubuntu).

**Lo que encontró la prueba:**
- Con la pregunta de reiniciar, una respuesta vacía (o la entrada cerrada) reiniciaba. Corregido:
  como `choice /c SN` de `iniciar.bat`, solo vale S o N, y sin teclado se toma N.
- En WSL, `onnxruntime` escribe un aviso amarillo («GPU device discovery failed») al cargar EEGNet,
  porque WSL no expone la tarjeta gráfica. Es inofensivo: el cálculo va en la CPU, como siempre.
- En WSL no se abre el navegador de Windows solo: hay que abrir <http://127.0.0.1:8000/> a mano
  (WSL comparte el puerto con Windows). En un Linux con escritorio lo abre `iniciar.sh`.

### macOS

Pendiente.
