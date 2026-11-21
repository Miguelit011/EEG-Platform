# EEG-Platform

Aplicación web, de uso **local** en Windows, Linux o macOS, para que investigadores de Ciencias del Deporte
procesen grabaciones EEG del casco **Emotiv EPOC X** (EDF, 14 canales) sin programar. Usa la
librería [EEG-Library](https://github.com/Miguelit011/EEG-Library) para todo el cálculo; la web sube, guarda y muestra.

Forma parte del Trabajo Fin de Grado de Miguel Ángel (Grado en Ingeniería Informática,
Ingeniería del Software, UEx).

![Pantalla de análisis espectral de una grabación](docs/capturas/pantalla_3_analisis.png)

Qué hace:

1. Subir uno o muchos EDF a la vez, con los parámetros de procesado (referencia, paso banda y notch).
2. Lista de grabaciones con su estado y el progreso del lote.
3. Calidad de la señal por grabación: mapa de electrodos sobre el cerebro y motivo de cada descarte.
4. Análisis espectral por grabación: potencia por banda y por zona, con una cabeza y un cerebro en 3D y cuatro mapas por banda (el color entre sensores es una interpolación orientativa, no localiza fuentes).
5. Una pestaña **Modelos** con lo que predicen los modelos de IA enchufables (hoy, c1, c2 y c3 del estudio) para cada grabación, junto a su resultado en el test independiente, con el intervalo y el nivel de azar, y un resumen de todas las grabaciones.
6. Una pestaña **Tiempo en tarea**, solo para PASAT y PVTB: cómo cambia el EEG a lo largo de la tarea según la regresión logística y la red EEGNet, con su veredicto en test y cuatro mapas del cerebro animados.
7. Descargar los resultados en CSV (una grabación o el lote completo).

Calidad, Análisis, Modelos y Tiempo en tarea son cuatro vistas de una misma grabación: la barra de navegación recuerda la última que abriste y un selector con flechas permite cambiar de grabación sin salir de la pestaña.

> **No detecta ni mide fatiga.** Los modelos clasifican la condición de la grabación (por
> ejemplo, reposo o tarea) y los resultados del TFG muestran que el EEG no predice la fatiga
> percibida. La pestaña Tiempo en tarea mide cómo cambia el EEG con el tiempo en la tarea, no
> el nivel de fatiga de la persona. Los resultados de los modelos se acompañan siempre de su
> acierto en un test independiente y de sus limitaciones.

## Antes de empezar

- **Un sistema compatible:**
  - **Windows 10 u 11**.
  - **Linux** con glibc 2.28 o posterior (Ubuntu 20.04, Debian 10, Fedora 29 o posteriores), en x86_64 o ARM.
  - **macOS 13 Ventura o posterior**, en Intel o Apple Silicon.

  Qué se ha probado en cada uno: [`docs/PRUEBA_LINUX_MACOS.md`](docs/PRUEBA_LINUX_MACOS.md).
- Conexión a internet **solo para instalar**; después funciona sin internet.
- **Python 3.10** (puede convivir con otras versiones). Es la versión con la que se entrenaron los
  modelos; ya no recibe actualizaciones, pero no se puede cambiar sin volver a validarlos.
  - Windows: <https://www.python.org/downloads/windows/> (instalador de 64 bits de la 3.10.x).
  - macOS: el instalador de la 3.10.11 de <https://www.python.org/downloads/release/python-31011/>
    («macOS 64-bit universal2 installer»).
  - Linux: el paquete de tu distribución. En Ubuntu 22.04, `sudo apt install python3.10 python3.10-venv`;
    en Ubuntu 24.04 o posterior, antes `sudo add-apt-repository ppa:deadsnakes/ppa`; en Fedora,
    `sudo dnf install python3.10`.
- **En Windows, una ruta corta.** Windows limita las rutas a 260 caracteres y alguna dependencia tiene archivos
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

| Sistema | Cómo |
|---|---|
| Windows | Doble clic en **`instalar.bat`** |
| macOS | Doble clic en **`instalar.command`** |
| Linux | En una terminal, desde la carpeta `EEG-Platform`: **`bash instalar.sh`** |

Busca Python 3.10, crea el entorno, instala las dependencias (la primera vez tarda unos
minutos), crea la configuración y la base de datos y comprueba que los modelos cargan. Si algo
falla, te dice qué es.

<details>
<summary>Lo mismo, a mano (desde la carpeta <code>EEG-Platform</code>)</summary>

En PowerShell (Windows):

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe manage.py migrate
```

En una terminal de Linux o macOS:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
```
</details>

## Usar

| Sistema | Cómo | Qué se abre |
|---|---|---|
| Windows | Doble clic en **`iniciar.bat`** | Dos ventanas negras (la web y el procesador) y el navegador |
| macOS | Doble clic en **`iniciar.command`** | Una ventana de Terminal con la web y el procesador, y el navegador |
| Linux | **`bash iniciar.sh`** en una terminal | La web y el procesador en esa terminal, y el navegador |

La plataforma está en <http://127.0.0.1:8000/>. **Deja abiertas esas ventanas mientras trabajes;
para terminar, ciérralas** (en Linux y macOS también vale Ctrl+C). Si la lista avisa de que el
procesador no está en marcha, es que su ventana se cerró: vuelve a abrir el lanzador.

La guía paso a paso, con capturas, está en [`docs/GUIA_DE_USO.md`](docs/GUIA_DE_USO.md).

Si ya hay algo funcionando en el puerto 8000 (por ejemplo, la versión anterior sin cerrar),
el lanzador te pregunta si quieres **reiniciarla con la versión actual** (pulsa `S`) o solo abrir
el navegador (`N`). Reiniciar es seguro: lo que estaba en cola continúa donde iba.

**macOS, la primera vez:** si la carpeta se descargó como ZIP desde el navegador (y no con
`git clone`), macOS puede bloquear los `.command` por venir de internet. Ábrelos con clic derecho →
**Abrir**; si no aparece esa opción, en **Ajustes del Sistema → Privacidad y seguridad**, pulsa
**Abrir igualmente**. Si dice que no tienes permiso para abrirlo, ejecuta una vez en Terminal,
dentro de la carpeta `EEG-Platform`: `chmod +x *.command *.sh`.

## Actualizar a una versión nueva

1. **Cierra** las ventanas de la versión anterior (en Windows, «EEG-Platform - web» y
   «EEG-Platform - procesador»), o pulsa `S` cuando el lanzador te pregunte por ellas. Si no,
   sigues viendo la versión vieja.
2. Actualiza las carpetas (`EEG-Platform` y, si cambió, `EEG-Library`) con la versión nueva.
   Tus datos viven aparte, en `EEG-Platform-datos`, y no se tocan.
3. Vuelve a **instalar** (`instalar.bat`, `instalar.command` o `bash instalar.sh`). Es seguro
   repetirlo: reutiliza el entorno y la configuración, instala lo que falte y aplica las
   migraciones de la base de datos.
4. **Arranca** la plataforma como siempre.

La web no guarda en el navegador copias antiguas del CSS ni del JS, así que no hace falta limpiar
la caché ni pulsar Ctrl+F5.

## Dónde se guardan los datos

Los EDF y los resultados son de **participantes menores de edad**. Se guardan **fuera del
repositorio**, en la carpeta `EEG-Platform-datos` (o la que indiques en `EEG_PLATFORM_DATOS`
dentro de `.env`). La plataforma no arranca si se configura una carpeta dentro del repositorio.
Nunca se suben a git ni a servicios externos, y la web no usa recursos de internet.

## Para quien desarrolla

En Windows (PowerShell). En Linux y macOS, lo mismo con `.venv/bin/python` y `/` en las rutas.

```powershell
.venv\Scripts\python.exe -m pytest                       # tests
.venv\Scripts\python.exe manage.py runserver             # solo la web
.venv\Scripts\python.exe manage.py procesar              # solo el procesador
.venv\Scripts\python.exe manage.py comprobar_modelos     # valida los modelos registrados
.venv\Scripts\python.exe manage.py documentar_csv        # regenera docs/COLUMNAS_CSV.md
.venv\Scripts\python.exe docs\generar_capturas.py        # regenera las capturas de docs/capturas (datos anónimos)
.venv\Scripts\python.exe docs\comparar_sistemas.py generar <json>   # resultado de un EDF sintético, para comparar sistemas
.venv\Scripts\python.exe docs\comparar_sistemas.py comparar <a> <b> # compara dos JSON de sistemas distintos, número a número
.venv\Scripts\python.exe docs\generar_mallas.py --pial-izq <pial_left.gii.gz> --pial-der <pial_right.gii.gz>   # regenera static/models (ver su docstring)
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
| [`docs/PRUEBA_LINUX_MACOS.md`](docs/PRUEBA_LINUX_MACOS.md) | Prueba en Linux y macOS: lista de comprobación y resultados |
| [`docs/diseno/`](docs/diseno/) | Críticas de diseño de la interfaz (registro de la Fase 9, generadas con una herramienta de revisión) |
| [`PLAN.md`](PLAN.md) | Plan de desarrollo por fases |

## Licencia

MIT. Ver [`LICENSE`](LICENSE). Los recursos de terceros de `static/` (Chart.js, Three.js, fuentes IBM Plex y mallas de cabeza y cerebro) conservan su propia licencia, que acompaña a cada uno.
