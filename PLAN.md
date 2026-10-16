# Plan de desarrollo — eeg-platform

Cada fase deja algo que funciona y se puede enseñar. No se empieza una fase sin cerrar la anterior.

| Fase | Qué | Repo | Estado |
|---|---|---|---|
| 0 | Contrato con la librería y modelos empaquetados | EEG-Library | [x] |
| 1 | Esqueleto Django | EEG-Platform | [x] |
| 2 | Subida y lista de grabaciones | EEG-Platform | [x] |
| 3 | Procesado en segundo plano | EEG-Platform | [x] |
| 4 | Pantalla de calidad | EEG-Platform | [x] |
| 5 | Pantalla de análisis y mapa de la cabeza | EEG-Platform | [x] |
| 6 | Exportación CSV | EEG-Platform | [x] |
| 7 | Modelos enchufables (c1, c2, c3) | EEG-Platform | [x] |
| 8 | Cierre: arranque fácil, guía y material para la memoria | EEG-Platform | [x] |

Versión mínima defendible: Fases 0–6. La Fase 7 añade la parte de IA y la extensibilidad.

---

## Pantallas

**1. Grabaciones.** Zona para soltar uno o muchos EDF. Debajo, los parámetros de procesado, comunes a todo el lote y con opciones cerradas: referencia (CAR condicional u original), paso banda (1–30 o 3–30 Hz) y notch a 50 Hz (sí/no). Por defecto, los del estudio. Después, la lista de archivos con: nombre, condición (opcional y editable), duración, resumen de calidad, estado y un enlace al detalle. Incluye el progreso del lote y un botón para descargar el CSV del lote.

**2. Calidad (por grabación).** Resumen de electrodos buenos y descartados. Mapa de la cabeza con los 14 electrodos coloreados por estado, más una tabla con cada electrodo, su zona, su estado y el motivo del descarte. Muestra también lo que el pipeline aplicó: CAR sí/no y componentes de ICA eliminadas.

**3. Análisis (por grabación).** Potencia relativa por banda en toda la cabeza, tabla zona × banda y mapa de la cabeza coloreado por potencia, con selector de banda y el valor de cada electrodo al pasar el ratón. Debajo, el bloque de modelos y la descarga del CSV de esa grabación.

---

## Modelos: lo que ya sabemos

- Se usan los modelos finales del análisis confirmatorio del 2026-10-07 (`EEG-Data\processed\test_20261007-133358\modelos\`), entrenados con train+val completos. Variante: regresión logística, la principal del pre-registro (`PREREGISTRO_TEST.md` §6).
  - **c1**: ojos abiertos / cerrados. Test: 0.855 [0.794–0.912]; azar 0.5.
  - **c2**: reposo / tarea. Test: 0.851 [0.813–0.885]; azar 0.5.
  - **c3**: cuál de las 5 tareas. Test: 0.488 [0.441–0.531]; azar 0.2.
  - Las tres cifras son exactitud balanceada sobre las 28 personas del test.
- Cada `.joblib` es un Pipeline completo (imputador, escalado y modelo) que comprueba el nombre y el orden de sus 70 columnas.
- Entrada: una fila por grabación con 70 características. Son 4 regiones × 4 bandas × (log absoluta y relativa, cada una con media y sd entre épocas), más 6 extra. No hay normalización entre grabaciones, así que se pueden aplicar a un EDF suelto.
- Se guardaron con scikit-learn 1.7.2 y Python 3.10.
- Las Fases 17–19 no dejaron modelos guardados: solo métricas de validación cruzada. No se reejecutan.

---

## Fase 0 — Contrato con la librería *(en EEG-Library)* — **hecha** (2026-10-15)
Contrato documentado en `EEG-Library/docs/CONTRATO.md`; fixture en `EEG-Library/docs/ejemplos/analisis_grabacion.json`.
**Objetivo:** que la web solo tenga que llamar a la librería y guardar lo que devuelve.

Entregables:
- Función pública `analizar_grabacion(ruta_edf, parametros)` que devuelva un diccionario serializable a JSON con:
  - Metadatos: duración, frecuencia de muestreo, canales y versión de la librería.
  - Parámetros aplicados de verdad: referencia, filtros, si se aplicó CAR y componentes de ICA eliminadas.
  - Calidad por canal: estado y motivo, con los criterios que ya usa el pipeline. Si la librería no distingue «dudoso», se usan dos estados; no se inventan umbrales.
  - Potencia absoluta y relativa por canal y banda, y sus agregados por zona.
  - `caracteristicas`: las 70 columnas, con su nombre, que usan los modelos.
- El cálculo EDF → 70 características usa **el mismo código** que construye `matriz_rf.parquet`, sin copias ni valores ficticios de VAS o condición. Si hace falta, se separa la parte que exige esos campos.
- Los modelos c1, c2 y c3 (logística) empaquetados dentro de EEG-Library. Cada uno lleva una ficha JSON con:
  - qué predice y sus clases con nombre (confirmadas en el código de entrenamiento);
  - a qué condiciones se aplica;
  - los parámetros de procesado con los que es válido;
  - las columnas que necesita;
  - su resultado en el test con IC;
  - fecha, SHA-256 de `matriz_rf.parquet`, versión de scikit-learn y avisos.
- Función `predecir(modelo, caracteristicas, parametros)` que devuelve la clase y las probabilidades, o «no disponible» si los parámetros no son los del entrenamiento.
- scikit-learn 1.7.2 y Python 3.10 fijados en `pyproject.toml`.
- Un JSON de ejemplo generado con un EDF real, que se copiará como fixture a EEG-Platform.

Aceptación:
- **Paridad:** en una muestra de grabaciones de train/val (nunca de test), las 70 características calculadas desde el EDF coinciden con su fila de `matriz_rf.parquet`.
- **Clases:** al predecir sobre filas de train/val con el nombre de clase asignado, el acierto es alto. Si el orden estuviera mal, el acierto caería en picado.
- La matriz reconstruida con el lote sale idéntica a la actual.
- Los tests existentes siguen pasando y los resultados del pipeline no cambian.

## Fase 1 — Esqueleto — **hecha** (2026-10-15)
**Objetivo:** proyecto Django vacío que arranca.

Incluye:
- Un proyecto y una app.
- SQLite.
- Carpeta de datos configurable fuera del repo, con `.gitignore` y `.env.example`.
- Plantilla base con navegación a las tres pantallas.
- pytest-django.
- EEG-Library instalada en editable.
- La sección «Comandos» de `CLAUDE.md` rellenada.

Aceptación:
- `runserver` muestra la pantalla Grabaciones vacía.
- Los tests pasan.
- Ningún dato queda dentro del repo.

## Fase 2 — Subida y lista de grabaciones — **hecha** (2026-10-16)
**Objetivo:** subir uno o muchos EDF y verlos listados. Todavía no se procesan.

Incluye:
- Modelos `Lote` (parámetros de procesado y fecha) y `Grabacion` (archivo, nombre original, condición opcional y su origen —nombre, manual o vacía—, duración, estado, mensaje de error y resultado JSON).
- Subida múltiple: selector y arrastrar y soltar.
- Validación al subir: el EDF se lee y tiene fs ≥ 256 Hz y los canales esperados. Un archivo inválido se marca con su error y no rompe el resto del lote.
- La condición se lee del nombre con un patrón configurable y se puede editar desde la lista. Si no se reconoce, queda vacía.
- Parámetros con los valores por defecto de `ESTADO.md`, que son los del entrenamiento de los modelos.

Aceptación:
- Subir 1 archivo y subir 20 de golpe funcionan.
- Un archivo corrupto en un lote solo marca ese archivo.
- Hay tests de validación y del patrón de condición.

## Fase 3 — Procesado en segundo plano — **hecha** (2026-10-16)
**Objetivo:** procesar lotes grandes sin bloquear la web y sin infraestructura extra.

Incluye:
- Cola en la propia base de datos.
- Un comando `manage.py` que hace de worker y procesa las grabaciones en cola de una en una, llamando a `analizar_grabacion` y guardando el JSON.
- La lista se actualiza sola cada pocos segundos (estado y progreso del lote).
- Botones para reintentar las fallidas y para reprocesar.

Aceptación:
- Un lote de 20 archivos se procesa entero.
- Si se para el worker y se vuelve a lanzar, continúa donde iba.
- Un error en un archivo no detiene el resto.
- Hay tests del procesado con un EDF pequeño.

## Fase 4 — Pantalla de calidad — **hecha** (2026-10-16)
**Objetivo:** que el investigador vea si la grabación es aprovechable.

Incluye la pantalla 2, construida solo a partir del JSON guardado. El mapa de electrodos se dibuja en SVG con posiciones fijas del Emotiv.

Aceptación:
- Funciona con el fixture de la Fase 0.
- Muestra correctamente grabaciones con 0, 1 o varios electrodos descartados.
- Los colores no dependen solo del tono: el estado también se distingue por forma o texto.

## Fase 5 — Pantalla de análisis y mapa de la cabeza — **hecha** (2026-10-16)
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

## Fase 6 — Exportación CSV — **hecha** (2026-10-16; pendiente: que Rosa/Ana lo confirmen en SPSS)
**Objetivo:** que los investigadores puedan hacer sus análisis en Excel o SPSS.

Incluye:
- CSV de una grabación y CSV del lote, ambos con una fila por grabación.
- Columnas: archivo, condición, duración, electrodos descartados, potencia por electrodo × banda, potencia por zona × banda y, cuando existan, las predicciones de los modelos.
- Ninguna columna lleva «fatiga» en el nombre. Las columnas internas `indice_fatiga_*` del modelo no se exportan con ese nombre.
- Separador, decimal y codificación pensados para Excel en español. **Confirmar con Rosa/Ana antes de cerrar.**

Aceptación:
- El CSV se abre bien en Excel y en SPSS.
- Los nombres de columna son estables y están documentados.

## Fase 7 — Modelos enchufables — **hecha** (2026-10-16)
**Objetivo:** mostrar c1, c2 y c3, y que añadir un modelo nuevo no exija tocar la web.

Incluye:
- Los modelos se registran en una lista de `settings`. Cada modelo es su archivo más su ficha.
- Se aplican sobre las `caracteristicas` ya guardadas en el JSON de cada grabación. Un modelo nuevo que use esas mismas características no obliga a reprocesar.
- Qué modelos se muestran:
  - Con la condición del archivo conocida: los modelos que aplican a esa condición, y se compara la predicción con la etiqueta, avisando si discrepan con alta confianza.
  - Con la condición desconocida: c2 decide reposo o tarea, y según eso se muestra c1 o c3, marcado como «condición estimada».
- Si los parámetros del lote no son los del entrenamiento: «no disponible con estos parámetros».
- La ficha de cada modelo muestra el resultado del test con su IC y el nivel de azar.
- c3 muestra las 5 probabilidades, no solo la clase ganadora.
- Aviso fijo: los modelos no miden fatiga, y parte del acierto puede deberse a la duración o al orden de las tareas.
- `docs/AÑADIR_UN_MODELO.md`, escrito para los investigadores de Ciencias del Deporte.

Aceptación:
- Un modelo de prueba se añade solo con su archivo y una línea en `settings`, y aparece en la pantalla y en el CSV.
- Las cifras mostradas coinciden con `resultados.json` del análisis confirmatorio.
- Con parámetros distintos a los del entrenamiento no se muestran predicciones.

## Fase 8 — Cierre — **hecha** (2026-10-16)
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

**Fase 0** (desde la carpeta TFG, Opus, modo plan):
> Lee EEG-Platform/CLAUDE.md, EEG-Platform/PLAN.md y EEG-Library/CLAUDE.md. Fase 0 de PLAN.md, en EEG-Library, con lo que recoge «Modelos: lo que ya sabemos». Antes de nada, comprueba que el entorno funciona (tests de EEG-Library, lectura de matriz_rf.parquet y carga de los .joblib). Propón un plan y espera mi confirmación.

**Fases 1–8:**
> Fase N de PLAN.md. Propón un plan y espera mi confirmación.

**Al terminar cada fase:**
> Comprueba los criterios de aceptación de la Fase N uno por uno, marca la fase en PLAN.md y actualiza EEG-Platform/docs/DECISIONES.md.