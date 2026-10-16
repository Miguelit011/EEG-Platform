import hashlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from eeg_library.modelado.prediccion import leer_ficha, listar_modelos, predecir
from eeg_library.procesado.grabacion import ALIAS_CARACTERISTICAS

from grabaciones import modelos


class Command(BaseCommand):
    help = ("Comprueba cada modelo de settings.MODELOS: que existan su ficha y su .joblib, "
            "que coincidan, que sus columnas sean características que la plataforma "
            "calcula y que puedan predecir.")

    def handle(self, *args, **opciones):
        self.stdout.write(f"Carpeta de modelos externos: {settings.MODELOS_DIR}")
        # Las características que guarda la plataforma son las 70 de los modelos del estudio,
        # empaquetados en EEG-Library.
        disponibles = set()
        for id_modelo in listar_modelos():
            disponibles |= set(leer_ficha(id_modelo)[0]["columnas"])
        fallos = 0
        for nombre in settings.MODELOS:
            problemas = self._comprobar(nombre, disponibles)
            if problemas:
                fallos += 1
                self.stdout.write(self.style.ERROR(f"✖ {nombre}"))
                for p in problemas:
                    self.stdout.write(f"    - {p}")
            else:
                ficha = leer_ficha(modelos._entrada(nombre))[0]
                self.stdout.write(self.style.SUCCESS(
                    f"✔ {nombre}: «{ficha.get('titulo', ficha['id'])}», "
                    f"clases {', '.join(c['nombre'] for c in ficha['clases'])}"))
        if fallos:
            raise CommandError(f"{fallos} modelo(s) con problemas. Revisa docs/AÑADIR_UN_MODELO.md.")
        self.stdout.write("Todos los modelos están bien.")

    def _comprobar(self, nombre, disponibles):
        problemas = []
        try:
            ficha, ruta_ficha = leer_ficha(modelos._entrada(nombre))
        except FileNotFoundError:
            return [f"No se encuentra la ficha. Si es un modelo externo, debe estar en "
                    f"{settings.MODELOS_DIR} y su nombre acabar en .json."]
        except ValueError as error:
            return [str(error)]
        except Exception as error:
            return [f"La ficha no es un JSON válido: {error}"]

        ruta_modelo = ruta_ficha.parent / ficha["archivo"]
        if not ruta_modelo.is_file():
            return [f"No se encuentra el archivo del modelo «{ficha['archivo']}» junto a su ficha."]
        sha = hashlib.sha256(Path(ruta_modelo).read_bytes()).hexdigest()
        if sha != ficha["sha256_modelo"]:
            return [f"El SHA-256 de «{ficha['archivo']}» no coincide con el de la ficha. "
                    f"El de este archivo es: {sha}"]

        try:
            modelo = modelos.cargar(nombre)
        except modelos.ErrorDeModelo as error:
            return problemas + [str(error)]

        por_clase = ficha.get("condiciones_por_clase")
        if por_clase:
            if list(por_clase) != [c["nombre"] for c in ficha["clases"]]:
                problemas.append("`condiciones_por_clase` debe tener una entrada por cada clase, "
                                 "en el mismo orden.")
            if sorted(c for v in por_clase.values() for c in v) != sorted(
                    ficha["condiciones_aplicables"]):
                problemas.append("Las condiciones de `condiciones_por_clase` deben ser exactamente "
                                 "las de `condiciones_aplicables`, sin repetir.")
        faltan = [c for c in ficha["columnas"]
                  if c not in disponibles and ALIAS_CARACTERISTICAS.get(c) not in disponibles]
        if faltan:
            problemas.append(f"Usa {len(faltan)} característica(s) que la plataforma no calcula: "
                             f"{', '.join(faltan[:5])}{'…' if len(faltan) > 5 else ''}")
            return problemas
        try:
            prueba = predecir(modelo, {c: 0.0 for c in ficha["columnas"]},
                              ficha["parametros_validos"])
            if not prueba["disponible"]:
                problemas.append("No puede predecir con sus propios parámetros válidos.")
        except Exception as error:
            problemas.append(f"Falla al predecir: {error}")
        return problemas
