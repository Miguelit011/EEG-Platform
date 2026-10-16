# Prueba completa con un lote real

Resumen **agregado** de una prueba de extremo a extremo con 100 EDF reales del estudio (2026-10-16).
No incluye nombres de archivo ni de participantes: los datos son de menores y esta carpeta va a git.

## Cómo se hizo

- **Selección:** 100 EDF de `dataset_final`, **solo de sujetos de entrenamiento y validación**
  (`splits.csv`). Se excluyeron los 730 EDF de los 28 sujetos del test: el análisis confirmatorio
  se abrió una sola vez y no se vuelve a pasar por los modelos. El reparto es estratificado: uno por
  cada combinación de centro y condición (56 combinaciones: 8 centros × 7 condiciones) y otros 44 al
  azar (semilla fija) entre el resto. Total: **378 MB**.
- **Cómo:** el flujo normal de la plataforma, con una carpeta de datos temporal fuera del repo:
  subida de los 100 archivos en un solo lote con los parámetros del estudio (CAR condicional,
  1–30 Hz, notch 50 Hz), procesado con `manage.py procesar`, visita a las pantallas de calidad y
  análisis de cada grabación y descarga del CSV del lote.
- **Equipo:** AMD Ryzen 5 5600G (6 núcleos, 12 hilos), 15,3 GB de RAM (6,6 GB libres), Windows 11.
  El procesador eligió **4 procesos** por sí solo (mitad de los hilos, máximo 4; memoria suficiente).

## Resultados

| | |
|---|---|
| Subida y validación de los 100 EDF (378 MB) | **2,2 s** (solo se lee la cabecera de cada archivo) |
| Procesado completo (calidad, ICA, potencia y 70 características) | **97 s** en total: **0,97 s por EDF**, unos **62 EDF por minuto** |
| Grabaciones procesadas | **99 de 100** |
| Grabaciones con error | **1**: «Fase ica: se requieren al menos 2 canales buenos (recibidos: 1)». Es una grabación casi sin electrodos buenos; el error es el esperado y no detuvo al resto |
| Archivos de 128 Hz (aceptados y remuestreados a 256 Hz) | 2 |
| Electrodos buenos por grabación (de 14) | 9: 6 · 10: 9 · 11: 23 · 12: 27 · 13: 22 · 14: 12 |
| Grabaciones con menos de 8 electrodos buenos (aviso) | 0 |
| Pantallas de calidad y análisis (2 × 99) | **198 de 198** se muestran sin error |
| CSV del lote | 99 filas × 182 columnas, 138 KB, generado en 0,7 s |
| CSV abierto con **Excel 16** (Windows en español) | 100 filas (con cabecera) × 182 columnas, números como números, **sin errores** de celda |

Extrapolación (no medida): procesar los 4.574 EDF del estudio con este equipo tardaría del orden de
**75 minutos** con 4 procesos.

### Los modelos sobre este lote (solo una comprobación de que funcionan)

Las 99 grabaciones son de sujetos con los que **se entrenaron** los modelos, así que estas cifras
**no miden rendimiento** (el rendimiento está en el test independiente: c1 0,855, c2 0,851 y
c3 0,488). Sirven para comprobar el cableado: con la condición conocida, la predicción coincide
con ella en 90 de 99 grabaciones (c2), 22 de 26 (c1) y 35 de 73 (c3), el mismo orden de magnitud
que ya se vio en entrenamiento.

## Qué demuestra

- Un lote de cientos de EDF se sube, se procesa y se exporta sin intervención, en minutos.
- Un archivo malo no detiene al resto: queda marcado con su motivo.
- El CSV es utilizable directamente en Excel.
- La plataforma funciona con grabaciones de las distintas versiones de EmotivPro del estudio
  (128 y 256 Hz).

## Cómo repetirla

Con otra carpeta de datos (`EEG_PLATFORM_DATOS`): subir los EDF desde la web, mantener abierto el
procesador y, al terminar, descargar el CSV del lote. Las cifras de tiempo dependen del equipo.
