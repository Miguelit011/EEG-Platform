# EEG-Platform

Aplicación web, de uso **local** en Windows, para que investigadores de Ciencias del Deporte
procesen grabaciones EEG del casco **Emotiv EPOC X** (EDF, 14 canales) sin programar. Usa la
librería [EEG-Library](../EEG-Library) para todo el cálculo; la web sube, guarda y muestra.

Forma parte del Trabajo Fin de Grado de Miguel Ángel (Grado en Ingeniería Informática,
Ingeniería del Software, UEx).

Qué hace:

1. Subir uno o muchos EDF a la vez, con los parámetros de procesado (referencia, paso banda y notch).
2. Lista de grabaciones con su estado y el progreso del lote.
3. Calidad de la señal por grabación: mapa de electrodos y motivo de cada descarte.
4. Análisis espectral por grabación: potencia por banda, por zona y mapa de la cabeza.
5. Resultados de modelos de IA enchufables (hoy, c1, c2 y c3 del estudio).
6. Descargar los resultados en CSV (una grabación o el lote completo).

> **No detecta ni mide fatiga.** Los modelos clasifican la condición de la grabación (por
> ejemplo, reposo o tarea) y los resultados del TFG muestran que el EEG no predice la fatiga
> percibida. Los resultados de los modelos se acompañan siempre de su acierto en un test
> independiente y de sus limitaciones.

## Antes de empezar

- **Windows 10 u 11** y conexión a internet **solo para instalar**; después funciona sin internet.
- **Python 3.10** (puede convivir con otras versiones). Descárgalo de
  <https://www.python.org/downloads/windows/> (instalador de 64 bits de la 3.10.x).
- **Una ruta corta.** Windows limita las rutas a 260 caracteres y alguna dependencia tiene archivos
  con rutas muy profundas: instala en algo como `C:\TFG` y no dentro de OneDrive ni de carpetas
  con nombres largos. `instalar.bat` lo comprueba al empezar.
- **Las dos carpetas juntas.** La plataforma instala EEG-Library desde la carpeta de al lado,
  así que los dos repositorios deben estar clonados en la misma carpeta:

  ```
  TFG\
  ├── EEG-Library\         librería de procesado
  ├── EEG-Platform\        esta aplicación
  └── EEG-Platform-datos\  se crea sola: base de datos, EDF subidos y resultados
  ```

## Instalar (una vez)

Haz doble clic en **`instalar.bat`**. Busca Python 3.10, crea el entorno, instala las
dependencias (la primera vez tarda unos minutos), crea la configuración y la base de datos y
comprueba que los modelos cargan. Si algo falla, te dice qué es.

<details>
<summary>Lo mismo, a mano, en PowerShell (desde la carpeta <code>EEG-Platform</code>)</summary>

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe manage.py migrate
```
</details>

## Usar

Haz doble clic en **`iniciar.bat`**. Se abren dos ventanas negras (la web y el procesador) y el
navegador en <http://127.0.0.1:8000/>. **Déjalas abiertas mientras trabajes; para terminar,
ciérralas.** Si la lista avisa de que el procesador no está en marcha, es que esa ventana se
cerró: vuelve a abrir `iniciar.bat`.

La guía paso a paso, con capturas, está en [`docs/GUIA_DE_USO.md`](docs/GUIA_DE_USO.md).

## Dónde se guardan los datos

Los EDF y los resultados son de **participantes menores de edad**. Se guardan **fuera del
repositorio**, en la carpeta `EEG-Platform-datos` (o la que indiques en `EEG_PLATFORM_DATOS`
dentro de `.env`). La plataforma no arranca si se configura una carpeta dentro del repositorio.
Nunca se suben a git ni a servicios externos, y la web no usa recursos de internet.

## Para quien desarrolla

```powershell
.venv\Scripts\python.exe -m pytest                       # tests
.venv\Scripts\python.exe manage.py runserver             # solo la web
.venv\Scripts\python.exe manage.py procesar              # solo el procesador
.venv\Scripts\python.exe manage.py comprobar_modelos     # valida los modelos registrados
.venv\Scripts\python.exe manage.py documentar_csv        # regenera docs/COLUMNAS_CSV.md
.venv\Scripts\python.exe docs\generar_capturas.py        # regenera las capturas de docs/capturas (datos anónimos)
```

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/GUIA_DE_USO.md`](docs/GUIA_DE_USO.md) | Cómo usar la plataforma, con capturas |
| [`docs/COLUMNAS_CSV.md`](docs/COLUMNAS_CSV.md) | Qué significa cada columna del CSV |
| [`docs/AÑADIR_UN_MODELO.md`](docs/AÑADIR_UN_MODELO.md) | Cómo añadir un modelo nuevo |
| [`docs/DECISIONES.md`](docs/DECISIONES.md) | Decisiones de diseño y su porqué |
| [`docs/MATERIAL_MEMORIA.md`](docs/MATERIAL_MEMORIA.md) | Arquitectura, casos de uso, tests y capturas para la memoria |
| [`docs/PRUEBA_LOTE_REAL.md`](docs/PRUEBA_LOTE_REAL.md) | Prueba completa con un lote de EDF reales |
| [`PLAN.md`](PLAN.md) | Plan de desarrollo por fases |
