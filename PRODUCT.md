# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Investigadores de Ciencias del Deporte (sin conocimientos de programación) que procesan grabaciones EEG del casco Emotiv EPOC X (EDF, 14 canales, 256 Hz) en su propio equipo. Secundario con el mismo peso visual: el tribunal del TFG y la defensa (capturas en la memoria, demo en proyector).

## Product Purpose
Herramienta web local (Django) para subir uno o muchos EDF, procesarlos con EEG-Library, revisar la calidad de la señal, ver la potencia por banda (delta, theta, alfa, beta) y por zona, consultar modelos de IA enchufables (c1, c2, c3) y exportar CSV para Excel/SPSS. Éxito: un investigador la usa sin ayuda y entiende lo que ve y lo que no puede concluirse.

## Positioning
Herramienta científica local, honesta con sus límites: cada resultado de modelo se muestra con su exactitud en el test independiente, su intervalo y el nivel de azar. No es un producto comercial ni un panel de monitorización.

## Operating Context
Windows, uso local en 127.0.0.1, sin internet (sin CDN ni build de npm; fuentes, JS y librerías en `static/`). Plantillas Django con CSS propio y JS mínimo. Interfaz en español. Pantallas: Grabaciones (subida y lista), Calidad, Análisis (potencias, mapa de la cabeza, modelos) y descarga CSV.

## Capabilities and Constraints
- Todos los valores salen de EEG-Library; la web no recalcula (salvo la media de la cabeza).
- Ningún texto, nombre ni gráfica puede sugerir que se detecta o mide fatiga.
- Los modelos solo predicen con los parámetros de entrenamiento; si no, «no disponible».
- Electrodos descartados: sin valor en ningún sitio.
- Con 14 electrodos no se localizan fuentes: cualquier mapa suave es una interpolación orientativa sobre la superficie.
- Datos de menores: nunca a git ni a servicios externos; las grabaciones viven fuera del repo.
- Cabeza y cerebro 3D: plantilla fsaverage (FreeSurfer; MNE-Python y nilearn, BSD) con licencias en `static/models/`.

## Evidence on Hand
Grabaciones reales en EEG-Data (solo lectura; para diseñar se usan copias de train/val, nunca del test). Fixture anónimo en `tests/fixtures/`. Capturas reproducibles con `docs/generar_capturas.py`.

## Product Principles
1. Claridad antes que adorno: un investigador debe entender cada pantalla sin explicación.
2. Honestidad visible: límites, azar e interpolación se dicen en la propia interfaz.
3. Nada depende solo del color (estado, escala, selección).
4. Local y autosuficiente: funciona sin internet.
5. Aspecto de instrumento científico serio, no de plantilla genérica.

## Accessibility & Inclusion
Daltonismo (escalas perceptualmente uniformes, estado por forma y texto). Tema claro y oscuro. Buen contraste en proyector y pantallas de portátil. WCAG AA como mínimo.
