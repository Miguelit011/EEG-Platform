"""
`manage.py runserver` sin caché para los archivos estáticos (CSS, JS, fuentes y mallas 3D).

La plataforma es local y de una sola persona: lo que importa es que, al actualizarla, el
navegador no mezcle una página nueva con un CSS o un JS antiguos que guardó la vez anterior.
Con `Cache-Control: no-cache` el navegador pregunta cada vez si el archivo cambió (en local es
instantáneo) y solo lo descarga si es distinto.
"""

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.management.commands.runserver import Command as RunserverBase


class StaticFilesSinCache(StaticFilesHandler):
    def serve(self, request):
        respuesta = super().serve(request)
        respuesta["Cache-Control"] = "no-cache"
        return respuesta


class Command(RunserverBase):
    def get_handler(self, *args, **options):
        manejador = super().get_handler(*args, **options)
        if isinstance(manejador, StaticFilesHandler):
            return StaticFilesSinCache(manejador.application)
        return manejador
