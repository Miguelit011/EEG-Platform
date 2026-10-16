from django.db import models

from eeg_library.preprocesado.reader import TARGET_SFREQ
from eeg_library.procesado.parametros import OPCIONES, PARAMETROS_ESTUDIO, normalizar_parametros


def _texto_banda(banda):
    return f"{banda[0]:g}-{banda[1]:g}"


# Las opciones salen de la librería (cerradas); aquí solo se les pone etiqueta.
_ETIQUETA_REFERENCIA = {
    "car_condicional": "CAR condicional (la del estudio)",
    "original": "Original del casco, sin re-referenciar",
}
REFERENCIAS = [(r, _ETIQUETA_REFERENCIA[r]) for r in OPCIONES["referencia"]]
BANDAS = [(_texto_banda(b), f"{_texto_banda(b).replace('-', '–')} Hz") for b in OPCIONES["banda_hz"]]
BANDA_ESTUDIO = _texto_banda(PARAMETROS_ESTUDIO["banda_hz"])
HAY_NOTCH = PARAMETROS_ESTUDIO["notch_hz"] is not None


class Lote(models.Model):
    """Grabaciones subidas a la vez, con los parámetros de procesado comunes."""

    fecha = models.DateTimeField(auto_now_add=True)
    referencia = models.CharField(max_length=20, choices=REFERENCIAS,
                                  default=PARAMETROS_ESTUDIO["referencia"])
    banda = models.CharField("paso banda", max_length=10, choices=BANDAS, default=BANDA_ESTUDIO)
    notch = models.BooleanField("notch a 50 Hz", default=HAY_NOTCH)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Lote {self.pk}"

    def parametros(self):
        """Parámetros en el formato de `analizar_grabacion` (ya validados por la librería)."""
        notch = next(n for n in OPCIONES["notch_hz"] if n is not None)
        return normalizar_parametros({
            "referencia": self.referencia,
            "banda_hz": [float(x) for x in self.banda.split("-")],
            "notch_hz": notch if self.notch else None,
        })

    @property
    def resumen_parametros(self):
        referencia = dict(REFERENCIAS)[self.referencia]
        notch = "con notch 50 Hz" if self.notch else "sin notch"
        return f"{referencia} · {dict(BANDAS)[self.banda]} · {notch}"

    @property
    def con_parametros_del_estudio(self):
        return self.parametros() == normalizar_parametros()


def ruta_edf(grabacion, nombre):
    return f"edf/lote_{grabacion.lote_id}/{nombre}"


class Grabacion(models.Model):
    class Estado(models.TextChoices):
        SUBIDA = "subida", "Subida"
        EN_COLA = "en_cola", "En cola"
        PROCESANDO = "procesando", "Procesando"
        PROCESADA = "procesada", "Procesada"
        ERROR = "error", "Error"

    class OrigenCondicion(models.TextChoices):
        NOMBRE = "nombre", "Del nombre del archivo"
        MANUAL = "manual", "Escrita a mano"
        VACIA = "vacia", "Sin condición"

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="grabaciones")
    # Vacío si el archivo era inválido: solo se guardan los EDF que se pueden procesar.
    archivo = models.FileField(upload_to=ruta_edf, blank=True, max_length=300)
    nombre_original = models.CharField(max_length=255)
    condicion = models.CharField("condición", max_length=40, blank=True)
    origen_condicion = models.CharField(max_length=10, choices=OrigenCondicion.choices,
                                        default=OrigenCondicion.VACIA)
    duracion_s = models.FloatField(null=True, blank=True)
    sfreq_original_hz = models.FloatField(null=True, blank=True)
    remuestreada = models.BooleanField(default=False)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.SUBIDA)
    mensaje_error = models.TextField(blank=True)
    resultado = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nombre_original

    @property
    def duracion_texto(self):
        if self.duracion_s is None:
            return "—"
        minutos, segundos = divmod(round(self.duracion_s), 60)
        return f"{minutos} min {segundos:02d} s"

    @property
    def frecuencia_texto(self):
        if self.sfreq_original_hz is None:
            return "—"
        if self.remuestreada:
            return (f"{self.sfreq_original_hz:g} Hz → {TARGET_SFREQ:g} Hz "
                    f"(remuestreada)")
        return f"{self.sfreq_original_hz:g} Hz"
