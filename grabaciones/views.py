from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from grabaciones.analisis_espectral import resumen_analisis
from grabaciones.calidad import resumen_calidad
from grabaciones.exportacion import csv_de, nombre_de_archivo_seguro
from grabaciones.models import Grabacion, Lote, Procesador
from grabaciones.subida import LoteForm, guardar_lote

CONDICIONES_SUGERIDAS = ["OA", "OC", "STROOP", "PASAT", "PVTB", "MSIT", "PVSAT"]


def _contexto_lista():
    hay_cola = Grabacion.objects.filter(estado__in=Grabacion.ESTADOS_PENDIENTES).exists()
    return {
        # Sin el JSON de resultados: la lista se actualiza cada pocos segundos.
        "lotes": Lote.objects.prefetch_related(
            Prefetch("grabaciones", queryset=Grabacion.objects.defer("resultado"))),
        "hay_grabaciones": Grabacion.objects.exists(),
        "condiciones_sugeridas": CONDICIONES_SUGERIDAS,
        "hay_cola": hay_cola,
        # Solo se avisa si hay trabajo pendiente: sin cola, que no haya procesador no importa.
        "procesador": Procesador.activo() if hay_cola else None,
    }


def _pagina(request, formulario):
    return render(request, "grabaciones/lista.html",
                  {"pantalla": "grabaciones", "formulario": formulario, **_contexto_lista()})


def lista(request):
    """Pantalla 1: subida de EDF y lista de grabaciones."""
    return _pagina(request, LoteForm())


def lista_parcial(request):
    """Solo la lista, para que se actualice sola mientras hay cola."""
    return render(request, "grabaciones/_lista.html", _contexto_lista())


def calidad(request, pk):
    """Pantalla 2: calidad de la señal de una grabación, a partir de su JSON guardado."""
    grabacion = get_object_or_404(Grabacion.objects.select_related("lote"), pk=pk)
    resumen = resumen_calidad(grabacion.resultado) if grabacion.estado == "procesada" else None
    return render(request, "grabaciones/calidad.html", {
        "pantalla": "calidad", "grabacion": grabacion, "resumen": resumen,
    })


def analisis(request, pk):
    """Pantalla 3: análisis espectral de una grabación, a partir de su JSON guardado."""
    grabacion = get_object_or_404(Grabacion.objects.select_related("lote"), pk=pk)
    resumen = resumen_analisis(grabacion.resultado) if grabacion.estado == "procesada" else None
    return render(request, "grabaciones/analisis.html", {
        "pantalla": "analisis", "grabacion": grabacion, "resumen": resumen,
    })


def _descarga(grabaciones, nombre):
    respuesta = HttpResponse(csv_de(grabaciones), content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def csv_grabacion(request, pk):
    """CSV de una grabación procesada (una fila)."""
    grabacion = get_object_or_404(Grabacion, pk=pk)
    if grabacion.estado != Grabacion.Estado.PROCESADA:
        messages.error(request, "Solo se pueden exportar las grabaciones ya procesadas.")
        return redirect("grabaciones:lista")
    stem = nombre_de_archivo_seguro(grabacion.nombre_original.rsplit(".", 1)[0])
    return _descarga([grabacion], f"eeg_{stem}.csv")


def csv_lote(request, pk):
    """CSV de las grabaciones procesadas de un lote (una fila por grabación)."""
    lote = get_object_or_404(Lote, pk=pk)
    procesadas = list(lote.grabaciones.filter(estado=Grabacion.Estado.PROCESADA))
    if not procesadas:
        messages.error(request, f"El lote {lote.pk} no tiene grabaciones procesadas que exportar.")
        return redirect("grabaciones:lista")
    return _descarga(procesadas, f"eeg_lote_{lote.pk}_{lote.fecha:%Y-%m-%d}.csv")


@require_POST
def subir(request):
    """Crea un lote con los EDF recibidos. Cada archivo se valida por separado."""
    formulario = LoteForm(request.POST)
    archivos = request.FILES.getlist("archivos")
    if not archivos:
        messages.error(request, "Elige al menos un archivo EDF.")
    if not formulario.is_valid() or not archivos:
        return _pagina(request, formulario)

    lote = formulario.save()
    grabaciones = guardar_lote(lote, archivos)
    con_error = sum(g.estado == Grabacion.Estado.ERROR for g in grabaciones)
    correctas = len(grabaciones) - con_error
    if correctas:
        messages.success(request, f"Lote {lote.pk}: {correctas} grabaciones en cola.")
    if con_error:
        messages.error(request, f"Lote {lote.pk}: {con_error} archivos con error "
                                f"(se indica en la lista).")
    return redirect("grabaciones:lista")


@require_POST
def cambiar_condicion(request, pk):
    """Edita la condición de una grabación; vacía significa «sin condición»."""
    grabacion = get_object_or_404(Grabacion, pk=pk)
    campo = Grabacion._meta.get_field("condicion")
    condicion = request.POST.get("condicion", "").strip().upper()[:campo.max_length]
    grabacion.condicion = condicion
    grabacion.origen_condicion = (Grabacion.OrigenCondicion.MANUAL if condicion
                                  else Grabacion.OrigenCondicion.VACIA)
    grabacion.save(update_fields=["condicion", "origen_condicion"])
    return redirect("grabaciones:lista")


@require_POST
def encolar(request, pk):
    """Reintenta una grabación fallida o reprocesa una procesada (conserva el resultado hasta el nuevo)."""
    grabacion = get_object_or_404(Grabacion, pk=pk)
    if grabacion.reintentable or grabacion.reprocesable:
        grabacion.estado = Grabacion.Estado.EN_COLA
        grabacion.mensaje_error = ""
        grabacion.save(update_fields=["estado", "mensaje_error"])
    else:
        messages.error(request, "Esa grabación no se puede volver a procesar ahora.")
    return redirect("grabaciones:lista")


@require_POST
def reintentar_lote(request, pk):
    """Devuelve a la cola las grabaciones del lote que fallaron al procesarse."""
    lote = get_object_or_404(Lote, pk=pk)
    n = sum(1 for g in lote.grabaciones.all() if g.reintentable)
    Grabacion.objects.filter(
        lote=lote, estado=Grabacion.Estado.ERROR).exclude(archivo="").update(
        estado=Grabacion.Estado.EN_COLA, mensaje_error="")
    messages.success(request, f"Lote {lote.pk}: {n} grabaciones vuelven a la cola.")
    return redirect("grabaciones:lista")
