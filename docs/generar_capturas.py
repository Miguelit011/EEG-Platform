"""
Genera las capturas de pantalla de la guía de uso y de la memoria (`docs/capturas/`).

Usa **solo datos anónimos**: el JSON de ejemplo de la librería (`tests/fixtures/`) y variantes
suyas, con nombres de archivo inventados. Nunca lee EDF ni resultados reales, porque las
capturas se guardan en el repositorio y los participantes son menores de edad.

Cómo funciona: crea una carpeta de datos temporal, la rellena con grabaciones de demostración,
arranca la web, hace una captura de cada pantalla con Edge (o Chrome) sin ventana y recorta las
tarjetas que interesan. Hay que ejecutarlo desde la carpeta EEG-Platform:

    .venv\\Scripts\\python.exe docs\\generar_capturas.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "capturas"
PUERTO = 8790
ANCHO = 1100
FONDO = (246, 247, 249)   # --fondo de estilos.css
BLANCO = (255, 255, 255)


def buscar_navegador():
    candidatos = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    candidatos += sorted(Path(os.environ.get("ProgramFiles(x86)", "")).glob(
        "Microsoft/EdgeCore/*/msedge.exe"), reverse=True)
    for c in candidatos:
        if c.is_file():
            return c
    sys.exit("No encuentro Edge ni Chrome para hacer las capturas.")


# ---------------------------------------------------------------------------
# Datos de demostración (todo anónimo)
# ---------------------------------------------------------------------------

def preparar_datos(datos):
    os.environ["EEG_PLATFORM_DATOS"] = str(datos)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(RAIZ))
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", verbosity=0)

    from eeg_library.preprocesado.quality import CANALES_EPOC
    from grabaciones.models import Grabacion, Lote
    from tests.auxiliar import FIXTURE, variante

    lote = Lote.objects.create()
    E = Grabacion.Estado

    def crear(nombre, condicion, estado, resultado=None, **extra):
        origen = "nombre" if condicion else "vacia"
        g = Grabacion.objects.create(
            lote=lote, nombre_original=nombre, condicion=condicion, origen_condicion=origen,
            estado=estado, resultado=resultado, duracion_s=extra.pop("duracion_s", 140.0),
            sfreq_original_hz=extra.pop("sfreq", 256.0), remuestreada=extra.pop("remuestreada", False),
            n_canales_buenos=(resultado or {}).get("metadatos", {}).get("n_canales_buenos"),
            **extra)
        return g

    ids = {}
    ids["oa"] = crear("participante01_OA.edf", "OA", E.PROCESADA, FIXTURE, duracion_s=137.0,
                      archivo="demo/a.edf").pk
    crear("participante01_OC.edf", "OC", E.PROCESADA, variante(["O1"]), duracion_s=121.0,
          archivo="demo/b.edf")
    crear("participante02_STROOP.edf", "STROOP", E.PROCESADA, variante(["F7", "F3", "T7"]),
          duracion_s=62.0, archivo="demo/c.edf")
    ids["pocos"] = crear("participante02_PASAT.edf", "PASAT", E.PROCESADA,
                         variante(CANALES_EPOC[7:]), duracion_s=181.0, archivo="demo/d.edf").pk
    ids["sin"] = crear("registro_sin_condicion.edf", "", E.PROCESADA, variante(["P8"]),
                       duracion_s=95.0, sfreq=128.0, remuestreada=True, archivo="demo/e.edf").pk
    crear("participante03_MSIT.edf", "MSIT", E.EN_COLA, archivo="demo/f.edf")
    crear("participante03_PVTB.edf", "PVTB", E.PROCESANDO, archivo="demo/g.edf")
    crear("participante04_OA.edf", "OA", E.ERROR, archivo="demo/h.edf",
          mensaje_error="Fase «ica»: ValueError: Se requieren al menos 2 canales buenos "
                        "para ajustar ICA (recibidos: 1).")
    crear("participante04_OC.edf", "OC", E.ERROR, duracion_s=None, sfreq=None,
          mensaje_error="Frecuencia de muestreo insuficiente: 64 Hz (se requieren al menos 128 Hz).")
    return ids


def marcar_procesador(activo):
    from django.utils import timezone
    from grabaciones.models import Procesador
    Procesador.objects.all().delete()
    if activo:
        Procesador.objects.create(pid=1, procesos=4, ultimo_latido=timezone.now())


# ---------------------------------------------------------------------------
# Capturas
# ---------------------------------------------------------------------------

def capturar(navegador, url, destino, alto=4800):
    subprocess.run(
        [str(navegador), "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={ANCHO},{alto}", "--virtual-time-budget=4000",
         f"--screenshot={destino}", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120)


def recortar_pagina(ruta):
    """Quita el espacio vacío de debajo de la página."""
    from PIL import Image
    imagen = Image.open(ruta).convert("RGB")
    ancho, alto = imagen.size
    ultima = 0
    for y in range(alto - 1, -1, -1):
        if any(imagen.getpixel((x, y)) != FONDO for x in range(0, ancho, 7)):
            ultima = y
            break
    imagen.crop((0, 0, ancho, min(alto, ultima + 28))).save(ruta)
    return imagen.crop((0, 0, ancho, min(alto, ultima + 28)))


def tarjetas(imagen):
    """Rangos verticales (y0, y1) de las tarjetas blancas, leyendo una columna dentro de ellas."""
    x = 34   # dentro del relleno de la tarjeta, a la izquierda del contenido
    rangos, y0 = [], None
    for y in range(imagen.size[1]):
        blanco = imagen.getpixel((x, y)) == BLANCO
        if blanco and y0 is None:
            y0 = y
        elif not blanco and y0 is not None:
            if y - y0 > 40:
                rangos.append((y0 - 1, y))
            y0 = None
    if y0 is not None:
        rangos.append((y0 - 1, imagen.size[1] - 1))
    return rangos


def guardar_recorte(imagen, rangos, desde, hasta, nombre):
    y0, y1 = rangos[desde][0], rangos[hasta][1]
    imagen.crop((12, max(0, y0 - 6), imagen.size[0] - 12, min(imagen.size[1], y1 + 6))).save(
        SALIDA / nombre)


def main():
    navegador = buscar_navegador()
    SALIDA.mkdir(parents=True, exist_ok=True)
    datos = Path(tempfile.mkdtemp(prefix="eeg_capturas_"))
    servidor = None
    try:
        ids = preparar_datos(datos)
        marcar_procesador(activo=True)
        entorno = {**os.environ, "EEG_PLATFORM_DATOS": str(datos), "PYTHONPATH": str(RAIZ)}
        servidor = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", f"127.0.0.1:{PUERTO}", "--noreload"],
            cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{PUERTO}"
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/", timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            sys.exit("La web de demostración no arrancó.")

        tmp = datos / "tmp.png"

        def pagina(ruta_url, nombre):
            capturar(navegador, base + ruta_url, tmp)
            imagen = recortar_pagina(tmp)
            imagen.save(SALIDA / nombre)
            return imagen, tarjetas(imagen)

        # Pantalla 1: grabaciones
        imagen, t = pagina("/", "pantalla_1_grabaciones.png")
        guardar_recorte(imagen, t, 0, 0, "lista_subida.png")
        guardar_recorte(imagen, t, 1, 1, "lista_lotes.png")
        marcar_procesador(activo=False)
        imagen, t = pagina("/", "lista_sin_procesador.png")
        guardar_recorte(imagen, t, 1, 1, "lista_sin_procesador.png")
        marcar_procesador(activo=True)

        # Pantalla 2: calidad
        imagen, t = pagina(f"/grabaciones/{ids['oa']}/calidad/", "pantalla_2_calidad.png")
        imagen, t = pagina(f"/grabaciones/{ids['pocos']}/calidad/", "calidad_pocos_electrodos.png")
        guardar_recorte(imagen, t, 0, 0, "calidad_pocos_electrodos.png")

        # Pantalla 3: análisis y modelos
        imagen, t = pagina(f"/grabaciones/{ids['oa']}/analisis/", "pantalla_3_analisis.png")
        guardar_recorte(imagen, t, 0, 1, "analisis_grafica_y_tabla.png")
        guardar_recorte(imagen, t, 2, 2, "analisis_mapa.png")
        guardar_recorte(imagen, t, 3, 3, "analisis_modelos.png")
        imagen, t = pagina(f"/grabaciones/{ids['sin']}/analisis/", "analisis_sin_condicion.png")
        guardar_recorte(imagen, t, 3, 3, "analisis_modelos_condicion_estimada.png")
        os.remove(SALIDA / "analisis_sin_condicion.png")
    finally:
        if servidor:
            servidor.terminate()
            servidor.wait(timeout=20)
        shutil.rmtree(datos, ignore_errors=True)
    for ruta in sorted(SALIDA.glob("*.png")):
        print(f"{ruta.name:48} {ruta.stat().st_size // 1024:5} KB")


if __name__ == "__main__":
    main()
