from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from grabaciones.models import Grabacion, Lote
from grabaciones.subida import LoteForm, guardar_lote

CONDICIONES_SUGERIDAS = ["OA", "OC", "STROOP", "PASAT", "PVTB", "MSIT", "PVSAT"]


def _pagina(request, formulario):
    lotes = Lote.objects.prefetch_related("grabaciones")
    return render(request, "grabaciones/lista.html", {
        "pantalla": "grabaciones",
        "formulario": formulario,
        "lotes": lotes,
        "hay_grabaciones": Grabacion.objects.exists(),
        "condiciones_sugeridas": CONDICIONES_SUGERIDAS,
    })


def lista(request):
    """Pantalla 1: subida de EDF y lista de grabaciones."""
    return _pagina(request, LoteForm())


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
        messages.success(request, f"Lote {lote.pk}: {correctas} grabaciones subidas.")
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
