"""
Eliminar grabaciones y lotes de la plataforma.

Se borran el registro (con sus resultados) y la **copia** del EDF que la plataforma guardó en su
carpeta de datos. El archivo original del que se subió el EDF no se toca nunca: la web no conoce su
ruta, solo recibe una copia. Además, el borrado de archivos solo actúa dentro de
`MEDIA_ROOT/edf`: una ruta que quedase fuera de esa carpeta se deja como está.

Una grabación que se está procesando no se puede eliminar: el trabajador la tiene en marcha.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db import transaction

from grabaciones.models import Grabacion, Lote


def procesandose(grabaciones):
    """Las grabaciones de la lista que el trabajador tiene en marcha ahora mismo."""
    return [g for g in grabaciones if g.estado == Grabacion.Estado.PROCESANDO]


def _borrar_copia(grabacion):
    """Borra la copia del EDF de la plataforma. `True` si no queda ninguna (o no había)."""
    if not grabacion.archivo:
        return True
    raiz = (Path(settings.MEDIA_ROOT) / "edf").resolve()
    try:
        ruta = Path(grabacion.archivo.path).resolve()
        ruta.relative_to(raiz)           # fuera de `edf/`: no se toca
    except (SuspiciousFileOperation, ValueError):
        return False
    try:
        ruta.unlink(missing_ok=True)
    except OSError:
        return False
    if ruta.parent != raiz:              # la carpeta del lote, si ha quedado vacía
        try:
            ruta.parent.rmdir()
        except OSError:
            pass
    return True


def eliminar_grabaciones(grabaciones):
    """
    Elimina las grabaciones dadas (salvo las que se están procesando) y los lotes que queden vacíos.

    Devuelve `{"eliminadas": n, "bloqueadas": n, "copias_sin_borrar": n}`.
    """
    pks = [g.pk for g in grabaciones]
    with transaction.atomic():
        a_borrar = list(Grabacion.objects.select_for_update()
                        .filter(pk__in=pks).exclude(estado=Grabacion.Estado.PROCESANDO))
        lotes = {g.lote_id for g in a_borrar}
        Grabacion.objects.filter(pk__in=[g.pk for g in a_borrar]).delete()
        for lote in Lote.objects.filter(pk__in=lotes):
            if not lote.grabaciones.exists():
                lote.delete()
    sin_borrar = sum(not _borrar_copia(g) for g in a_borrar)
    return {"eliminadas": len(a_borrar), "bloqueadas": len(pks) - len(a_borrar),
            "copias_sin_borrar": sin_borrar}
