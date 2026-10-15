# eeg-platform — contexto para Claude Code

## Qué es
Aplicación web Django, de uso **local**, para que investigadores de Ciencias del Deporte (sin conocimientos de programación) procesen grabaciones EEG del casco Emotiv EPOC X (EDF, 14 canales, 256 Hz) con la librería `eeg-library`.
Forma parte del TFG de Miguel Ángel (Grado en Ingeniería Informática, Ingeniería del Software, UEx) y se describe en la memoria y en la defensa.

El plan de trabajo está en `PLAN.md`. Las decisiones tomadas se registran en `docs/DECISIONES.md`.

## Qué hace
1. Subir uno o muchos EDF a la vez, con parámetros de procesado (referencia, paso banda, notch).
2. Lista de grabaciones con su estado (subida, en cola, procesando, procesada, error).
3. Por grabación: calidad de la señal (mapa de electrodos y electrodos descartados con su motivo).
4. Por grabación: análisis espectral (potencia delta/theta/alfa/beta, por electrodo y por zona, y un mapa de la cabeza por banda).
5. Resultados de modelos de IA **enchufables**: hoy, los de las Fases 17–19; mañana, los que añadan otros investigadores.
6. Descargar resultados en CSV (una grabación o el lote completo).

## Qué NO es
- **No detecta ni mide fatiga.** Ningún texto, nombre de variable ni gráfica debe sugerirlo. Los resultados del TFG demuestran que el EEG no predice el VAS.
- No reimplementa procesamiento de señal: todo cálculo sale de `eeg-library`. La web llama, guarda y muestra.

## Principios
- Lo más simple que funcione. Ante la duda, menos código y menos dependencias.
- Fuera de alcance salvo petición expresa: login y usuarios, Docker, PostgreSQL, Celery o Redis, API REST, React u otra SPA, despliegue en servidor y otros cascos (BitBrain).
- La condición de la grabación (OA, OC, STROOP…) es un **metadato opcional**. En este estudio va en el nombre del archivo; en otros estudios puede no existir y la plataforma debe funcionar igual.
- Datos de participantes menores de edad: los EDF y los resultados viven en una carpeta configurable **fuera del repo**. Nunca van a git ni a servicios externos. No se usan CDN: el JS y el CSS se sirven desde `static/`, así la web funciona sin internet.
- Honestidad en la interfaz: cada modelo muestra su exactitud real (la de `MODELADO.md` en eeg-library) y sus limitaciones.
- Interfaz en español. Se usa en Windows: rutas con `pathlib`.

## Stack
- Python (la misma versión que `eeg-library`), Django 5, SQLite y plantillas Django.
- JS mínimo sin framework, Chart.js copiado en `static/`.
- pytest + pytest-django.
- `eeg-library` instalada en modo editable (`pip install -e ../eeg-library`).

## Forma de trabajar
- Una fase de `PLAN.md` cada vez. Antes de escribir código, propón un plan breve y espera confirmación.
- Una fase está terminada cuando sus criterios de aceptación se cumplen, los tests pasan y la app arranca.
- Al cerrar una fase: marca su estado en `PLAN.md` y añade a `docs/DECISIONES.md` las decisiones relevantes, con su porqué en una o dos líneas.
- No hagas commits: los hace Miguel Ángel. Al cerrar una fase, propón un mensaje de commit corto.

## Dominio
- Canales Emotiv: AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4.
- Zonas y bandas: las que defina `eeg-library`. Si no las define, se usan estas zonas: frontal (AF3, AF4, F3, F4, F7, F8, FC5, FC6), temporal (T7, T8), parietal (P7, P8) y occipital (O1, O2).
- Condiciones del estudio original: OA, OC, STROOP, PASAT, PVTB, MSIT y PVSAT.
- El orden del pipeline está fijado en `ESTADO.md` (eeg-library). La web solo expone parámetros que la librería ya admite, con sus valores por defecto.

## Comandos
<!-- Se rellenan en la Fase 1: instalar, arrancar, tests, worker -->
