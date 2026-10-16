from django.db import models

from eeg_library.preprocesado.reader import TARGET_SFREQ
from eeg_library.procesado.parametros import OPCIONES, PARAMETROS_ESTUDIO, normalizar_parametros

from grabaciones.calidad import nivel_de_fiabilidad


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

    @property
    def progreso(self):
        """Recuento por estado, para mostrar «7 de 20 procesadas»."""
        estados = [g.estado for g in self.grabaciones.all()]
        pendientes = sum(e in Grabacion.ESTADOS_PENDIENTES for e in estados)
        return {
            "total": len(estados),
            "procesadas": estados.count(Grabacion.Estado.PROCESADA),
            "con_error": estados.count(Grabacion.Estado.ERROR),
            "pendientes": pendientes,
        }

    @property
    def hay_fallidas_reintentables(self):
        return any(g.reintentable for g in self.grabaciones.all())


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

    ESTADOS_PENDIENTES = (Estado.EN_COLA, Estado.PROCESANDO)

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
    # Copia de `resultado["metadatos"]["n_canales_buenos"]`: la lista lo muestra sin
    # cargar el JSON completo de cada grabación en cada actualización.
    n_canales_buenos = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nombre_original

    @property
    def aviso_canales(self):
        """(nivel, texto) de aviso por pocos electrodos buenos, como en la librería."""
        if self.estado != self.Estado.PROCESADA:
            return "normal", ""
        return nivel_de_fiabilidad(self.n_canales_buenos)

    @property
    def reintentable(self):
        """Falló al procesar (y su EDF se conserva). Los rechazados al subir no tienen archivo."""
        return self.estado == self.Estado.ERROR and bool(self.archivo)

    @property
    def reprocesable(self):
        return self.estado == self.Estado.PROCESADA

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


class Procesador(models.Model):
    """
    Señal de vida del procesador (una sola fila). Lo escribe `manage.py procesar`
    cada pocos segundos; la web la lee para avisar si hay cola y nadie procesa.
    """

    pid = models.IntegerField()
    procesos = models.IntegerField()
    ultimo_latido = models.DateTimeField()

    @classmethod
    def activo(cls):
        """La fila del procesador si dio señales hace poco; si no, None."""
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        limite = timezone.now() - timedelta(seconds=settings.PROCESADOR_LATIDO_CADUCA_S)
        return cls.objects.filter(ultimo_latido__gte=limite).first()
