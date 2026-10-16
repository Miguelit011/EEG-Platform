"""Cierre: instalación, arranque, documentación y que no haya datos de participantes en el repo."""

import re
from pathlib import Path

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
              "docs/PRUEBA_LOTE_REAL.md", "docs/AÑADIR_UN_MODELO.md", "docs/COLUMNAS_CSV.md"]


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

def test_las_capturas_se_generan_solo_con_datos_anonimos():
    script = texto("docs/generar_capturas.py")
    assert "EEG-Data" not in script and "EEG_DATA" not in script
    assert "tests.auxiliar" in script and "FIXTURE" in script


def test_ningun_codigo_de_participante_real_en_el_repositorio():
    """Los códigos de sujeto del estudio (centro C1–C8 + F y tres cifras) no van a git."""
    patron = re.compile(r"C[1-8][_-]?F\d{3}")
    revisados = 0
    for ruta in RAIZ.rglob("*"):
        partes = set(ruta.relative_to(RAIZ).parts)
        if (not ruta.is_file() or partes & {".venv", ".git", "__pycache__", ".pytest_cache", "vendor"}
                or ruta.suffix not in {".py", ".md", ".json", ".html", ".bat", ".txt", ".svg", ".js", ".css"}):
            continue
        revisados += 1
        assert not patron.search(ruta.read_text(encoding="utf-8", errors="ignore")), ruta
    assert revisados > 40
