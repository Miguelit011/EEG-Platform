from django.shortcuts import render


def lista(request):
    """Pantalla 1: grabaciones. En la Fase 1 siempre está vacía."""
    return render(request, "grabaciones/lista.html",
                  {"pantalla": "grabaciones", "grabaciones": []})
