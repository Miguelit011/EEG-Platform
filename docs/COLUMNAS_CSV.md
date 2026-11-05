# Columnas del CSV

Generado con `manage.py documentar_csv`; no se edita a mano. Un test comprueba que coincide con las columnas que exporta la plataforma.

## Formato

- Una fila por grabación procesada. El CSV de una grabación y el de un lote tienen las mismas columnas.
- Separador de columnas `;`, decimal `,`, codificación UTF-8 con BOM y saltos de línea de Windows: es lo que Excel en español abre directamente. Se cambia en `settings` (`CSV_SEPARADOR`, `CSV_DECIMAL`, `CSV_CODIFICACION`).
- Una celda vacía significa «sin dato»: electrodo descartado, zona sin electrodos válidos o parámetro que no se aplicó. Nunca se escribe un cero en su lugar.
- Los nombres de columna no llevan tildes ni espacios, para que SPSS y R los acepten como nombres de variable. Son estables: no cambian entre versiones.
- Los valores de potencia son los mismos que se ven en pantalla. La potencia **relativa** es la proporción (de 0 a 1) de la potencia total de 1 a 30 Hz que cae en la banda; la **absoluta** va en log10 de V².
- «Toda la cabeza» es la media de la potencia relativa de los electrodos válidos.
- Los electrodos descartados no tienen valor de potencia: se calculó con señal que no pasó por CAR ni ICA y no es comparable.
- Bandas: `delta` (1–4 Hz), `theta` (4–8 Hz), `alfa` (8–13 Hz), `beta` (13–30 Hz). Zonas: `frontal`, `frontocentral`, `temporal`, `posterior`.

Total: 188 columnas.

## Identificación

| Columna | Significado | Unidad |
|---|---|---|
| `archivo` | Nombre del archivo EDF subido | texto |
| `lote` | Número del lote en que se subió | número |
| `condicion` | Condición de la grabación (vacía si no se conoce) | texto |
| `origen_condicion` | De dónde sale la condición: nombre (del nombre del archivo), manual o vacia | texto |
| `duracion_s` | Duración del registro, antes de recortar los márgenes | segundos |
| `n_epocas` | Ventanas (épocas) analizadas | número |
| `frecuencia_original_hz` | Frecuencia de muestreo del archivo original | Hz |
| `remuestreada` | 1 si el archivo se remuestreó a 256 Hz; 0 si no | 1/0 |

## Calidad y procesado aplicado

| Columna | Significado | Unidad |
|---|---|---|
| `electrodos_buenos` | Electrodos buenos de los 14 del Emotiv | número |
| `electrodos_descartados` | Electrodos descartados, separados por «\|» (vacío si no hay ninguno) | texto |
| `referencia` | Referencia pedida: car_condicional u original | texto |
| `car_aplicada` | 1 si se aplicó la CAR; 0 si no (referencia original o menos de 6 electrodos buenos) | 1/0 |
| `banda_min_hz` | Inicio del paso banda | Hz |
| `banda_max_hz` | Fin del paso banda | Hz |
| `notch_hz` | Frecuencia del filtro notch (vacío si no se aplicó) | Hz |
| `ica_n_componentes_eliminadas` | Componentes de ICA eliminadas (artefactos oculares) | número |
| `ica_componentes_eliminadas` | Números de las componentes eliminadas, separados por «\|» | texto |

## Toda la cabeza

| Columna | Significado | Unidad |
|---|---|---|
| `cabeza_delta_rel` | Potencia relativa en delta: media de los electrodos válidos | proporción 0–1 |
| `cabeza_theta_rel` | Potencia relativa en theta: media de los electrodos válidos | proporción 0–1 |
| `cabeza_alfa_rel` | Potencia relativa en alfa: media de los electrodos válidos | proporción 0–1 |
| `cabeza_beta_rel` | Potencia relativa en beta: media de los electrodos válidos | proporción 0–1 |

## Por zona

| Columna | Significado | Unidad |
|---|---|---|
| `zona_frontal_delta_rel` | Potencia relativa en delta, zona frontal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontal_theta_rel` | Potencia relativa en theta, zona frontal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontal_alfa_rel` | Potencia relativa en alfa, zona frontal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontal_beta_rel` | Potencia relativa en beta, zona frontal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontal_delta_logabs` | Potencia absoluta en delta, zona frontal | log10 de V² |
| `zona_frontal_theta_logabs` | Potencia absoluta en theta, zona frontal | log10 de V² |
| `zona_frontal_alfa_logabs` | Potencia absoluta en alfa, zona frontal | log10 de V² |
| `zona_frontal_beta_logabs` | Potencia absoluta en beta, zona frontal | log10 de V² |
| `zona_frontocentral_delta_rel` | Potencia relativa en delta, zona frontocentral (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontocentral_theta_rel` | Potencia relativa en theta, zona frontocentral (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontocentral_alfa_rel` | Potencia relativa en alfa, zona frontocentral (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontocentral_beta_rel` | Potencia relativa en beta, zona frontocentral (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_frontocentral_delta_logabs` | Potencia absoluta en delta, zona frontocentral | log10 de V² |
| `zona_frontocentral_theta_logabs` | Potencia absoluta en theta, zona frontocentral | log10 de V² |
| `zona_frontocentral_alfa_logabs` | Potencia absoluta en alfa, zona frontocentral | log10 de V² |
| `zona_frontocentral_beta_logabs` | Potencia absoluta en beta, zona frontocentral | log10 de V² |
| `zona_temporal_delta_rel` | Potencia relativa en delta, zona temporal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_temporal_theta_rel` | Potencia relativa en theta, zona temporal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_temporal_alfa_rel` | Potencia relativa en alfa, zona temporal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_temporal_beta_rel` | Potencia relativa en beta, zona temporal (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_temporal_delta_logabs` | Potencia absoluta en delta, zona temporal | log10 de V² |
| `zona_temporal_theta_logabs` | Potencia absoluta en theta, zona temporal | log10 de V² |
| `zona_temporal_alfa_logabs` | Potencia absoluta en alfa, zona temporal | log10 de V² |
| `zona_temporal_beta_logabs` | Potencia absoluta en beta, zona temporal | log10 de V² |
| `zona_posterior_delta_rel` | Potencia relativa en delta, zona posterior (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_posterior_theta_rel` | Potencia relativa en theta, zona posterior (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_posterior_alfa_rel` | Potencia relativa en alfa, zona posterior (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_posterior_beta_rel` | Potencia relativa en beta, zona posterior (vacío si no hay electrodos válidos) | proporción 0–1 |
| `zona_posterior_delta_logabs` | Potencia absoluta en delta, zona posterior | log10 de V² |
| `zona_posterior_theta_logabs` | Potencia absoluta en theta, zona posterior | log10 de V² |
| `zona_posterior_alfa_logabs` | Potencia absoluta en alfa, zona posterior | log10 de V² |
| `zona_posterior_beta_logabs` | Potencia absoluta en beta, zona posterior | log10 de V² |

## Por electrodo

| Columna | Significado | Unidad |
|---|---|---|
| `rel_AF3_delta` | Potencia relativa en delta, electrodo AF3 (vacío si está descartado) | proporción 0–1 |
| `rel_AF3_theta` | Potencia relativa en theta, electrodo AF3 (vacío si está descartado) | proporción 0–1 |
| `rel_AF3_alfa` | Potencia relativa en alfa, electrodo AF3 (vacío si está descartado) | proporción 0–1 |
| `rel_AF3_beta` | Potencia relativa en beta, electrodo AF3 (vacío si está descartado) | proporción 0–1 |
| `logabs_AF3_delta` | Potencia absoluta en delta, electrodo AF3 (vacío si está descartado) | log10 de V² |
| `logabs_AF3_theta` | Potencia absoluta en theta, electrodo AF3 (vacío si está descartado) | log10 de V² |
| `logabs_AF3_alfa` | Potencia absoluta en alfa, electrodo AF3 (vacío si está descartado) | log10 de V² |
| `logabs_AF3_beta` | Potencia absoluta en beta, electrodo AF3 (vacío si está descartado) | log10 de V² |
| `rel_F7_delta` | Potencia relativa en delta, electrodo F7 (vacío si está descartado) | proporción 0–1 |
| `rel_F7_theta` | Potencia relativa en theta, electrodo F7 (vacío si está descartado) | proporción 0–1 |
| `rel_F7_alfa` | Potencia relativa en alfa, electrodo F7 (vacío si está descartado) | proporción 0–1 |
| `rel_F7_beta` | Potencia relativa en beta, electrodo F7 (vacío si está descartado) | proporción 0–1 |
| `logabs_F7_delta` | Potencia absoluta en delta, electrodo F7 (vacío si está descartado) | log10 de V² |
| `logabs_F7_theta` | Potencia absoluta en theta, electrodo F7 (vacío si está descartado) | log10 de V² |
| `logabs_F7_alfa` | Potencia absoluta en alfa, electrodo F7 (vacío si está descartado) | log10 de V² |
| `logabs_F7_beta` | Potencia absoluta en beta, electrodo F7 (vacío si está descartado) | log10 de V² |
| `rel_F3_delta` | Potencia relativa en delta, electrodo F3 (vacío si está descartado) | proporción 0–1 |
| `rel_F3_theta` | Potencia relativa en theta, electrodo F3 (vacío si está descartado) | proporción 0–1 |
| `rel_F3_alfa` | Potencia relativa en alfa, electrodo F3 (vacío si está descartado) | proporción 0–1 |
| `rel_F3_beta` | Potencia relativa en beta, electrodo F3 (vacío si está descartado) | proporción 0–1 |
| `logabs_F3_delta` | Potencia absoluta en delta, electrodo F3 (vacío si está descartado) | log10 de V² |
| `logabs_F3_theta` | Potencia absoluta en theta, electrodo F3 (vacío si está descartado) | log10 de V² |
| `logabs_F3_alfa` | Potencia absoluta en alfa, electrodo F3 (vacío si está descartado) | log10 de V² |
| `logabs_F3_beta` | Potencia absoluta en beta, electrodo F3 (vacío si está descartado) | log10 de V² |
| `rel_FC5_delta` | Potencia relativa en delta, electrodo FC5 (vacío si está descartado) | proporción 0–1 |
| `rel_FC5_theta` | Potencia relativa en theta, electrodo FC5 (vacío si está descartado) | proporción 0–1 |
| `rel_FC5_alfa` | Potencia relativa en alfa, electrodo FC5 (vacío si está descartado) | proporción 0–1 |
| `rel_FC5_beta` | Potencia relativa en beta, electrodo FC5 (vacío si está descartado) | proporción 0–1 |
| `logabs_FC5_delta` | Potencia absoluta en delta, electrodo FC5 (vacío si está descartado) | log10 de V² |
| `logabs_FC5_theta` | Potencia absoluta en theta, electrodo FC5 (vacío si está descartado) | log10 de V² |
| `logabs_FC5_alfa` | Potencia absoluta en alfa, electrodo FC5 (vacío si está descartado) | log10 de V² |
| `logabs_FC5_beta` | Potencia absoluta en beta, electrodo FC5 (vacío si está descartado) | log10 de V² |
| `rel_T7_delta` | Potencia relativa en delta, electrodo T7 (vacío si está descartado) | proporción 0–1 |
| `rel_T7_theta` | Potencia relativa en theta, electrodo T7 (vacío si está descartado) | proporción 0–1 |
| `rel_T7_alfa` | Potencia relativa en alfa, electrodo T7 (vacío si está descartado) | proporción 0–1 |
| `rel_T7_beta` | Potencia relativa en beta, electrodo T7 (vacío si está descartado) | proporción 0–1 |
| `logabs_T7_delta` | Potencia absoluta en delta, electrodo T7 (vacío si está descartado) | log10 de V² |
| `logabs_T7_theta` | Potencia absoluta en theta, electrodo T7 (vacío si está descartado) | log10 de V² |
| `logabs_T7_alfa` | Potencia absoluta en alfa, electrodo T7 (vacío si está descartado) | log10 de V² |
| `logabs_T7_beta` | Potencia absoluta en beta, electrodo T7 (vacío si está descartado) | log10 de V² |
| `rel_P7_delta` | Potencia relativa en delta, electrodo P7 (vacío si está descartado) | proporción 0–1 |
| `rel_P7_theta` | Potencia relativa en theta, electrodo P7 (vacío si está descartado) | proporción 0–1 |
| `rel_P7_alfa` | Potencia relativa en alfa, electrodo P7 (vacío si está descartado) | proporción 0–1 |
| `rel_P7_beta` | Potencia relativa en beta, electrodo P7 (vacío si está descartado) | proporción 0–1 |
| `logabs_P7_delta` | Potencia absoluta en delta, electrodo P7 (vacío si está descartado) | log10 de V² |
| `logabs_P7_theta` | Potencia absoluta en theta, electrodo P7 (vacío si está descartado) | log10 de V² |
| `logabs_P7_alfa` | Potencia absoluta en alfa, electrodo P7 (vacío si está descartado) | log10 de V² |
| `logabs_P7_beta` | Potencia absoluta en beta, electrodo P7 (vacío si está descartado) | log10 de V² |
| `rel_O1_delta` | Potencia relativa en delta, electrodo O1 (vacío si está descartado) | proporción 0–1 |
| `rel_O1_theta` | Potencia relativa en theta, electrodo O1 (vacío si está descartado) | proporción 0–1 |
| `rel_O1_alfa` | Potencia relativa en alfa, electrodo O1 (vacío si está descartado) | proporción 0–1 |
| `rel_O1_beta` | Potencia relativa en beta, electrodo O1 (vacío si está descartado) | proporción 0–1 |
| `logabs_O1_delta` | Potencia absoluta en delta, electrodo O1 (vacío si está descartado) | log10 de V² |
| `logabs_O1_theta` | Potencia absoluta en theta, electrodo O1 (vacío si está descartado) | log10 de V² |
| `logabs_O1_alfa` | Potencia absoluta en alfa, electrodo O1 (vacío si está descartado) | log10 de V² |
| `logabs_O1_beta` | Potencia absoluta en beta, electrodo O1 (vacío si está descartado) | log10 de V² |
| `rel_O2_delta` | Potencia relativa en delta, electrodo O2 (vacío si está descartado) | proporción 0–1 |
| `rel_O2_theta` | Potencia relativa en theta, electrodo O2 (vacío si está descartado) | proporción 0–1 |
| `rel_O2_alfa` | Potencia relativa en alfa, electrodo O2 (vacío si está descartado) | proporción 0–1 |
| `rel_O2_beta` | Potencia relativa en beta, electrodo O2 (vacío si está descartado) | proporción 0–1 |
| `logabs_O2_delta` | Potencia absoluta en delta, electrodo O2 (vacío si está descartado) | log10 de V² |
| `logabs_O2_theta` | Potencia absoluta en theta, electrodo O2 (vacío si está descartado) | log10 de V² |
| `logabs_O2_alfa` | Potencia absoluta en alfa, electrodo O2 (vacío si está descartado) | log10 de V² |
| `logabs_O2_beta` | Potencia absoluta en beta, electrodo O2 (vacío si está descartado) | log10 de V² |
| `rel_P8_delta` | Potencia relativa en delta, electrodo P8 (vacío si está descartado) | proporción 0–1 |
| `rel_P8_theta` | Potencia relativa en theta, electrodo P8 (vacío si está descartado) | proporción 0–1 |
| `rel_P8_alfa` | Potencia relativa en alfa, electrodo P8 (vacío si está descartado) | proporción 0–1 |
| `rel_P8_beta` | Potencia relativa en beta, electrodo P8 (vacío si está descartado) | proporción 0–1 |
| `logabs_P8_delta` | Potencia absoluta en delta, electrodo P8 (vacío si está descartado) | log10 de V² |
| `logabs_P8_theta` | Potencia absoluta en theta, electrodo P8 (vacío si está descartado) | log10 de V² |
| `logabs_P8_alfa` | Potencia absoluta en alfa, electrodo P8 (vacío si está descartado) | log10 de V² |
| `logabs_P8_beta` | Potencia absoluta en beta, electrodo P8 (vacío si está descartado) | log10 de V² |
| `rel_T8_delta` | Potencia relativa en delta, electrodo T8 (vacío si está descartado) | proporción 0–1 |
| `rel_T8_theta` | Potencia relativa en theta, electrodo T8 (vacío si está descartado) | proporción 0–1 |
| `rel_T8_alfa` | Potencia relativa en alfa, electrodo T8 (vacío si está descartado) | proporción 0–1 |
| `rel_T8_beta` | Potencia relativa en beta, electrodo T8 (vacío si está descartado) | proporción 0–1 |
| `logabs_T8_delta` | Potencia absoluta en delta, electrodo T8 (vacío si está descartado) | log10 de V² |
| `logabs_T8_theta` | Potencia absoluta en theta, electrodo T8 (vacío si está descartado) | log10 de V² |
| `logabs_T8_alfa` | Potencia absoluta en alfa, electrodo T8 (vacío si está descartado) | log10 de V² |
| `logabs_T8_beta` | Potencia absoluta en beta, electrodo T8 (vacío si está descartado) | log10 de V² |
| `rel_FC6_delta` | Potencia relativa en delta, electrodo FC6 (vacío si está descartado) | proporción 0–1 |
| `rel_FC6_theta` | Potencia relativa en theta, electrodo FC6 (vacío si está descartado) | proporción 0–1 |
| `rel_FC6_alfa` | Potencia relativa en alfa, electrodo FC6 (vacío si está descartado) | proporción 0–1 |
| `rel_FC6_beta` | Potencia relativa en beta, electrodo FC6 (vacío si está descartado) | proporción 0–1 |
| `logabs_FC6_delta` | Potencia absoluta en delta, electrodo FC6 (vacío si está descartado) | log10 de V² |
| `logabs_FC6_theta` | Potencia absoluta en theta, electrodo FC6 (vacío si está descartado) | log10 de V² |
| `logabs_FC6_alfa` | Potencia absoluta en alfa, electrodo FC6 (vacío si está descartado) | log10 de V² |
| `logabs_FC6_beta` | Potencia absoluta en beta, electrodo FC6 (vacío si está descartado) | log10 de V² |
| `rel_F4_delta` | Potencia relativa en delta, electrodo F4 (vacío si está descartado) | proporción 0–1 |
| `rel_F4_theta` | Potencia relativa en theta, electrodo F4 (vacío si está descartado) | proporción 0–1 |
| `rel_F4_alfa` | Potencia relativa en alfa, electrodo F4 (vacío si está descartado) | proporción 0–1 |
| `rel_F4_beta` | Potencia relativa en beta, electrodo F4 (vacío si está descartado) | proporción 0–1 |
| `logabs_F4_delta` | Potencia absoluta en delta, electrodo F4 (vacío si está descartado) | log10 de V² |
| `logabs_F4_theta` | Potencia absoluta en theta, electrodo F4 (vacío si está descartado) | log10 de V² |
| `logabs_F4_alfa` | Potencia absoluta en alfa, electrodo F4 (vacío si está descartado) | log10 de V² |
| `logabs_F4_beta` | Potencia absoluta en beta, electrodo F4 (vacío si está descartado) | log10 de V² |
| `rel_F8_delta` | Potencia relativa en delta, electrodo F8 (vacío si está descartado) | proporción 0–1 |
| `rel_F8_theta` | Potencia relativa en theta, electrodo F8 (vacío si está descartado) | proporción 0–1 |
| `rel_F8_alfa` | Potencia relativa en alfa, electrodo F8 (vacío si está descartado) | proporción 0–1 |
| `rel_F8_beta` | Potencia relativa en beta, electrodo F8 (vacío si está descartado) | proporción 0–1 |
| `logabs_F8_delta` | Potencia absoluta en delta, electrodo F8 (vacío si está descartado) | log10 de V² |
| `logabs_F8_theta` | Potencia absoluta en theta, electrodo F8 (vacío si está descartado) | log10 de V² |
| `logabs_F8_alfa` | Potencia absoluta en alfa, electrodo F8 (vacío si está descartado) | log10 de V² |
| `logabs_F8_beta` | Potencia absoluta en beta, electrodo F8 (vacío si está descartado) | log10 de V² |
| `rel_AF4_delta` | Potencia relativa en delta, electrodo AF4 (vacío si está descartado) | proporción 0–1 |
| `rel_AF4_theta` | Potencia relativa en theta, electrodo AF4 (vacío si está descartado) | proporción 0–1 |
| `rel_AF4_alfa` | Potencia relativa en alfa, electrodo AF4 (vacío si está descartado) | proporción 0–1 |
| `rel_AF4_beta` | Potencia relativa en beta, electrodo AF4 (vacío si está descartado) | proporción 0–1 |
| `logabs_AF4_delta` | Potencia absoluta en delta, electrodo AF4 (vacío si está descartado) | log10 de V² |
| `logabs_AF4_theta` | Potencia absoluta en theta, electrodo AF4 (vacío si está descartado) | log10 de V² |
| `logabs_AF4_alfa` | Potencia absoluta en alfa, electrodo AF4 (vacío si está descartado) | log10 de V² |
| `logabs_AF4_beta` | Potencia absoluta en beta, electrodo AF4 (vacío si está descartado) | log10 de V² |

## Trazabilidad

| Columna | Significado | Unidad |
|---|---|---|
| `version_eeg_library` | Versión de EEG-Library que procesó la grabación | texto |
| `fecha_analisis` | Fecha y hora del procesado | texto |

## Modelos

| Columna | Significado | Unidad |
|---|---|---|
| `c1_oa_oc_logistica_clase` | Ojos abiertos / ojos cerrados: clase predicha (vacía si el modelo no se aplica a la grabación) | texto |
| `c1_oa_oc_logistica_p_OA` | Ojos abiertos / ojos cerrados: probabilidad de la clase OA | proporción 0–1 |
| `c1_oa_oc_logistica_p_OC` | Ojos abiertos / ojos cerrados: probabilidad de la clase OC | proporción 0–1 |
| `c1_oa_oc_logistica_condicion_estimada` | Ojos abiertos / ojos cerrados: 1 si se aplicó porque la condición de la grabación no se conocía y se estimó; 0 si se conocía (vacía si el modelo no se aplica) | 1/0 |
| `c2_reposo_tarea_logistica_clase` | Reposo / tarea: clase predicha (vacía si el modelo no se aplica a la grabación) | texto |
| `c2_reposo_tarea_logistica_p_reposo` | Reposo / tarea: probabilidad de la clase reposo | proporción 0–1 |
| `c2_reposo_tarea_logistica_p_tarea` | Reposo / tarea: probabilidad de la clase tarea | proporción 0–1 |
| `c2_reposo_tarea_logistica_condicion_estimada` | Reposo / tarea: 1 si se aplicó porque la condición de la grabación no se conocía y se estimó; 0 si se conocía (vacía si el modelo no se aplica) | 1/0 |
| `c3_tareas_logistica_clase` | Cuál de las 5 tareas: clase predicha (vacía si el modelo no se aplica a la grabación) | texto |
| `c3_tareas_logistica_p_STROOP` | Cuál de las 5 tareas: probabilidad de la clase STROOP | proporción 0–1 |
| `c3_tareas_logistica_p_PASAT` | Cuál de las 5 tareas: probabilidad de la clase PASAT | proporción 0–1 |
| `c3_tareas_logistica_p_PVTB` | Cuál de las 5 tareas: probabilidad de la clase PVTB | proporción 0–1 |
| `c3_tareas_logistica_p_MSIT` | Cuál de las 5 tareas: probabilidad de la clase MSIT | proporción 0–1 |
| `c3_tareas_logistica_p_PVSAT` | Cuál de las 5 tareas: probabilidad de la clase PVSAT | proporción 0–1 |
| `c3_tareas_logistica_condicion_estimada` | Cuál de las 5 tareas: 1 si se aplicó porque la condición de la grabación no se conocía y se estimó; 0 si se conocía (vacía si el modelo no se aplica) | 1/0 |

## Tiempo en tarea

| Columna | Significado | Unidad |
|---|---|---|
| `tiempo_en_tarea_rho` | Tendencia a lo largo de la grabación: correlación de Spearman entre la puntuación de cada ventana y su momento (vacía si no es PASAT ni PVTB) | −1 a 1 |
| `tiempo_en_tarea_p_primer_tercio` | Probabilidad de «último tercio» que el modelo da a la media del primer tercio | proporción 0–1 |
| `tiempo_en_tarea_p_ultimo_tercio` | Probabilidad de «último tercio» que el modelo da a la media del último tercio | proporción 0–1 |
| `tiempo_en_tarea_final_mayor` | 1 si el último tercio se parece más al final de la tarea que el primero; 0 si no (vacía si empatan o no se aplica) | 1/0 |
| `tiempo_en_tarea_eegnet_rho` | Lo mismo que tiempo_en_tarea_rho, con la red neuronal EEGNet (vacía si no es PASAT ni PVTB, o si la grabación se procesó antes de que la plataforma incluyera EEGNet) | −1 a 1 |
| `tiempo_en_tarea_eegnet_final_mayor` | 1 si, según EEGNet, el último tercio se parece más al final de la tarea que el primero; 0 si no (vacía si empatan o no se aplica) | 1/0 |
