# Prueba en Linux y macOS (Fase 12)

Qué se ha comprobado de la plataforma fuera de Windows, y la lista que se sigue en cada sistema.
Como en [`PRUEBA_LOTE_REAL.md`](PRUEBA_LOTE_REAL.md), no incluye nombres de archivo ni de participantes.

## Estado

| Sistema | Estado |
|---|---|
| Windows 11 (x86_64) | **Probado**: es el sistema en que se desarrolló y se hizo la prueba con un lote real |
| Linux: Ubuntu en WSL (x86_64) | Pendiente |
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

Pendiente.
