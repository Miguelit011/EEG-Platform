import pytest

from eeg_library.preprocesado.quality import CANALES_EPOC
from eeg_library.preprocesado.reader import MIN_SFREQ, TARGET_SFREQ

from grabaciones.validacion import DURACION_MINIMA_S, ErrorDeValidacion, validar_edf
from tests.edf_sinteticos import escribir_edf


def test_edf_valido_a_256_hz(tmp_path):
    info = validar_edf(escribir_edf(tmp_path / "ok.edf", duracion_s=30))
    assert info.duracion_s == pytest.approx(30, abs=1)
    assert info.sfreq_original_hz == TARGET_SFREQ
    assert info.remuestreada is False


def test_128_hz_se_acepta_y_se_marca_como_remuestreada(tmp_path):
    # Misma regla que la librería: MIN_SFREQ se lee de ella, no se copia.
    info = validar_edf(escribir_edf(tmp_path / "128.edf", sfreq=MIN_SFREQ))
    assert info.sfreq_original_hz == MIN_SFREQ
    assert info.remuestreada is True


def test_por_debajo_del_minimo_se_rechaza(tmp_path):
    with pytest.raises(ErrorDeValidacion, match="Frecuencia de muestreo insuficiente"):
        validar_edf(escribir_edf(tmp_path / "64.edf", sfreq=64))


def test_faltan_canales(tmp_path):
    ruta = escribir_edf(tmp_path / "pocos.edf", canales=CANALES_EPOC[:12])
    with pytest.raises(ErrorDeValidacion, match="Faltan 2 de los 14 canales") as error:
        validar_edf(ruta)
    assert CANALES_EPOC[12] in str(error.value) and CANALES_EPOC[13] in str(error.value)


def test_duracion_minima_derivada_de_la_libreria():
    # 5 s + 5 s de recorte y una ventana de 4 s: 14 s para tener una época.
    assert DURACION_MINIMA_S == 14


def test_grabacion_demasiado_corta(tmp_path):
    with pytest.raises(ErrorDeValidacion, match="demasiado corta.*mínimo 14 s"):
        validar_edf(escribir_edf(tmp_path / "corta.edf", duracion_s=DURACION_MINIMA_S - 1))


def test_justo_la_duracion_minima_se_acepta(tmp_path):
    validar_edf(escribir_edf(tmp_path / "minima.edf", duracion_s=DURACION_MINIMA_S))


def test_archivo_corrupto(tmp_path):
    ruta = tmp_path / "roto.edf"
    ruta.write_bytes(b"esto no es un edf")
    with pytest.raises(ErrorDeValidacion, match="No se puede leer"):
        validar_edf(ruta)


def test_archivo_vacio(tmp_path):
    ruta = tmp_path / "vacio.edf"
    ruta.write_bytes(b"")
    with pytest.raises(ErrorDeValidacion):
        validar_edf(ruta)
