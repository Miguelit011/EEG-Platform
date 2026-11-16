import pytest
from django.core.management import call_command

from grabaciones import recursos
from grabaciones.recursos import MEMORIA_POR_PROCESO, procesos_automaticos

GB = 1024**3


@pytest.mark.parametrize("hilos, libre_gb, esperado", [
    (12, 16, 4),     # sobremesa potente: tope de 4
    (8, 16, 4),      # portátil de 4 núcleos con hilos
    (4, 16, 2),      # portátil modesto
    (2, 16, 1),      # el mínimo
    (1, 16, 1),
    (12, 3.5, 3),    # poca memoria libre manda sobre los núcleos
    (12, 1.2, 1),
    (12, 0.2, 1),    # nunca menos de 1
])
def test_procesos_segun_el_equipo(hilos, libre_gb, esperado):
    n, _ = procesos_automaticos(hilos=hilos, libre=int(libre_gb * GB))
    assert n == esperado


def test_sin_poder_medir_la_memoria_solo_cuentan_los_hilos():
    n, texto = procesos_automaticos(hilos=8, libre=None)
    assert n == 4 and "GB" not in texto


def test_la_explicacion_dice_de_donde_sale():
    _, texto = procesos_automaticos(hilos=8, libre=6 * GB)
    assert "8 hilos" in texto and "6.0 GB libres" in texto


def test_en_este_equipo_da_un_valor_valido():
    n, _ = procesos_automaticos()
    assert 1 <= n <= recursos.MAXIMO_POR_DEFECTO
    libre = recursos.memoria_libre_bytes()
    assert libre is None or libre > 0


def test_el_comando_calcula_los_procesos_si_no_se_indican(monkeypatch, settings, capsys):
    llamadas = []
    monkeypatch.setattr("grabaciones.procesador.trabajar",
                        lambda procesos, **kw: llamadas.append(procesos) or
                        {"procesadas": 0, "con_error": 0})
    monkeypatch.setattr("grabaciones.management.commands.procesar.procesos_automaticos",
                        lambda: (3, "8 hilos, 6.0 GB libres"))
    settings.PROCESOS = None
    call_command("procesar", "--una-vez")
    assert llamadas == [3]
    assert "calculados para este equipo: 8 hilos, 6.0 GB libres" in capsys.readouterr().out


def test_el_entorno_y_el_argumento_anulan_el_calculo(monkeypatch, settings, capsys):
    llamadas = []
    monkeypatch.setattr("grabaciones.procesador.trabajar",
                        lambda procesos, **kw: llamadas.append(procesos) or
                        {"procesadas": 0, "con_error": 0})
    monkeypatch.setattr("grabaciones.management.commands.procesar.procesos_automaticos",
                        lambda: pytest.fail("no debe calcularse"))
    settings.PROCESOS = 2
    call_command("procesar", "--una-vez")
    call_command("procesar", "--una-vez", "--procesos", "1")
    assert llamadas == [2, 1]
    salida = capsys.readouterr().out
    assert "fijados con EEG_PLATFORM_PROCESOS" in salida and "indicados con --procesos" in salida


# ---------------------------------------------------------------------------
# Windows, Linux y macOS
# ---------------------------------------------------------------------------

MEMINFO = """MemTotal:       16303428 kB
MemFree:         1234567 kB
MemAvailable:    6291456 kB
Buffers:          123456 kB
"""


def test_memoria_libre_en_linux(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(MEMINFO, encoding="ascii")
    assert recursos._memoria_libre_linux(meminfo) == 6 * GB   # MemAvailable, no MemFree


@pytest.mark.parametrize("contenido", ["", "MemTotal: 16303428 kB\n", "MemAvailable: mucho kB\n"])
def test_memoria_libre_en_linux_ilegible(tmp_path, contenido):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(contenido, encoding="ascii")
    assert recursos._memoria_libre_linux(meminfo) is None
    assert recursos._memoria_libre_linux(tmp_path / "no_existe") is None


def test_memoria_libre_segun_el_sistema(monkeypatch):
    monkeypatch.setattr(recursos, "_memoria_libre_windows", lambda: 1)
    monkeypatch.setattr(recursos, "_memoria_libre_linux", lambda: 2)
    assert recursos.memoria_libre_bytes("win32") == 1
    assert recursos.memoria_libre_bytes("linux") == 2
    assert recursos.memoria_libre_bytes("darwin") is None   # en macOS solo cuentan los hilos


def test_el_lanzador_de_cada_sistema():
    assert recursos.lanzador("win32") == "iniciar.bat"
    assert recursos.lanzador("linux") == "iniciar.sh"
    assert recursos.lanzador("darwin") == "iniciar.command"
    for nombre in ("iniciar.bat", "iniciar.sh", "iniciar.command"):
        assert (recursos.Path(__file__).resolve().parents[1] / nombre).is_file(), nombre
