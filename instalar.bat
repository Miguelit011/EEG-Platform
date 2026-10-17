@echo off
rem Instala EEG-Platform: entorno de Python, dependencias, configuración y base de datos.
rem Se ejecuta una sola vez (y de nuevo si se actualiza la plataforma). Necesita internet.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title EEG-Platform - instalación

echo.
echo ============================================================
echo   Instalación de EEG-Platform
echo ============================================================
echo.

rem --- 1. La librería EEG-Library debe estar al lado -----------------------------
if not exist "..\EEG-Library\pyproject.toml" (
    echo [ERROR] No encuentro la carpeta EEG-Library al lado de EEG-Platform.
    echo.
    echo   Las dos carpetas tienen que estar juntas, por ejemplo:
    echo       TFG\EEG-Library
    echo       TFG\EEG-Platform
    echo.
    goto :fallo
)

rem --- 1b. La ruta no puede ser demasiado larga ------------------------------------
rem Windows limita las rutas a 260 caracteres y alguna dependencia ^(onnxruntime^) tiene
rem archivos con rutas muy profundas: en una carpeta muy anidada la instalación falla.
powershell -NoProfile -Command "if ((Get-Location).Path.Length -gt 120) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Esta carpeta está demasiado anidada:
    echo         %CD%
    echo.
    echo   Windows limita las rutas a 260 caracteres y la instalación fallaría a medias.
    echo   Mueve la carpeta TFG ^(con EEG-Library y EEG-Platform dentro^) a una ruta corta,
    echo   por ejemplo C:\TFG, y vuelve a ejecutar instalar.bat. Evita OneDrive y las
    echo   carpetas con nombres largos.
    echo.
    goto :fallo
)

rem --- 2. Python 3.10 ------------------------------------------------------------
set "PY="
py -3.10 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.10"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PY if exist "%ProgramFiles%\Python310\python.exe" set "PY=%ProgramFiles%\Python310\python.exe"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [ERROR] No encuentro Python 3.10, que es la versión que necesita la plataforma.
    echo.
    echo   1. Descarga Python 3.10 desde https://www.python.org/downloads/windows/
    echo      ^(el instalador de 64 bits de la versión 3.10.x, no la tienda de Windows^).
    echo   2. Instálalo y vuelve a ejecutar instalar.bat.
    echo.
    echo   Si tienes otras versiones de Python no pasa nada: pueden convivir.
    echo.
    goto :fallo
)
echo [1/5] Python 3.10 encontrado.

rem --- 3. Entorno virtual --------------------------------------------------------
if exist ".venv\Scripts\python.exe" (
    echo [2/5] El entorno de Python ya existe.
) else (
    echo [2/5] Creando el entorno de Python...
    %PY% -m venv .venv
    if errorlevel 1 goto :fallo
)

rem --- 4. Dependencias -----------------------------------------------------------
echo [3/5] Instalando las dependencias ^(la primera vez tarda unos minutos^)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fallo

rem --- 5. Configuración y base de datos ------------------------------------------
if exist ".env" (
    echo [4/5] El archivo de configuración .env ya existe; no se toca.
) else (
    copy ".env.example" ".env" >nul
    echo [4/5] Creado el archivo de configuración .env.
)
echo [5/5] Preparando la base de datos...
".venv\Scripts\python.exe" manage.py migrate --noinput >nul
if errorlevel 1 goto :fallo

echo.
echo Comprobando la instalación...
if not exist "static\models\cabeza.bin" goto :faltan_mallas
if not exist "static\models\cerebro.bin" goto :faltan_mallas
".venv\Scripts\python.exe" manage.py check
if errorlevel 1 goto :fallo
".venv\Scripts\python.exe" manage.py comprobar_modelos
if errorlevel 1 goto :fallo

echo.
echo ============================================================
echo   Instalación terminada. Para usar la plataforma, abre
echo   iniciar.bat.
echo.
echo   Si ya tenías la plataforma abierta, ciérrala ^(las ventanas
echo   "EEG-Platform - web" y "EEG-Platform - procesador"^) y ábrela
echo   otra vez para usar la versión nueva.
echo ============================================================
echo.
pause
exit /b 0

:faltan_mallas
echo.
echo [ERROR] Faltan los archivos de la cabeza y el cerebro 3D ^(carpeta static\models^).
echo         Vuelve a descargar o clonar EEG-Platform completa: no se han copiado todos
echo         los archivos.
goto :fallo

:fallo
echo.
echo ============================================================
echo   La instalación no se ha podido completar.
echo   Lee el mensaje de error de más arriba. Si no lo entiendes,
echo   guarda esta ventana y consúltalo.
echo ============================================================
echo.
pause
exit /b 1
