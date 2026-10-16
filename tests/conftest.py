import pytest


@pytest.fixture
def base_de_datos(db):
    """La pantalla Grabaciones consulta la base de datos."""


@pytest.fixture
def archivos_en_carpeta_temporal(settings, tmp_path):
    """Los EDF de los tests nunca se escriben en la carpeta de datos real."""
    settings.MEDIA_ROOT = tmp_path / "archivos"


# Para los módulos que usan la web: `pytestmark = USA_LA_WEB`.
USA_LA_WEB = pytest.mark.usefixtures("base_de_datos", "archivos_en_carpeta_temporal")
