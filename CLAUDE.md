# EEG-Platform — instrucciones del proyecto

## Qué es
Aplicación web Django, de uso **local**, para que investigadores de Ciencias del Deporte (sin conocimientos de programación) procesen grabaciones EEG del casco Emotiv EPOC X (EDF, 14 canales, 256 Hz) con la librería EEG-Library.
Forma parte de un TFG del Grado en Ingeniería Informática (UEx).

El plan de trabajo está en `PLAN.md`. Las decisiones tomadas se registran en `docs/DECISIONES.md`.

## Qué hace
1. Subir uno o muchos EDF a la vez, con parámetros de procesado (referencia, paso banda, notch).
2. Lista de grabaciones con su estado (subida, en cola, procesando, procesada, error).
3. Por grabación: calidad de la señal (mapa de electrodos y electrodos descartados con su motivo).
4. Por grabación: análisis espectral (potencia delta/theta/alfa/beta, por electrodo y por zona) con un visor de cabeza y cerebro reales en 3D y cuatro mapas 2D por banda. El color entre sensores es una interpolación orientativa y no localiza fuentes.
5. Resultados de modelos de IA **enchufables**. Hoy son c1 (ojos abiertos/cerrados), c2 (reposo/tarea) y c3 (cuál de las 5 tareas); mañana, los que añadan otros investigadores.
6. Pestaña **Tiempo en tarea** (Fases 10 y 11), solo para PASAT y PVTB: cómo cambia el EEG a lo largo de la tarea según la logística de la línea `tiempo_en_tarea` de EEG-Library y de la red neuronal EEGNet (ONNX, calculada por la librería al procesar): un apartado de resultado por modelo, uno al lado del otro (veredicto de tercios con su cifra en test), y cuatro mapas 2D animados del cerebro (uno por banda) con una cinta de tiempo de dos pistas.
7. Descargar resultados en CSV (una grabación o el lote completo).

## Qué NO es
- **No detecta ni mide fatiga.** Ningún texto, nombre de variable ni gráfica debe sugerirlo. Con estos datos, características y modelos no se ha encontrado una relación predictiva robusta entre el EEG y la VAS.
  - La palabra «fatiga» solo aparece en los avisos que dicen que **no** se mide: el del bloque de modelos y el de la pestaña **Tiempo en tarea** («no el nivel de fatiga de la persona»). La pestaña, su enlace y las columnas `tiempo_en_tarea_*` del CSV no la llevan. Los tests lo vigilan en todas las páginas y en el CSV.
- No reimplementa procesamiento de señal: todo cálculo sale de EEG-Library. La web llama, guarda y muestra.

## Principios
- Lo más simple que funcione. Ante la duda, menos código y menos dependencias.
- Fuera de alcance: login y usuarios, Docker, PostgreSQL, Celery o Redis, API REST, React u otra SPA, despliegue en servidor y otros cascos (BitBrain).
- La condición de la grabación (OA, OC, STROOP…) es un **metadato opcional**. En este estudio va en el nombre del archivo; en otros estudios puede no existir y la plataforma debe funcionar igual.
- Datos de participantes menores de edad: los EDF y los resultados viven en una carpeta configurable **fuera del repo**. Nunca van a git ni a servicios externos. No se usan CDN: el JS y el CSS se sirven desde `static/`, así la web funciona sin internet.
- Honestidad en la interfaz: cada modelo muestra su resultado en el test independiente de 28 personas, con su intervalo y el nivel de azar, y sus limitaciones. Ese resultado sale de `resultados.json` del análisis confirmatorio, no de las cifras de validación cruzada de `MODELADO.md`.
- Los modelos solo predicen si la grabación se procesó con los parámetros con que se entrenaron. Si no, la interfaz lo indica.
- Interfaz en español. Se usa en Windows, Linux y macOS (Fase 12): rutas con `pathlib`, nada propio de un sistema sin alternativa para los otros, y los lanzadores en dos versiones (`.bat` para Windows; `.sh` y `.command` para Linux y macOS).

## Stack
- Python 3.10 (el de EEG-Library), Django 5, SQLite y plantillas Django. scikit-learn 1.7.2, fijado por EEG-Library.
- JS mínimo sin framework. Chart.js y Three.js (visor 3D) copiados en `static/vendor/`, fuentes IBM Plex en `static/fonts/` y mallas de cabeza y cerebro (plantilla fsaverage) en `static/models/`, cada uno con su licencia. Sin CDN ni npm.
- pytest + pytest-django.
- EEG-Library instalada en modo editable (`pip install -e ../EEG-Library`).

## Forma de trabajar
- Se trabaja una fase de `PLAN.md` cada vez, con un plan breve aprobado antes de escribir código.
- Una fase está terminada cuando sus criterios de aceptación se cumplen, los tests pasan y la app arranca.
- Al cerrar una fase: marca su estado en `PLAN.md` y añade a `docs/DECISIONES.md` las decisiones relevantes, con su porqué en una o dos líneas.
- Los commits los hace el autor después de revisar los cambios.

## Dominio
- Canales Emotiv: AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4.
- Zonas y bandas: las de EEG-Library. Las regiones son frontal, frontocentral, temporal y posterior; las bandas, delta, theta, alfa y beta.
- Condiciones del estudio original: OA, OC, STROOP, PASAT, PVTB, MSIT y PVSAT.
- El orden del pipeline está fijado en `ESTADO.md` (EEG-Library). La web solo expone parámetros que la librería ya admite, con sus valores por defecto.

## Comandos
Desde la carpeta `EEG-Platform`, en PowerShell. Python 3.10 y EEG-Library clonada al lado (`..\EEG-Library`).

- Instalar (una vez): doble clic en `instalar.bat` (busca Python 3.10, crea `.venv`, instala `requirements.txt`, crea `.env` y migra). A mano:
  ```
  & "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  copy .env.example .env      # EEG_PLATFORM_DATOS es opcional
  .venv\Scripts\python.exe manage.py migrate
  ```
- Usar: doble clic en `iniciar.bat` (abre la web y el procesador en dos ventanas y el navegador). Solo la web: `.venv\Scripts\python.exe manage.py runserver` y abrir http://127.0.0.1:8000/
- Capturas de la guía y la memoria (datos anónimos): `.venv\Scripts\python.exe docs\generar_capturas.py`
- Los `.bat` llevan saltos de línea CRLF y UTF-8 sin BOM (`.gitattributes` lo fija).
- Linux y macOS: `bash instalar.sh` y `bash iniciar.sh` (en macOS, doble clic en `instalar.command` e `iniciar.command`), y los mismos comandos con `.venv/bin/python`. `iniciar.sh` ejecuta la web y el procesador en una sola terminal y los para al cerrarla. Los `.sh` y `.command` llevan LF y deben ser ejecutables en git (`git add --chmod=+x`); deben funcionar con el bash 3.2 de macOS.
- ¿Mismo resultado en otro sistema?: `docs/comparar_sistemas.py generar <json>` en cada uno y `comparar <a> <b>` (EDF sintético por defecto). Lista de comprobación: `docs/PRUEBA_LINUX_MACOS.md`.
- Tests: `.venv\Scripts\python.exe -m pytest`
- Modelos: `.venv\Scripts\python.exe manage.py comprobar_modelos` valida los de `settings.MODELOS` (ficha, SHA-256, columnas, predicción). Cómo añadir uno: `docs/AÑADIR_UN_MODELO.md`. Los externos van en `EEG-Platform-datos\modelos\`.
- Documentación de las columnas del CSV: `.venv\Scripts\python.exe manage.py documentar_csv` regenera `docs/COLUMNAS_CSV.md` (un test falla si está desactualizado).
- Procesador (en otra terminal, abierto mientras se usa la web): `.venv\Scripts\python.exe manage.py procesar`. Procesa la cola con N procesos. N se calcula en cada equipo (mitad de los hilos, máximo 4 y un proceso por GB libre; `grabaciones/recursos.py`) y se puede fijar con `--procesos N` o `EEG_PLATFORM_PROCESOS`, porque la plataforma se usará en portátiles distintos. `--una-vez` termina al vaciar la cola. Se para con Ctrl+C y, al relanzarlo, continúa donde iba. Si hay cola y no está en marcha, la lista lo avisa nombrando el lanzador del sistema (`recursos.lanzador`). `iniciar.bat` (o `iniciar.sh`) lo lanza junto a la web. Los hijos se crean con *spawn* en todos los sistemas, y SIGTERM o SIGHUP lo paran como Ctrl+C.

Los datos (base SQLite, EDF y resultados) van a `EEG_PLATFORM_DATOS`; por defecto `..\EEG-Platform-datos`. Django no arranca si apunta dentro del repo.