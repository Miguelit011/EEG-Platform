from django.conf import settings
from django.core.management.base import BaseCommand

from grabaciones.exportacion import documentacion_markdown


class Command(BaseCommand):
    help = "Regenera docs/COLUMNAS_CSV.md a partir de las columnas que exporta la plataforma."

    def handle(self, *args, **opciones):
        ruta = settings.BASE_DIR / "docs" / "COLUMNAS_CSV.md"
        ruta.write_text(documentacion_markdown(), encoding="utf-8", newline="\n")
        self.stdout.write(f"Escrito {ruta}")