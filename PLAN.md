# Plan de desarrollo — eeg-platform

Cada fase deja algo que funciona y se puede enseñar. No se empieza una fase sin cerrar la anterior.

| Fase | Qué | Repo | Estado |
|---|---|---|---|
| 0 | Contrato con la librería y modelos exportados | EEG-Library | [ ] |
| 1 | Esqueleto Django | eeg-platform | [ ] |
| 2 | Subida y lista de grabaciones | eeg-platform | [ ] |
| 3 | Procesado en segundo plano | eeg-platform | [ ] |
| 4 | Pantalla de calidad | eeg-platform | [ ] |
| 5 | Pantalla de análisis y mapa de la cabeza | eeg-platform | [ ] |
| 6 | Exportación CSV | eeg-platform | [ ] |
| 7 | Modelos enchufables (F17–19) | eeg-platform | [ ] |
| 8 | Cierre: arranque fácil, guía y material para la memoria | eeg-platform | [ ] |

Versión mínima defendible: Fases 0–6. La Fase 7 añade la parte de IA y la extensibilidad.

---

## Pantallas

**1. Grabaciones.** Zona para soltar uno o muchos EDF. Debajo, los parámetros de procesado (referencia, paso banda y notch a 50 Hz), comunes a todo el lote. Después, la lista de archivos con: nombre, condición (opcional y editable), duración, resumen de calidad, estado y un enlace al detalle. Incluye el progreso del lote y un botón para descargar el CSV del lote.

**2. Calidad (por grabación).** Resumen de electrodos buenos y descartados. Mapa de la cabeza con los 14 electrodos coloreados por estado, más una tabla con cada electrodo, su zona, su estado y el motivo del descarte. Muestra también lo que el pipeline aplicó: CAR sí/no y componentes de ICA eliminadas.

**3. Análisis (por grabación).** Potencia relativa por banda en toda la cabeza, tabla zona × banda y mapa de la cabeza coloreado por potencia, con selector de banda y el valor de cada electrodo al pasar el ratón. Debajo, el bloque de modelos y la descarga del CSV de esa grabación.

---

## Fase 0 — Contrato con la librería *(en EEG-Library)*
**Objetivo:** que la web solo tenga que llamar a una función y guardar lo que devuelve.

Entregables:
- Una función pública (por ejemplo `analizar_grabacion(ruta_edf, parametros)`) que devuelva un diccionario serializable a JSON con:
  - Metadatos: duración, frecuencia de muestreo, canales y versión de la librería.
  - Parámetros aplicados de verdad: referencia, filtros, si se aplicó CAR y componentes de ICA eliminadas.
  - Calidad por canal: estado y motivo, con los criterios que ya usa el pipeline. Si la librería no distingue «dudoso», se usan dos estados; no se inventan umbrales.
  - Potencia absoluta y relativa por canal y banda, y sus agregados por zona.
  - Lo que necesiten los modelos para predecir (las mismas características con que se entrenaron).
- Los modelos de las Fases 17, 18 y 19 guardados en archivo, cada uno con una ficha: qué predice, clases, a qué condiciones aplica, exactitud en el test de 28 personas (de `MODELADO.md`), avisos y versión de la librería. Si ya existen, solo se documentan.
- Un JSON de ejemplo generado con un EDF real, que se copiará como fixture a eeg-platform.

Aceptación:
- Tests nuevos en EEG-Library.
- Los tests existentes siguen pasando.
- Los resultados del pipeline no cambian.

## Fase 1 — Esqueleto
**Objetivo:** proyecto Django vacío que arranca.

Incluye:
- Un proyecto y una app.
- SQLite.
- Carpeta de datos configurable fuera del repo, con `.gitignore` y `.env.example`.
- Plantilla base con navegación a las tres pantallas.
- pytest-django.
- `EEG-Library` instalada en editable.
- La sección «Comandos» de `CLAUDE.md` rellenada.

Aceptación:
- `runserver` muestra la pantalla Grabaciones vacía.
- Los tests pasan.
- Ningún dato queda dentro del repo.

## Fase 2 — Subida y lista de grabaciones
**Objetivo:** subir uno o muchos EDF y verlos listados. Todavía no se procesan.

Incluye:
- Modelos `Lote` (parámetros de procesado y fecha) y `Grabacion` (archivo, nombre original, condición opcional y su origen —nombre, manual o vacía—, duración, estado, mensaje de error y resultado JSON).
- Subida múltiple: selector y arrastrar y soltar.
- Validación al subir: el EDF se lee y tiene fs ≥ 256 Hz y los canales esperados. Un archivo inválido se marca con su error y no rompe el resto del lote.
- La condición se lee del nombre con un patrón configurable y se puede editar desde la lista. Si no se reconoce, queda vacía.
- Parámetros con los valores por defecto de `ESTADO.md`.

Aceptación:
- Subir 1 archivo y subir 20 de golpe funcionan.
- Un archivo corrupto en un lote solo marca ese archivo.
- Hay tests de validación y del patrón de condición.

## Fase 3 — Procesado en segundo plano
**Objetivo:** procesar lotes grandes sin bloquear la web y sin infraestructura extra.

Incluye:
- Cola en la propia base de datos.
- Un comando `manage.py` que hace de worker y procesa las grabaciones en cola de una en una, llamando a la función de la Fase 0 y guardando el JSON.
- La lista se actualiza sola cada pocos segundos (estado y progreso del lote).
- Botones para reintentar las fallidas y para reprocesar.

Aceptación:
- Un lote de 20 archivos se procesa entero.
- Si se para el worker y se vuelve a lanzar, continúa donde iba.
- Un error en un archivo no detiene el resto.
- Hay tests del procesado con un EDF pequeño.

## Fase 4 — Pantalla de calidad
**Objetivo:** que el investigador vea si la grabación es aprovechable.

Incluye la pantalla 2, construida solo a partir del JSON guardado. El mapa de electrodos se dibuja en SVG con posiciones fijas del Emotiv.

Aceptación:
- Funciona con el fixture de la Fase 0.
- Muestra correctamente grabaciones con 0, 1 o varios electrodos descartados.
- Los colores no dependen solo del tono: el estado también se distingue por forma o texto.

## Fase 5 — Pantalla de análisis y mapa de la cabeza
**Objetivo:** ver la actividad por banda y zona.

Incluye:
- La pantalla 3 sin el bloque de modelos.
- Gráfica de barras con Chart.js.
- Tabla zona × banda.
- Mapa de la cabeza interactivo: selector de banda, color según la potencia y valor al pasar el ratón. Si la librería ya genera topomapas con MNE, se pueden usar como imagen por banda en lugar del SVG; la Fase 5 decide cuál de las dos opciones es más simple.

Aceptación:
- Funciona con el fixture.
- Los electrodos descartados aparecen marcados y no se colorean.
- Hay leyenda con la escala.

## Fase 6 — Exportación CSV
**Objetivo:** que los investigadores puedan hacer sus análisis en Excel o SPSS.

Incluye:
- CSV de una grabación y CSV del lote, ambos con una fila por grabación.
- Columnas: archivo, condición, duración, electrodos descartados, potencia por electrodo × banda, potencia por zona × banda y, cuando existan, las predicciones de los modelos.
- Separador, decimal y codificación pensados para Excel en español. **Confirmar con Rosa/Ana antes de cerrar.**

Aceptación:
- El CSV se abre bien en Excel y en SPSS.
- Los nombres de columna son estables y están documentados.

## Fase 7 — Modelos enchufables
**Objetivo:** mostrar los modelos F17–19 y que añadir uno nuevo no exija tocar la web.

Incluye:
- Una interfaz pequeña de modelo: ficha (nombre, qué predice, a qué condiciones aplica, exactitud, avisos) y `predecir(resultado) -> clase + probabilidades`.
- Los modelos se registran en una lista de `settings`.
- F17 (OA/OC), F18 (reposo/tarea) y F19 (cuál de las 5 tareas).
- Si la condición del archivo se conoce: solo se ejecutan los modelos que aplican y se compara la predicción con la etiqueta, avisando si discrepan con alta confianza.
- Si la condición no se conoce: se muestran con la nota «resultado orientativo; este modelo solo es válido para …».
- Aviso fijo en la interfaz: los modelos no miden fatiga, y parte del acierto puede deberse a la duración o al orden de las tareas.
- `docs/AÑADIR_UN_MODELO.md`, escrito para los investigadores de Ciencias del Deporte.

Aceptación:
- Un modelo de prueba se añade solo con su archivo y una línea en `settings`, y aparece en la pantalla y en el CSV.
- Las exactitudes mostradas coinciden con `MODELADO.md`.

## Fase 8 — Cierre
**Objetivo:** que alguien que no programa pueda usarla, y tener material para la memoria.

Incluye:
- Un `iniciar.bat` que arranca la web y el worker y abre el navegador.
- `docs/GUIA_DE_USO.md` con capturas.
- Prueba completa con un lote real.
- Para la memoria: diagrama de arquitectura (web ↔ librería ↔ worker ↔ datos), casos de uso, número de tests y capturas de las tres pantallas.

Aceptación:
- Desde un clon limpio, siguiendo el README, la web funciona en Windows.

---

## Prompts

**Fase 0** (sesión en EEG-Library; copia antes la sección Fase 0 de este archivo al repo o pégala):
> Vamos a crear una web Django que use esta librería. Necesito lo descrito en «Fase 0 — Contrato con la librería» (te lo pego abajo). Revisa primero la API pública y `MODELADO.md`, propón un plan y espera mi confirmación antes de escribir código.

**Fases 1–8** (sesión en eeg-platform, con `CLAUDE.md` y `PLAN.md` en la raíz):
> Fase N de PLAN.md. Propón un plan y espera mi confirmación.

**Al terminar cada fase:**
> Comprueba los criterios de aceptación de la Fase N uno por uno, marca la fase en PLAN.md y actualiza docs/DECISIONES.md.
