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
