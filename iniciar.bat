@echo off
rem Arranca EEG-Platform: la web, el procesador en segundo plano y el navegador.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title EEG-Platform

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] La plataforma todavía no está instalada.
    echo         Abre primero instalar.bat.
    echo.
    pause
    exit /b 1
)

rem --- La base de datos al día ^(rápido si no hay nada que hacer^) -----------------
".venv\Scripts\python.exe" manage.py migrate --noinput >nul
if errorlevel 1 (
    echo.
    echo [ERROR] No se ha podido preparar la base de datos. Ejecuta instalar.bat de nuevo.
    echo.
    pause
    exit /b 1
)

rem --- ¿Ya está en marcha? --------------------------------------------------------
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
    echo.
    echo Ya hay algo funcionando en el puerto 8000. Si es EEG-Platform, no hace falta
    echo arrancarla otra vez: abro el navegador.
    echo.
    start "" "http://127.0.0.1:8000/"
    timeout /t 5 >nul
    exit /b 0
)

echo.
echo Arrancando EEG-Platform...
echo Se abrirán dos ventanas: la web y el procesador. Déjalas abiertas mientras trabajes;
echo para terminar, ciérralas.
echo.

start "EEG-Platform - procesador" /D "%CD%" cmd /k .venv\Scripts\python.exe manage.py procesar
start "EEG-Platform - web" /D "%CD%" cmd /k .venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

rem --- Esperar a que la web responda ^(hasta 60 s^) y abrir el navegador ----------------
powershell -NoProfile -Command "for ($i = 0; $i -lt 60; $i++) { try { Invoke-WebRequest 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep 1 } }; exit 1"
if errorlevel 1 (
    echo [ERROR] La web no ha arrancado. Mira el mensaje de la ventana "EEG-Platform - web".
    echo.
    pause
    exit /b 1
)
start "" "http://127.0.0.1:8000/"
echo Listo: la plataforma está en http://127.0.0.1:8000/
timeout /t 4 >nul
exit /b 0
