# eeg-platform — contexto para Claude Code

## Qué es
Aplicación web Django, de uso **local**, para que investigadores de Ciencias del Deporte (sin conocimientos de programación) procesen grabaciones EEG del casco Emotiv EPOC X (EDF, 14 canales, 256 Hz) con la librería EEG-Library.
Forma parte del TFG de Miguel Ángel (Grado en Ingeniería Informática, Ingeniería del Software, UEx) y se describe en la memoria y en la defensa.

El plan de trabajo está en `PLAN.md`. Las decisiones tomadas se registran en `docs/DECISIONES.md`.

## Qué hace
1. Subir uno o muchos EDF a la vez, con parámetros de procesado (referencia, paso banda, notch).
2. Lista de grabaciones con su estado (subida, en cola, procesando, procesada, error).
3. Por grabación: calidad de la señal (mapa de electrodos y electrodos descartados con su motivo).
4. Por grabación: análisis espectral (potencia delta/theta/alfa/beta, por electrodo y por zona, y un mapa de la cabeza por banda).
5. Resultados de modelos de IA **enchufables**. Hoy son c1 (ojos abiertos/cerrados), c2 (reposo/tarea) y c3 (cuál de las 5 tareas); mañana, los que añadan otros investigadores.
6. Descargar resultados en CSV (una grabación o el lote completo).

## Qué NO es
- **No detecta ni mide fatiga.** Ningún texto, nombre de variable ni gráfica debe sugerirlo. Los resultados del TFG demuestran que el EEG no predice el VAS.
- No reimplementa procesamiento de señal: todo cálculo sale de EEG-Library. La web llama, guarda y muestra.

## Principios
- Lo más simple que funcione. Ante la duda, menos código y menos dependencias.
- Fuera de alcance salvo petición expresa: login y usuarios, Docker, PostgreSQL, Celery o Redis, API REST, React u otra SPA, despliegue en servidor y otros cascos (BitBrain).
- La condición de la grabación (OA, OC, STROOP…) es un **metadato opcional**. En este estudio va en el nombre del archivo; en otros estudios puede no existir y la plataforma debe funcionar igual.
- Datos de participantes menores de edad: los EDF y los resultados viven en una carpeta configurable **fuera del repo**. Nunca van a git ni a servicios externos. No se usan CDN: el JS y el CSS se sirven desde `static/`, así la web funciona sin internet.
- Honestidad en la interfaz: cada modelo muestra su resultado en el test independiente de 28 personas, con su intervalo y el nivel de azar, y sus limitaciones. Ese resultado sale de `resultados.json` del análisis confirmatorio, no de las cifras de validación cruzada de `MODELADO.md`.
- Los modelos solo predicen si la grabación se procesó con los parámetros con que se entrenaron. Si no, la interfaz lo indica.
- Interfaz en español. Se usa en Windows: rutas con `pathlib`.

## Stack
- Python 3.10 (el de EEG-Library), Django 5, SQLite y plantillas Django. scikit-learn 1.7.2, fijado por EEG-Library.
- JS mínimo sin framework, Chart.js copiado en `static/`.
- pytest + pytest-django.
- EEG-Library instalada en modo editable (`pip install -e ../EEG-Library`).

## Forma de trabajar
- Una fase de `PLAN.md` cada vez. Antes de escribir código, propón un plan breve y espera confirmación.
- Una fase está terminada cuando sus criterios de aceptación se cumplen, los tests pasan y la app arranca.
- Al cerrar una fase: marca su estado en `PLAN.md` y añade a `docs/DECISIONES.md` las decisiones relevantes, con su porqué en una o dos líneas.
- No hagas commits: los hace Miguel Ángel. Al cerrar una fase, propón un mensaje de commit corto.

## Dominio
- Canales Emotiv: AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4.
- Zonas y bandas: las de EEG-Library. Las regiones son frontal, frontocentral, temporal y posterior; las bandas, delta, theta, alfa y beta.
- Condiciones del estudio original: OA, OC, STROOP, PASAT, PVTB, MSIT y PVSAT.
- El orden del pipeline está fijado en `ESTADO.md` (EEG-Library). La web solo expone parámetros que la librería ya admite, con sus valores por defecto.

## Comandos
Desde la carpeta `EEG-Platform`, en PowerShell. Python 3.10 y EEG-Library clonada al lado (`..\EEG-Library`).

- Instalar (una vez):
  ```
  & "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  copy .env.example .env      # y ajustar EEG_PLATFORM_DATOS
  .venv\Scripts\python.exe manage.py migrate
  ```
- Arrancar: `.venv\Scripts\python.exe manage.py runserver` y abrir http://127.0.0.1:8000/
- Tests: `.venv\Scripts\python.exe -m pytest`
- Procesador (en otra terminal, abierto mientras se usa la web): `.venv\Scripts\python.exe manage.py procesar`. Procesa la cola con N procesos. N se calcula en cada equipo (mitad de los hilos, máximo 4 y un proceso por GB libre; `grabaciones/recursos.py`) y se puede fijar con `--procesos N` o `EEG_PLATFORM_PROCESOS`, porque la plataforma se usará en portátiles distintos. `--una-vez` termina al vaciar la cola. Se para con Ctrl+C y, al relanzarlo, continúa donde iba. Si hay cola y no está en marcha, la lista lo avisa. El `iniciar.bat` de la Fase 8 lo lanzará junto a la web.

Los datos (base SQLite, EDF y resultados) van a `EEG_PLATFORM_DATOS`; por defecto `..\EEG-Platform-datos`. Django no arranca si apunta dentro del repo.