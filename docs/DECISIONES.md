# Decisiones

Decisiones relevantes de cada fase, con su porqué. Las más recientes, abajo.

## Fase 0 — Contrato con la librería (2026-10-15, en EEG-Library)

- **Parámetros de procesado como opciones cerradas.** La referencia (`car_condicional` u `original`), el paso banda (1–30 o 3–30 Hz) y el notch (50 Hz o ninguno) no admiten valores libres. Así cada combinación se puede declarar en la ficha de un modelo y comparar con la que se aplicó; un valor libre no coincidiría nunca con ningún modelo.
- **`predecir` no lleva reglas por modelo.** Compara los `parametros_validos` de la ficha con los aplicados. Si difieren, devuelve «no disponible» con los parámetros que requiere. c1, c2 y c3 declaran los del estudio.
- **ICA con `n − 1` componentes también cuando la CAR se omite.** Así se procesó el dataset, y una grabación de val tiene 4 canales buenos. Cambiarlo rompería la igualdad con `matriz_rf.parquet`. Con referencia `original` (sin CAR) se usan `n` componentes, porque no hay pérdida de rango.
- **Las características salen del mismo código que la matriz.** La agregación por grabación se separó de `construir_matriz_rf` en `resumir_por_grabacion`, que no necesita VAS ni condición. Verificado: la matriz reconstruida es idéntica, y la paridad es exacta en 13 EDF de train/val.
- **Alias neutro `indice_theta_alfa_*`.** En el JSON sustituye a `indice_fatiga_*`, para que la web no sugiera fatiga. `predecir` lo deshace antes de llamar al modelo.
- **Calidad con dos estados (bueno y descartado).** La librería no tiene un estado «dudoso» y no se inventan umbrales.
- **Modelos empaquetados con ficha generada, no escrita a mano.** `analisis/empaquetar_modelos.py` copia los `.joblib` sin tocarlos y toma las cifras de `resultados.json` y los nombres de clase de las constantes del código de entrenamiento. La carga comprueba el SHA-256.
- **Ejemplo JSON anonimizado.** Es una grabación de train cuyo nombre se sustituye por `ejemplo_OA.edf`, porque va al repo y los participantes son menores.
- **Python 3.10 y scikit-learn 1.7.2 fijados en `pyproject.toml`.** Son las versiones con que se guardaron los modelos; joblib no garantiza cargarlos con otras.

## Fase 1 — Esqueleto (2026-10-15)

- **`.venv` propio en EEG-Platform**, con Python 3.10 y `requirements.txt`. La web se instala y arranca desde su propia carpeta, que es lo más sencillo para el `iniciar.bat` de la Fase 8. EEG-Library entra en modo editable (`-e ../EEG-Library`).
- **Versiones científicas fijadas a las de la Fase 0** (numpy, pandas, scipy, mne, mne-icalabel, onnxruntime, pyarrow, joblib y scikit-learn). Son las que dieron paridad exacta con `matriz_rf.parquet`; otras podrían cambiar los resultados.
- **Carpeta de datos fuera del repo, comprobada al arrancar.** `EEG_PLATFORM_DATOS` (por defecto `../EEG-Platform-datos`) guarda la base SQLite y los archivos. Si apunta dentro del repo, Django no arranca, porque son datos de menores. El `.gitignore` añade una red de seguridad (`*.edf`, `*.sqlite3`, `*.csv`...).
- **`.env` leído con diez líneas propias**, sin `python-dotenv`: es una dependencia menos. El entorno tiene prioridad sobre el archivo.
- **Sin `admin` ni `auth`.** Login y usuarios están fuera de alcance; quitar las apps evita tablas y pantallas que nadie usaría.
- **Calidad y Análisis desactivadas en la navegación** mientras no se elige una grabación: son pantallas por grabación.
- **Django 5.2 (LTS)**, la última rama que admite Python 3.10.

## Fase 2 — Subida y lista de grabaciones (2026-10-16)

- **Los requisitos de un EDF son los de la librería, leídos de ella.** Frecuencia mínima `MIN_SFREQ` (128 Hz) y canales `CANALES_EPOC`. Un EDF de 128 Hz se acepta, la librería lo remuestrea a 256 Hz y la lista lo indica («128 Hz → 256 Hz (remuestreada)»). Copiar los números haría que la web y la librería pudieran discrepar.
- **Duración mínima de 14 s, derivada de la librería.** Es el recorte inicial más el final más una ventana de epocado, leídos de los argumentos por defecto de `recortar_registro` y `crear_epocas` (la librería no los expone como constantes). Comprobado: 14 s da 1 época y 13 s falla en el epocado. Se rechaza al subir para que no falle luego en el procesado.
- **La validación solo lee la cabecera del EDF** (`preload=False`): subir 20 archivos no carga 20 señales.
- **Un archivo inválido no se guarda en disco.** Queda en la lista con estado `error` y su mensaje, y no afecta al resto del lote. Los EDF son datos de menores: no se conserva lo que no se va a procesar.
- **Remuestreo y frecuencia original se guardan en la grabación al subir**, para que la lista los muestre antes de procesar. El JSON de la librería ya trae `metadatos.resampleado`.
- **Parámetros del lote como opciones cerradas tomadas de la librería** (`OPCIONES`, `PARAMETROS_ESTUDIO`); `Lote.parametros()` pasa por `normalizar_parametros`, así que la web no puede enviar a la librería una combinación que esta rechace.
- **Condición como metadato opcional con origen.** Se lee del nombre con un patrón configurable (`PATRON_CONDICION` o `EEG_PLATFORM_PATRON_CONDICION`), se edita a mano en la lista y se guarda si viene del nombre, de la edición o está vacía. El campo admite texto libre (con sugerencias), porque otros estudios tendrán otras condiciones.
- **Sin deep learning en la plataforma.** El epocado de 4 s es el común del pipeline, del que salen las 70 características de c1, c2 y c3; la ruta CNN de la librería no se usa.
- **`edfio` en `requirements.txt`** solo para que los tests escriban EDF sintéticos pequeños, sin datos de participantes en el repo. Los tests guardan los archivos en una carpeta temporal, nunca en `EEG-Platform-datos`.
- **`DATA_UPLOAD_MAX_NUMBER_FILES = 1000`**: el valor por defecto de Django (100) cortaría lotes grandes.

## Fase 3 — Procesado en segundo plano (2026-10-16)

- **Un procesador que reparte entre N procesos.** `manage.py procesar` es el único que toca la base de datos; los hijos (`ProcessPoolExecutor`) solo reciben una ruta y unos parámetros y devuelven el resultado (`analisis.py`, que no importa Django). Así no hay escrituras concurrentes ni conexiones de Django en procesos hijos.
- **N se calcula en cada equipo, no se fija.** La plataforma se ejecutará en el PC del autor, en el portátil de la defensa y en los de Ciencias del Deporte, así que `grabaciones/recursos.py` decide al arrancar el procesador: la mitad de los hilos, con tope en 4, y no más de un proceso por GB de memoria libre (mínimo 1). Se anula con `EEG_PLATFORM_PROCESOS` o `--procesos N`, y el comando dice qué eligió y por qué. Ejemplos: 12 hilos y 16 GB → 4; 4 hilos → 2; 2 hilos → 1; 12 hilos pero 1,2 GB libres → 1.
  - Tope en 4: medido con 12 EDF reales en un Ryzen 5 5600G (6 núcleos físicos), 1 proceso, 37 s; 2, 21 s; 4, 14,5 s; 6, 12,7 s. Con 4 se gana casi todo (2,5×); pasar a 6 solo añade un 15 %.
  - Memoria: un análisis llega a ~0,35–0,4 GB de pico (EDF de 380 s). Se reserva 1 GB por proceso para cubrir EDF de 71 canales y el propio procesador y la web.
  - La memoria libre se lee con la API de Windows (`ctypes`, sin `psutil`). Si no se puede leer, solo cuentan los hilos.
  - En un portátil con batería, o si se prefiere que no se caliente, conviene fijar 1 o 2: tarda más, pero es más suave.
- **Mismo resultado con N=1 y N>1.** Comprobado con 12 EDF reales (JSON idéntico salvo `fecha_analisis`) y con un test automático. Con N=1 también se usa un hijo, para que haya un único camino de código.
- **La cola es el campo `estado`.** Al subir, los EDF válidos pasan directamente a `en_cola`: no hay un paso intermedio que el investigador deba confirmar. `subida` queda en el modelo pero ya no se usa.
- **Continuar donde iba.** Al arrancar, lo que estaba `procesando` vuelve a la cola (es seguro porque solo hay un procesador). Con Ctrl+C también se devuelve lo que estaba a medias. Comprobado matando el procesador a la fuerza en mitad de un lote de 20 EDF reales: al relanzarlo terminaron las 20, sin repetir las ya hechas.
- **Señal de vida en la base de datos (`Procesador`, una fila).** Se actualiza cada 2 s, también cuando espera un archivo largo. Si hay cola y la señal tiene más de 15 s (o no existe), la lista avisa y da el comando. Con cola y procesador activo, indica cuántos procesos usa. Sin cola no avisa. Evita además lanzar dos procesadores a la vez.
- **Reintentar y reprocesar.** Una grabación fallida al procesar vuelve a la cola con un botón, y también todas las fallidas de un lote. Reprocesar una procesada conserva el resultado anterior hasta que termine el nuevo. Los archivos rechazados al subir no se pueden reintentar: no se guardaron.
- **Un error en un archivo solo marca ese archivo.** El mensaje incluye la fase de la librería donde falló. Si se muere un proceso hijo (p. ej. por memoria), las grabaciones afectadas quedan en `error` y se crea un grupo de procesos nuevo.
- **SQLite con WAL, `timeout` de 30 s y transacciones `IMMEDIATE`.** La web y el procesador escriben a la vez en la misma base; así no hay errores de «database is locked».
- **La lista se actualiza sola cada 3 s con un `fetch` a una vista parcial**, solo mientras haya cola. No pisa lo que se esté escribiendo en un campo de condición.
- **El procesador se lanza a mano en esta fase.** Queda documentado en `CLAUDE.md`; el `iniciar.bat` de la Fase 8 lo arrancará con la web.
- **Prueba con 20 EDF reales** (carpeta de datos temporal): 20 procesados con 4 procesos en 29 s, sin errores.

## Fase 4 — Pantalla de calidad (2026-10-16)

- **Avisos por pocos electrodos buenos: los mismos que la librería, sin excluir nada.** `aplicar_car` y `evaluar_calidad` avisan con menos de 8 electrodos buenos («se recomiendan al menos 8») y con menos de 6 («resultados no fiables», y la CAR se omite), pero la grabación se procesa igualmente. La web hace lo mismo: avisa en tres niveles (normal, aviso, crítico) en la pantalla de calidad y en la lista, y no impide nada. La librería no expone esos umbrales como constantes, así que están en `calidad.py` y un test comprueba que siguen coincidiendo con lo que hace y lo que dice `aplicar_car`.
- **La pantalla se construye solo con el JSON guardado.** `resumen_calidad` es una función pura sobre el JSON de `analizar_grabacion`; no consulta la librería ni recalcula nada. Se prueba con el fixture de la Fase 0 (copiado a `tests/fixtures/`) y con variantes derivadas de él.
- **El estado no depende solo del color.** Bueno = círculo azul relleno con ✔; descartado = rombo blanco de trazo discontinuo marrón con ✖. Cada electrodo lleva su nombre dentro, un `<title>` con el estado y el motivo, y la tabla repite el estado como texto. Los colores tienen buen contraste con el fondo.
- **Mapa SVG con posiciones fijas del Emotiv, generado en el servidor y sin JS.** Vista desde arriba, nariz arriba, izquierda/derecha rotuladas (impares a la izquierda). Coordenadas enteras en píxeles: con la localización en español, un decimal se escribiría con coma y rompería el SVG. Un test comprueba que los electrodos no se solapan y caben en la cabeza.
- **Mapa reutilizable** (`_mapa_cabeza.html`): recibe una lista de puntos con forma, símbolo, clase y título. La Fase 5 lo usará para la potencia por banda.
- **Motivos de descarte tal cual los da la librería,** con una línea de ayuda por tipo para quien no conoce el CQ ni el z robusto. No se muestran las métricas por canal: el motivo ya incluye el valor que decidió el descarte.
- **Lo que aplicó el procesado** se lee de `parametros_aplicados`: referencia, si se aplicó la CAR (y por qué no, si se omitió), componentes de ICA ajustadas y eliminadas, paso banda, notch y épocas. No se muestra la varianza eliminada por ICA, porque el contrato no fija su unidad.
- **`n_canales_buenos` copiado a la grabación al procesar,** y la lista carga las grabaciones sin el JSON de resultados. Así el aviso de la lista no obliga a leer ~20 KB por grabación cada 3 s mientras se actualiza sola. La migración rellena las ya procesadas.
- **Grabaciones sin procesar** (en cola, procesando o con error) abren la pantalla con una explicación en lugar de dar error; solo una grabación inexistente da 404. «Análisis» sigue desactivada hasta la Fase 5.

## Fase 5 — Pantalla de análisis y mapa de la cabeza (2026-10-16)

- **Mapa en SVG, no topomapas de MNE.** La librería no genera topomapas (matplotlib solo aparece en sus scripts de análisis y no está en las dependencias de la web). Se reutiliza el SVG de la Fase 4, que es lo más simple y no añade dependencias.
- **Un círculo por electrodo, sin interpolación.** Con 14 electrodos, una superficie suavizada inventaría valores entre ellos. Cada círculo lleva escrito su valor, además del color y del título al pasar el ratón, de modo que no depende de la vista del color ni del ratón. La pantalla lo dice.
- **Escala de color por banda**, del mínimo al máximo de esa banda en esa grabación. Con una escala común de 0 a 1, beta (~8 %) saldría casi plana. El coste es que el color no se compara entre bandas; la leyenda de cada banda da los valores numéricos de sus extremos y lo advierte. Paleta viridis (perceptualmente uniforme, legible con daltonismo); el texto de cada círculo es blanco o negro según el que más contraste da (≥ 4,5, comprobado en un test para toda la escala).
- **Selector de banda sin JavaScript.** El servidor dibuja un mapa por banda y el cambio se hace con radios y CSS (reglas generadas desde las bandas del JSON). Funciona aunque falle el JS y es accesible con teclado. Banda inicial: alfa.
- **«Toda la cabeza» es la media simple de la potencia relativa de los electrodos válidos.** La librería solo agrega por zona; es un cálculo trivial de presentación, y se rotula como «media de los electrodos válidos». Es el único dato que calcula la web.
- **Los electrodos descartados no se muestran con valor en ningún sitio** (ni mapa, ni barras, ni medias, ni tablas): su potencia se calculó con señal que no pasó por CAR ni ICA y no es comparable. Aparecen con el rombo de la Fase 4 y «descartado, sin dato». Una zona sin electrodos válidos sale como «—» y como hueco (no como cero) en la gráfica, y se avisa.
- **Chart.js 4.4.7 copiado a `static/vendor/`** (con su licencia MIT), descargado una vez de jsdelivr; en ejecución no hay CDN. Los datos entran con `json_script`, sin peticiones. La tabla zona × banda es la alternativa en texto de la gráfica.
- **Potencia absoluta como log10 de V²,** la misma unidad que la matriz del estudio y que `log10_absoluta_v2` de la librería (por electrodo, `log10` de `absoluta_v2`). Van en un bloque desplegable, junto con las tablas por electrodo × banda, que son las columnas que exportará la Fase 6.
- **Avisos:** los de pocos electrodos buenos (mismos umbrales que la Fase 4), el del paso banda 3–30 Hz (se detecta porque el filtro empieza por encima del inicio de delta) y el de zonas sin electrodos válidos.
- **Sin bloque de modelos ni descarga CSV todavía:** son las Fases 7 y 6.
- **Fixtures de test comunes** en `tests/auxiliar.py` (el fixture de la Fase 0 y variantes: descartados, CAR, ICA, paso banda), compartidos con los tests de calidad.
