from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from grabaciones import procesador
from grabaciones.recursos import procesos_automaticos


class Command(BaseCommand):
    help = ("Procesa las grabaciones en cola, repartidas entre varios procesos. "
            "Déjalo abierto mientras uses la web; se para con Ctrl+C.")

    def add_arguments(self, parser):
        parser.add_argument("--procesos", type=int, default=None,
                            help="Procesos en paralelo. Si no se indica, EEG_PLATFORM_PROCESOS "
                                 "o, en su defecto, los que admite este equipo.")
        parser.add_argument("--una-vez", action="store_true",
                            help="Termina cuando la cola se vacía, en vez de esperar más.")

    def handle(self, *args, procesos, una_vez, **opciones):
        if procesos is not None and procesos < 1:
            raise CommandError("--procesos debe ser al menos 1.")
        if procesos is not None:
            origen = "indicados con --procesos"
        elif settings.PROCESOS is not None:
            procesos, origen = settings.PROCESOS, "fijados con EEG_PLATFORM_PROCESOS"
        else:
            procesos, equipo = procesos_automaticos()
            origen = f"calculados para este equipo: {equipo}"
        self.stdout.write(f"Procesador en marcha con {procesos} proceso(s), {origen}. "
                          f"Ctrl+C para parar.")
        try:
            hechas = procesador.trabajar(procesos, una_vez=una_vez, informar=self.stdout.write)
        except procesador.ProcesadorYaEnMarcha as error:
            raise CommandError(str(error))
        except KeyboardInterrupt:
            self.stdout.write("Procesador detenido. Lo que quedaba a medias seguirá en la cola.")
            return
        self.stdout.write(f"Cola vacía: {hechas['procesadas']} procesadas, "
                          f"{hechas['con_error']} con error.")
