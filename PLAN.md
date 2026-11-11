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
| 9 | Diseño: rediseño visual y visualización topográfica 2D/3D | EEG-Platform | [x] |
| 10 (A) | Tiempo en tarea con la logística: pestaña nueva y cerebro animado | EEG-Library + EEG-Platform | [x] |
| 11 (B) | Tiempo en tarea con EEGNet: segunda cinta y comparación | EEG-Library + EEG-Platform | [x] |

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

## Fase 6 — Exportación CSV — **hecha** (2026-10-16)
**Objetivo:** que los investigadores puedan hacer sus análisis en Excel o SPSS.

Incluye:
- CSV de una grabación y CSV del lote, ambos con una fila por grabación.
- Columnas: archivo, condición, duración, electrodos descartados, potencia por electrodo × banda, potencia por zona × banda y, cuando existan, las predicciones de los modelos.
- Ninguna columna lleva «fatiga» en el nombre. Las columnas internas `indice_fatiga_*` del modelo no se exportan con ese nombre.
- Separador, decimal y codificación pensados para Excel en español.

Aceptación:
- El CSV se abre bien en Excel.
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

## Fase 9 — Diseño — **hecha** (2026-10-17)
**Objetivo:** una interfaz muy vistosa y profesional, pero clara para investigadores que no programan; que parezca una herramienta científica seria, no una plantilla genérica. No cambia la lógica ni los cálculos.

Incluye:
- Rediseño visual con Impeccable (`/teach-impeccable`, `/critique`, `/audit`, `/polish`) y capturas con chrome-devtools solo contra localhost.
- Pantalla Análisis: mapas topográficos 2D por banda (delta, theta, alfa, beta), interactivos (valor por electrodo al pasar el ratón), con escala perceptualmente uniforme (viridis/inferno), escala común o por banda y potencia absoluta o relativa.
- Modelo 3D interactivo de cabeza o cerebro (rotable, JS copiado en `static/`) con el mapa de cada banda proyectado sobre la superficie y los 14 electrodos marcados; quizá vista por las 4 regiones de la librería.
- Aviso visible en 2D y 3D: es una interpolación sobre la superficie, no una localización de fuentes. Posiciones de electrodos tomadas del montaje de la librería.
- Modelo 3D con licencia que permita redistribuirlo y tamaño razonable; origen y licencia anotados en `docs/DECISIONES.md`.

Restricciones: sin CDN ni build de npm (fuentes, JS y librerías en `static/`); ningún texto sugiere que se detecta o mide fatiga; los modelos mantienen resultado en test, intervalo y nivel de azar; todos los valores salen de EEG-Library.

Orden de trabajo (con parada del usuario en los pasos 1 y 2):
1. `/teach-impeccable`, `/critique` de las pantallas actuales y propuesta de dirección visual (2–3 alternativas). **Parar.**
2. Piloto solo en Análisis (2D y 3D), con capturas. **Parar y esperar visto bueno.**
3. Extender el diseño al resto de pantallas.
4. `/audit`, `/polish`, tests pasando, la app arranca y propuesta de mensaje de commit.

Resultado: dirección «visor de neuroimagen» (tema oscuro y claro, IBM Plex), visor de potencia por banda con la cabeza y el cerebro reales de la plantilla fsaverage en 3D y los cuatro mapas 2D sobre el cerebro (interpolación orientativa rotulada), lista, calidad y análisis rediseñados, Lighthouse 100 y 221 tests. Decisiones y licencias en `docs/DECISIONES.md`.

Nota: la Fase 5 decidió «un círculo por electrodo, sin interpolación». La Fase 9 la sustituye por una interpolación suave **rotulada como tal**, manteniendo el valor medido de cada electrodo visible y los descartados sin dato; se registrará en `DECISIONES.md`.

**Ampliación (2026-10-18): portada.** La web abre en `/` con una portada visual y la lista de grabaciones pasa a `/grabaciones/`. Escena 3D (cabeza translúcida, cerebro, 14 sensores y pulsos), cabeza con la rejilla de Análisis, fondo de neuronas homogéneo a la izquierda con efecto al pasar el ratón, título, frase y un botón a Grabaciones; respaldo sin 3D y tema claro propio. Decisiones en `docs/DECISIONES.md`. Respaldo WebP (claro y oscuro) hecho. `/critique` (23/32) y `/polish` de Impeccable hechos sobre la portada (ver `docs/DECISIONES.md`).

---

## Tiempo en tarea: lo que ya sabemos (para las Fases 10 y 11)

Sale de la línea `EEG-Library/analisis/tiempo_en_tarea/`, ya cerrada. Las cifras son de su evaluación en `test` (28 personas), no del desarrollo.

- **Qué se confirmó:** en PASAT y PVTB, el EEG cambia de forma ordenada a lo largo de la tarea en personas no vistas (H2), y ese cambio no lo explican el movimiento ni el contacto (H4). **No se confirmó** que el cambio supere al del reposo con ojos abiertos durante el mismo tiempo (H1). Lo que se mide es el **cambio con el tiempo en tarea**, no el nivel de fatiga de la persona.
- **Logística** (paso 6, `06_test/`): `rel` + `LogisticRegression(C=0.01)`, una por condición, entrenada con `train` + `val` (146 personas) para distinguir el primer tercio de la grabación del último. Entrada por ventana: `log10(pot_rel)` de 14 canales × 4 bandas, centrada por grabación y con los canales excluidos a 0. Modelos en `EEG-Data\processed\fatiga_aguda_test_20261027-190547\modelos\` (se usan `completa_PASAT.joblib` y `completa_PVTB.joblib`).
  - Acierto pareado de tercios (si el último tercio puntúa más que el primero en la misma grabación), grabación completa: **PASAT 0,735 [0,657–0,816]**, 102 grabaciones; **PVTB 0,835 [0,757–0,909]**, 103 grabaciones. Azar: 0,5.
  - ρ media por grabación (puntuación de cada ventana frente a su instante): PASAT +0,162, PVTB +0,180.
- **EEGNet** (paso 4 de `deep_learning/`): EEGNet-8,2 con máscara de canales (2 097 parámetros), un modelo conjunto para PASAT + PVTB, 3 semillas promediadas, entrenada con `train` + `val`. Entrada: ventanas crudas de 4 s remuestreadas a 128 Hz, z-score por grabación y canal, canales excluidos a 0 y mapa de máscara: `(2, 14, 512)`. Pesos `s0.pt`, `s1.pt` y `s2.pt` en `EEG-Data\processed\fatiga_aguda_dl_test_20261031-224217\modelos\`, con sus SHA-256 en `configuracion_dl.json`.
  - ρ PASAT + PVTB +0,160 [+0,130–0,190]; acierto pareado de tercios 0,737 [0,683–0,787].
  - Frente a la logística: Δρ −0,011 [−0,047–+0,028], **no se distinguen**.
- **Una ventana suelta dice poco** (AUC por ventana ≈ 0,58). Lo fiable es la tendencia de la grabación entera.
- **Control:** en reposo con ojos abiertos también hay algo de cambio con el tiempo (ρ +0,104 en `test`; acierto pareado 0,670), probablemente por el asentamiento del casco.
- Cifras y fuentes: `06_test/resultados_test.json` y `deep_learning/04_test_eegnet/resultados_test.json`. Las fichas las copian de ahí, y un test lo comprueba (como en la Fase 7).
- **Nombre** (2026-11-05, sustituye a la excepción del 2026-11-01): la función se llama **«Tiempo en tarea»** y no «Fatiga aguda». Tras la revisión de los tutores, la línea de EEG-Library pasó a llamarse así, porque lo confirmado es el cambio del EEG con el tiempo en la tarea, no que se deba a la fatiga. Con eso desaparece la única excepción a «No detecta ni mide fatiga»: la palabra ya no está en la barra, la pestaña ni el CSV, solo en los avisos que dicen que no se mide. El subtítulo dice siempre lo que se confirmó: «cambio del EEG a lo largo de la tarea».

Nota: la Fase 10 que se implementó el 2026-10-28 (gráfica de líneas por bloques y tabla de tercios en Análisis) se descartó entera sin llegar a commitearse. Esta Fase 10 la sustituye con otro enfoque: pestaña propia, un modelo con su cifra en test y una visualización animada.

## Fase 10 (A) — Tiempo en tarea con la logística — **hecha** (2026-11-01)

Resultado:
- **EEG-Library 0.15.0:** `por_ventana` en `analizar_grabacion`, modelos `tt_pasat_logistica` y `tt_pvtb_logistica` y `puntuar_tiempo_en_tarea`. **Paridad exacta** con el análisis en 20 grabaciones de `train` y `val` (diferencia máxima en la puntuación 1,4·10⁻¹⁴; 20/20 veredictos iguales). Ejemplo anónimo `analisis_grabacion_pasat.json`.
- **EEG-Platform:** pestaña «Tiempo en tarea» con veredicto y cifra en test, cerebro 3D animado (60 fps) con cinta de tiempo, respaldo 2D sin WebGL, 4 columnas `tiempo_en_tarea_*` al final del CSV, guía, capturas y 288 tests.
- **Desviación aprobada en el piloto:** el cerebro muestra por defecto el **cambio desde el principio** (diferencia con la media del primer tercio, paleta divergente morado–verde) y, como opción, el valor en cada momento. Con el valor, las diferencias entre electrodos tapaban el cambio con el tiempo y la animación apenas se movía.
- Decisiones en `docs/DECISIONES.md` («Tiempo en tarea»).
**Objetivo:** que, al abrir una grabación PASAT o PVTB, el investigador vea sin hacer nada cómo cambia el EEG a lo largo de la tarea, según el modelo validado, en una pantalla vistosa para la defensa.

Incluye, en EEG-Library (contrato 0.15.0):
- `analizar_grabacion` guarda también, **por ventana**, su instante y la potencia relativa de los 14 canales × 4 bandas. Es un bloque pequeño del JSON (≈ 50–100 KB en las grabaciones más largas). Sin ventanas crudas.
- Los modelos `completa_PASAT` y `completa_PVTB` se empaquetan en la librería con su ficha: qué hacen, condición, parámetros válidos, versión de scikit-learn, SHA-256 de origen, resultado en test (acierto pareado con IC, azar, personas y grabaciones, ρ) y avisos.
- Una función de la librería, al estilo de `predecir`, que recibe el bloque por ventana y devuelve la puntuación de cada ventana, la ρ de la grabación y el veredicto principio/final. Centra por grabación y anula los canales excluidos, igual que el análisis, y responde «no disponible» si los parámetros no son los del entrenamiento o hay menos de 10 ventanas. La web no calcula nada.

Incluye, en EEG-Platform:
- **Pestaña «Tiempo en tarea»** por grabación, junto a Calidad, Análisis y Modelos. Se muestra con condición PASAT o PVTB. Con otra condición o sin condición, explica a qué grabaciones se aplica y cómo indicarla en la lista. No se estima la condición con c3 (en test acierta 0,488).
- **Cerebro animado:** el visor 3D actual muestra la beta relativa por electrodo en cada tramo de la grabación (media móvil de varias ventanas) y avanza con un botón de reproducir y pausar. Se elige la beta porque es la firma confirmada en PVTB (H3). Escala fija en toda la grabación, para que el cambio se vea.
- **Cinta de tiempo** bajo el cerebro: cada franja se colorea según la puntuación suavizada del modelo, de «se parece al principio» a «se parece al final». Al pinchar o arrastrar en la cinta, el cerebro salta a ese instante.
- **Veredicto en una frase:** si el último tercio puntúa más que el primero, con la cifra del test de esa tarea (acierto pareado, IC y azar sobre la escala de 0 a 1 que ya usan los modelos).
- **«Qué mira el modelo»:** mapa de cabeza con los pesos de la logística por banda, rotulado como descriptivo. *(Quitado al cerrar la fase por decisión del autor: demasiados datos. También se probó y se quitó «Qué ha cambiado en esta grabación»; ver `docs/DECISIONES.md`.)*
- **Aviso fijo:** mide el cambio con el tiempo en tarea, no el nivel de fatiga de la persona; una ventana suelta no es fiable; parte del cambio puede deberse al asentamiento del casco (también aparece en reposo), y el orden del protocolo es fijo.
- Accesibilidad y respaldo: la animación se controla con teclado, respeta `prefers-reduced-motion` y, sin WebGL, usa los mapas 2D. Sin librerías nuevas ni CDN.
- CSV: columnas por grabación con la ρ y el veredicto principio/final (nombres fijados en el plan detallado), documentadas con `documentar_csv`.
- Las grabaciones procesadas antes de la fase no tienen el bloque por ventana: la pestaña lo dice y ofrece reprocesar.
- Documentación: `GUIA_DE_USO.md`, `DECISIONES.md`, capturas y la excepción sobre «fatiga» en `CLAUDE.md` (retirada el 2026-11-05 al renombrar la función a «Tiempo en tarea»).

Aceptación:
- **Paridad con el análisis:** en grabaciones de `train` y `val` (nunca de `test`), las puntuaciones por ventana que calcula la librería desde el EDF coinciden con las de `06_test/evaluacion_test.py` con los mismos `.joblib` (diferencia < 10⁻⁶), y la ρ por grabación también.
- Las cifras de las fichas coinciden con `06_test/resultados_test.json` (test que se omite si no está `EEG-Data`).
- Con parámetros distintos a los del estudio, con menos de 10 ventanas o con otra condición, no se muestran puntuaciones.
- Ningún texto fuera de la pestaña de tiempo en tarea menciona la fatiga, salvo los avisos que ya existían.
- La animación es fluida en el portátil de pruebas, y la pestaña funciona en tema claro y oscuro y sin WebGL.
- Los tests pasan, la app arranca y los tiempos de procesado no empeoran de forma apreciable.

Orden de trabajo (con parada del usuario en los pasos 1, 2 y 3):
1. Plan detallado (formato del bloque por ventana, suavizado, nombres de columnas y textos). **Parar.**
2. EEG-Library: bloque por ventana, modelos empaquetados y paridad. **Parar** con las cifras de la paridad.
3. Piloto de la pestaña con capturas (cerebro, cinta y veredicto). **Parar y esperar visto bueno.**
4. Resto de la pantalla, CSV, documentación, `/audit` y `/polish`, tests y propuesta de mensaje de commit.

## Fase 11 (B) — Tiempo en tarea con EEGNet — **hecha** (2026-11-01)

Resultado:
- **Exportación** (`EEG-Library/analisis/tiempo_en_tarea/deep_learning/05_onnx/`): ONNX = PyTorch con una diferencia máxima de 2,2·10⁻⁶ en 1 757 ventanas de `train`. `onnx`, `onnxscript` y `onnxruntime` solo en `C:\venvs\eeg-dl` (visto bueno del autor).
- **EEG-Library 0.16.0:** `modelado/tiempo_en_tarea_eegnet.py`; `analizar_grabacion` guarda `por_ventana["eegnet"]` (media de las tres semillas; +0,13 s por grabación típica). **Paridad exacta** con el análisis en 20 grabaciones de `train` y `val`: entrada de la red y puntuación idénticas (diferencia 0).
- **EEG-Platform:** segunda pista «Red neuronal (EEGNet)» en la cinta, con el mismo cabezal; su propio apartado de resultado al lado del de la logística (frase y escala de fiabilidad: acierto 0,737 en PASAT y PVTB juntas; al principio fue una frase de acuerdo bajo el veredicto, cambiada el 2026-11-02 a petición del autor); ρ y «no se distinguen» de la logística en «Detalles»; 2 columnas `tiempo_en_tarea_eegnet_*` al final del CSV; grabaciones sin EEGNet siguen con la logística y un aviso. Decisión del autor: segunda cinta (no selector ni solo frase).
- Declarado en la ficha y en la pantalla: el test evaluó cada semilla por separado; la plataforma combina las tres.
**Objetivo:** añadir EEGNet como segundo modelo en la misma pestaña, para enseñar que un modelo clásico y uno de deep learning ven lo mismo. **Es prescindible:** si la paridad no sale, la fase se para y la Fase 10 queda intacta.

Incluye:
- **Exportación a ONNX** de los tres pesos (`s0`–`s2`), una sola vez, con el entorno `C:\venvs\eeg-dl`, comprobando antes sus SHA-256 con `configuracion_dl.json`. El script de exportación vive en la línea de análisis. La web y la librería solo usan `onnxruntime`, que ya es dependencia: no se instala PyTorch.
- **EEG-Library:** preparación de la entrada tal como en el entrenamiento (remuestreo a 128 Hz con `resample_poly(x, 1, 2)`, z-score por grabación y canal, canales excluidos a 0 y mapa de máscara) y puntuación con las tres semillas promediadas. Se hace **durante el procesado**, porque las ventanas crudas no se guardan; como el modelo es conjunto para PASAT y PVTB, cambiar la condición no obliga a reprocesar. Ficha con su resultado en test y la comparación con la logística.
- **EEG-Platform:** segunda cinta bajo la de la logística, alineada en el tiempo; una frase sobre cuánto coinciden en esa grabación, y el resultado en test de los dos con el veredicto «no se distinguen». Columnas en el CSV.

Aceptación:
- **ONNX = PyTorch:** con el mismo tensor de ventanas de `train`, las puntuaciones coinciden (diferencia < 10⁻⁵).
- **Preparación = análisis:** en grabaciones de `train` y `val` (nunca de `test`), el tensor y las puntuaciones que calcula la librería desde el EDF coinciden con los de `deep_learning/04_test_eegnet/` (`comun_dl.py`).
- Las cifras de la ficha coinciden con `deep_learning/04_test_eegnet/resultados_test.json`.
- El procesado de una grabación no se alarga de forma apreciable (≈ 1 ms por ventana y semilla, medido en el desarrollo).
- Los tests pasan y la app arranca.

Orden de trabajo (con parada del usuario en los pasos 1 y 2):
1. Plan detallado. **Parar.**
2. Exportación y las dos paridades. **Parar** con las cifras. Si no salen, se documenta y se cierra la fase aquí.
3. Integración en la pestaña, CSV, documentación, tests y propuesta de mensaje de commit.
