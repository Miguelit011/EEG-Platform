"""Cierre: instalación, arranque, documentación y que no haya datos de participantes en el repo."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from config.settings import leer_env

RAIZ = settings.BASE_DIR
DOCS = RAIZ / "docs"


def texto(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Instalar y arrancar
# ---------------------------------------------------------------------------

def test_los_scripts_existen_y_son_bat_de_windows():
    for nombre in ("instalar.bat", "iniciar.bat"):
        datos = (RAIZ / nombre).read_bytes()
        assert not datos.startswith(b"\xef\xbb\xbf"), f"{nombre} no debe llevar BOM"
        assert b"\r\n" in datos and b"\n" not in datos.replace(b"\r\n", b""), \
            f"{nombre} debe usar saltos de línea de Windows (CRLF)"
    assert "*.bat text eol=crlf" in texto(".gitattributes")


def test_instalar_hace_lo_que_dice_el_readme():
    bat = texto("instalar.bat")
    for paso in ("py -3.10", "-m venv .venv", "requirements.txt", ".env.example",
                 "manage.py migrate", "manage.py check", "manage.py comprobar_modelos",
                 r"..\EEG-Library\pyproject.toml"):
        assert paso in bat, paso
    assert "https://www.python.org/downloads/windows/" in bat      # dice dónde bajar Python 3.10
    # Avisa de las rutas largas antes de empezar, en vez de fallar a medias dentro de pip.
    assert "Get-Location).Path.Length -gt 120" in bat and "demasiado anidada" in bat


def test_iniciar_arranca_web_procesador_y_navegador():
    bat = texto("iniciar.bat")
    for parte in ("manage.py procesar", "manage.py runserver 127.0.0.1:8000",
                  "start \"\" \"http://127.0.0.1:8000/\"", "manage.py migrate",
                  "instalar.bat"):
        assert parte in bat, parte


SCRIPTS_POSIX = ("instalar.sh", "iniciar.sh", "instalar.command", "iniciar.command")


def test_los_scripts_de_linux_y_macos_usan_saltos_de_linea_lf():
    for nombre in SCRIPTS_POSIX:
        datos = (RAIZ / nombre).read_bytes()
        assert datos.startswith(b"#!"), f"{nombre} debe empezar por #!"
        assert not datos.startswith(b"\xef\xbb\xbf"), f"{nombre} no debe llevar BOM"
        assert b"\r" not in datos, f"{nombre} debe usar saltos de línea LF (con CRLF bash falla)"
    gitattributes = texto(".gitattributes")
    assert "*.sh text eol=lf" in gitattributes and "*.command text eol=lf" in gitattributes


def test_instalar_sh_hace_lo_mismo_que_instalar_bat():
    sh = texto("instalar.sh")
    for paso in ("python3.10", "-m venv .venv", "requirements.txt", ".env.example",
                 "manage.py migrate", "manage.py check", "manage.py comprobar_modelos",
                 "../EEG-Library/pyproject.toml", "static/models/cabeza.bin",
                 "static/models/cerebro.bin"):
        assert paso in sh, paso
    # Dice cómo conseguir Python 3.10 en cada sistema, y el paquete de venv aparte de Ubuntu.
    assert "https://www.python.org/downloads/release/python-31011/" in sh
    assert "ppa:deadsnakes/ppa" in sh and "python3.10-venv" in sh
    assert "ábrela" in sh


def test_iniciar_sh_arranca_web_procesador_y_navegador():
    sh = texto("iniciar.sh")
    for parte in ("manage.py procesar", "manage.py runserver 127.0.0.1:8000", "--noreload",
                  "http://127.0.0.1:8000/", "-m webbrowser", "manage.py migrate", "instalar.sh",
                  "sigue mostrando la versión anterior", "pkill -TERM -f",
                  "trap parar EXIT INT TERM HUP"):
        assert parte in sh, parte
    # Como `choice /c SN`: pregunta hasta tener S o N, y sin teclado no cierra nada (N).
    assert "while :; do" in sh and 'respuesta="N"' in sh and "[Ss]) break" in sh
    # macOS trae bash 3.2: sin `wait -n` ni otras novedades de bash 4.
    assert "wait -n" not in sh and "declare -A" not in sh and ",,}" not in sh


def test_los_command_de_macos_llaman_a_su_script():
    for nombre, script in (("instalar.command", "instalar.sh"), ("iniciar.command", "iniciar.sh")):
        assert f"bash ./{script}" in texto(nombre)


@pytest.mark.skipif(sys.platform == "win32",
                    reason="en Windows `bash` puede ser el de WSL y no ver estas rutas")
def test_los_scripts_de_linux_y_macos_tienen_sintaxis_valida():
    for nombre in SCRIPTS_POSIX:
        resultado = subprocess.run(["bash", "-n", str(RAIZ / nombre)], capture_output=True, text=True)
        assert resultado.returncode == 0, (nombre, resultado.stderr)


def test_los_comandos_de_los_documentos_existen():
    comandos = {p.stem for p in (RAIZ / "grabaciones" / "management" / "commands").glob("*.py")
                if p.stem != "__init__"}
    assert {"procesar", "comprobar_modelos", "documentar_csv"} <= comandos
    for doc in ("README.md", "docs/GUIA_DE_USO.md", "docs/AÑADIR_UN_MODELO.md", "CLAUDE.md"):
        for comando in re.findall(r"manage\.py (\w+)", texto(doc)):
            assert comando in comandos | {"runserver", "migrate", "check", "makemigrations"}, \
                (doc, comando)


def test_env_example_sin_rutas_personales_y_legible(tmp_path, monkeypatch):
    ejemplo = texto(".env.example")
    assert not re.search(r"[A-Za-z]:\\Users\\", ejemplo)
    # Una línea activa de la carpeta de datos fijaría una ruta que en otro equipo no existe.
    assert not re.search(r"^EEG_PLATFORM_DATOS=.+", ejemplo, re.M)
    for clave in ("EEG_PLATFORM_PROCESOS", "DJANGO_DEBUG", "DJANGO_SECRET_KEY"):
        monkeypatch.delenv(clave, raising=False)
    copia = tmp_path / ".env"
    copia.write_text(ejemplo, encoding="utf-8")
    import os
    leer_env(copia)
    assert os.environ["DJANGO_DEBUG"] == "1"
    for clave in ("EEG_PLATFORM_PROCESOS", "DJANGO_DEBUG", "DJANGO_SECRET_KEY"):
        monkeypatch.delenv(clave, raising=False)


# ---------------------------------------------------------------------------
# Documentación
# ---------------------------------------------------------------------------

DOCUMENTOS = ["README.md", "docs/GUIA_DE_USO.md", "docs/MATERIAL_MEMORIA.md",
              "docs/PRUEBA_LOTE_REAL.md", "docs/AÑADIR_UN_MODELO.md", "docs/COLUMNAS_CSV.md",
              "docs/PRUEBA_LINUX_MACOS.md"]


def test_los_documentos_existen_y_sus_enlaces_funcionan():
    for doc in DOCUMENTOS:
        ruta = RAIZ / doc
        assert ruta.is_file(), doc
        for destino in re.findall(r"\]\(([^)\s]+)\)", ruta.read_text(encoding="utf-8")):
            if destino.startswith(("http", "#", "..")):
                continue
            archivo = destino.split("#")[0]
            assert (ruta.parent / archivo).exists(), f"{doc} enlaza a {destino}, que no existe"


def test_el_readme_enlaza_toda_la_documentacion():
    readme = texto("README.md")
    for doc in DOCUMENTOS[1:]:
        assert doc in readme, doc
    assert "instalar.bat" in readme and "iniciar.bat" in readme
    for script in SCRIPTS_POSIX:
        assert script in readme, script
    assert "macOS 13" in readme and "Linux" in readme
    assert "EEG-Library" in readme and "Python 3.10" in readme


def test_las_capturas_de_la_guia_existen():
    guia = texto("docs/GUIA_DE_USO.md")
    imagenes = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", guia)
    assert len(imagenes) >= 8
    for imagen in imagenes:
        assert (DOCS / imagen).is_file(), imagen
    for pantalla in ("pantalla_1_grabaciones", "pantalla_2_calidad", "pantalla_3_analisis"):
        assert (DOCS / "capturas" / f"{pantalla}.png").is_file()
    for figura in ("arquitectura", "casos_de_uso"):
        assert (DOCS / "figuras" / f"{figura}.svg").is_file()
        assert (DOCS / "figuras" / f"{figura}.png").is_file()


def test_la_guia_dice_que_no_mide_fatiga():
    guia = texto("docs/GUIA_DE_USO.md")
    assert "No detecta ni mide fatiga" in guia and "no miden fatiga" in guia


# ---------------------------------------------------------------------------
# Privacidad: nada de participantes en el repositorio
# ---------------------------------------------------------------------------

def test_las_capturas_y_los_tests_usan_los_ejemplos_anonimos_de_la_libreria():
    script = texto("docs/generar_capturas.py")
    assert "EEG-Data" not in script and "EEG_DATA" not in script
    assert "tests.auxiliar" in script and "FIXTURE" in script
    # Los JSON de `tests/fixtures/` son copias de los ejemplos anónimos de EEG-Library: si la
    # librería está al lado (como pide el README), tienen que seguir siendo idénticos.
    ejemplos = RAIZ.parent / "EEG-Library" / "docs" / "ejemplos"
    for nombre in ("analisis_grabacion.json", "analisis_grabacion_pasat.json"):
        copia = RAIZ / "tests" / "fixtures" / nombre
        assert copia.is_file(), nombre
        if (ejemplos / nombre).is_file():
            assert copia.read_bytes() == (ejemplos / nombre).read_bytes(), \
                f"tests/fixtures/{nombre} ya no es igual al ejemplo de EEG-Library"


def test_ningun_codigo_de_participante_real_en_el_repositorio():
    """Los códigos de sujeto del estudio (centro C1–C8 + F y tres cifras) no van a git."""
    patron = re.compile(r"C[1-8][_-]?F\d{3}")
    revisados = 0
    for ruta in RAIZ.rglob("*"):
        partes = set(ruta.relative_to(RAIZ).parts)
        if (not ruta.is_file() or partes & {".venv", ".git", "__pycache__", ".pytest_cache", "vendor"}
                or ruta.suffix not in {".py", ".md", ".json", ".html", ".bat", ".sh", ".command",
                                       ".txt", ".svg", ".js", ".css"}):
            continue
        revisados += 1
        assert not patron.search(ruta.read_text(encoding="utf-8", errors="ignore")), ruta
    assert revisados > 40


def test_actualizar_la_plataforma_esta_cubierto():
    """Tras actualizar hay que cerrar la versión antigua, y los binarios no se tocan en git."""
    assert "sigue mostrando la versión anterior" in texto("iniciar.bat")
    assert "choice /c SN" in texto("iniciar.bat") and "Stop-Process" in texto("iniciar.bat")
    instalar = texto("instalar.bat")
    assert r"static\models\cabeza.bin" in instalar and ":faltan_mallas" in instalar
    assert "ábrela" in instalar
    for regla in ("*.bin binary", "*.woff2 binary", "*.png binary"):
        assert regla in texto(".gitattributes")
