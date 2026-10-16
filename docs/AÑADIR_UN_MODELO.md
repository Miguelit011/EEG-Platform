# Añadir un modelo a la plataforma

Guía para quien entrena un modelo nuevo y quiere verlo en EEG-Platform. No hace falta
tocar el código de la web: basta con **dos archivos** y **una línea** de configuración.

## Qué hace la plataforma con un modelo

- Lo aplica a las grabaciones **ya procesadas**, usando las 70 características que se
  guardaron al procesarlas. **No hay que volver a procesar nada.**
- Lo muestra en la pantalla de análisis de cada grabación (con la clase predicha, la
  probabilidad de cada clase y su ficha) y lo añade al CSV.
- Solo lo aplica a las condiciones para las que dice servir. Con la condición del archivo
  conocida compara la predicción con ella; con la condición desconocida, lo muestra solo si
  la condición estimada por el modelo de reposo/tarea cae en su grupo.
- Solo predice si la grabación se procesó con **los mismos parámetros** con que se entrenó
  el modelo (referencia, paso banda y notch). Si no, dice «no disponible con estos
  parámetros» y no muestra ninguna predicción.

## Lo que necesitas antes

1. **El modelo guardado con `joblib`** (`.joblib`): un `Pipeline` de scikit-learn que incluya
   todo lo que necesita para predecir (imputación, escalado…) y se haya entrenado con un
   `DataFrame`, para que recuerde los nombres de sus columnas.
2. Entrenado con **scikit-learn 1.7.2 y Python 3.10**, que son las versiones de la plataforma.
   Con otras versiones el archivo puede no abrirse o dar resultados distintos.
3. Que use **las 70 características** de la plataforma, con sus nombres exactos
   (por ejemplo `frontal_delta_logabs_media`). Están en `docs/COLUMNAS_CSV.md` y en la
   ficha de cualquiera de los modelos del estudio. Puede usar solo algunas.
4. Un **test independiente** (personas que no se usaron para entrenar ni para elegir el
   modelo), con su intervalo de confianza y el nivel de azar. La plataforma muestra esas
   cifras junto a cada predicción; sin ellas, el modelo no debería enseñarse.

## Paso 1. Copia los dos archivos

Copia el `.joblib` y su ficha `.json` (el paso 2 explica cómo escribirla) a la carpeta de
modelos, que está junto a los datos de la plataforma:

```
EEG-Platform-datos\modelos\
    mi_modelo.joblib
    mi_modelo.json
```

(Si cambiaste la carpeta de datos con `EEG_PLATFORM_DATOS`, es la carpeta `modelos` de esa
ubicación. No va dentro de la carpeta del repositorio.)

## Paso 2. Escribe la ficha

La ficha es un archivo de texto `.json` con el mismo nombre que el modelo. Esta es la
estructura (la lista de `columnas` está abreviada: debe llevar **todas** las columnas del
modelo, en su orden):

```json
{
  "id": "mi_modelo",
  "titulo": "Tarea de memoria / tarea de atención",
  "archivo": "mi_modelo.joblib",
  "sha256_modelo": "PEGA_AQUI_EL_SHA256_DEL_JOBLIB",
  "que_predice": "Si una grabación es de una tarea de memoria o de una de atención.",
  "clases": [
    {"codigo": 0, "nombre": "memoria"},
    {"codigo": 1, "nombre": "atencion"}
  ],
  "condiciones_aplicables": ["PASAT", "PVSAT", "STROOP", "MSIT"],
  "condiciones_por_clase": {
    "memoria": ["PASAT", "PVSAT"],
    "atencion": ["STROOP", "MSIT"]
  },
  "parametros_validos": {"referencia": "car_condicional", "banda_hz": [1.0, 30.0], "notch_hz": 50.0},
  "columnas": ["frontal_delta_logabs_media", "frontal_delta_logabs_sd", "frontal_delta_rel_media"],
  "resultado_test": {
    "metrica": "exactitud_balanceada",
    "valor": 0.72,
    "ic95": [0.65, 0.79],
    "azar": 0.5,
    "n_grabaciones": 300,
    "n_personas": 28,
    "fuente": "Dónde está el análisis de donde salen estas cifras"
  },
  "entrenamiento": {"fecha": "2026-11-01", "variante": "regresión logística"},
  "avisos": ["Parte del acierto puede deberse a la duración de la grabación."]
}
```

Qué significa cada campo:

| Campo | Qué poner |
|---|---|
| `id` | Un nombre corto sin espacios ni tildes. Es el prefijo de sus columnas en el CSV |
| `titulo`, `que_predice` | Los textos que verá quien use la web |
| `archivo` | El nombre del `.joblib` (está en la misma carpeta) |
| `sha256_modelo` | La «huella» del `.joblib`; evita que la ficha describa otro archivo. Ver más abajo |
| `clases` | Una por clase, con el **código** que devuelve el modelo (0, 1…) y su nombre |
| `condiciones_aplicables` | Las condiciones de las grabaciones donde tiene sentido, escritas como en los nombres de archivo |
| `condiciones_por_clase` | Opcional. Qué condiciones corresponden a cada clase. Sirve para avisar si el modelo contradice la condición del archivo. Si falta, se supone que la clase se llama como la condición |
| `parametros_validos` | Los parámetros de procesado con que se entrenó: `referencia` (`car_condicional` u `original`), `banda_hz` (`[1, 30]` o `[3, 30]`) y `notch_hz` (`50` o `null`) |
| `columnas` | Las columnas del modelo, en su orden exacto |
| `resultado_test` | El resultado en el test independiente: `valor`, `ic95` (`[inferior, superior]`), `azar` (por ejemplo 0,5 con dos clases iguales), número de grabaciones y de personas, y de dónde salen |
| `entrenamiento`, `avisos` | Fecha y descripción del entrenamiento, y las limitaciones que quieras que se vean siempre |

### Cómo sacar el SHA-256 y las columnas

En PowerShell, desde la carpeta `EEG-Platform-datos\modelos`:

```powershell
Get-FileHash mi_modelo.joblib -Algorithm SHA256
```

Y para ver las columnas del modelo en el orden que necesita la ficha, desde la carpeta
`EEG-Platform`:

```powershell
.venv\Scripts\python.exe -c "import joblib, json; print(json.dumps(list(joblib.load(r'..\EEG-Platform-datos\modelos\mi_modelo.joblib').feature_names_in_)))"
```

## Paso 3. Añade una línea a la configuración

Abre `EEG-Platform\config\settings.py`, busca la lista `MODELOS` y añade el nombre de la
ficha, con la extensión `.json`:

```python
MODELOS = [
    "c1_oa_oc_logistica",
    "c2_reposo_tarea_logistica",
    "c3_tareas_logistica",
    "mi_modelo.json",
]
```

Los nombres sin `.json` son los modelos del estudio, que viajan con EEG-Library. Los que
acaban en `.json` se buscan en `EEG-Platform-datos\modelos`.

## Paso 4. Comprueba que está bien

Desde la carpeta `EEG-Platform`:

```powershell
.venv\Scripts\python.exe manage.py comprobar_modelos
```

Para cada modelo dice ✔ o ✖ y, si falla, por qué: que falte un archivo, que el SHA-256 no
coincida (y cuál es el correcto), que use características que la plataforma no calcula o que
no pueda predecir. Corrige lo que indique hasta que todos salgan ✔.

## Paso 5. Reinicia la web

Cierra y vuelve a abrir la web (el procesador no hace falta reiniciarlo). Abre el análisis de
una grabación: el modelo aparece en el bloque «Modelos» y sus columnas, al final del CSV
(`mi_modelo_clase`, `mi_modelo_p_<clase>` y `mi_modelo_condicion_estimada`; ver
`docs/COLUMNAS_CSV.md`, que se actualiza con `manage.py documentar_csv`).

## Problemas frecuentes

| Qué ves | Qué pasa |
|---|---|
| «No se pudo cargar el modelo… SHA-256» | Cambiaste el `.joblib` después de escribir la ficha. Vuelve a calcular el SHA-256 y pégalo |
| «No se encuentra la ficha» | El nombre de `settings.py` no coincide con el del archivo, o no está en `EEG-Platform-datos\modelos` |
| «No se pudo aplicar el modelo… Faltan características» | El modelo usa columnas que no están entre las 70 guardadas. Habría que añadirlas a la librería y reprocesar |
| «No disponible con estos parámetros de procesado» | La grabación se procesó con otra referencia, paso banda o notch que los de `parametros_validos`. Es lo correcto: no se predice con un procesado distinto |
| El modelo no aparece en una grabación | Su condición no está en `condiciones_aplicables` del modelo, o no se conoce y el modelo no pertenece al grupo estimado |

## Una advertencia importante

Estos modelos clasifican la **condición** de una grabación; no miden ningún estado del
participante. Un modelo nuevo debe presentarse con la misma honestidad: resultado en un test
independiente con su intervalo, nivel de azar y limitaciones. La plataforma lo muestra tal cual
lo escribas en la ficha.
