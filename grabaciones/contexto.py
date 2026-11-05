"""
Contexto de navegación: la «grabación activa».

Calidad, Análisis y Modelos son pantallas de una grabación, así que la barra de navegación
necesita saber de cuál. La grabación activa es la que se está viendo; si no se está viendo
ninguna (por ejemplo, en la lista), la última que se abrió (la recuerda una cookie con su
número) o, si no hay, la última procesada. Así las pestañas están siempre activas.
"""

from django.urls import reverse

from grabaciones.models import Grabacion

COOKIE = "grabacion_activa"
VISTAS = {"calidad": "calidad", "analisis": "analisis", "modelos_grabacion": "modelos",
          "tiempo_en_tarea": "tiempo_en_tarea"}
NOMBRE_VISTA = {"calidad": "grabaciones:calidad", "analisis": "grabaciones:analisis",
                "modelos": "grabaciones:modelos_grabacion",
                "tiempo_en_tarea": "grabaciones:tiempo_en_tarea"}
ATAJO = {"calidad": "grabaciones:atajo_calidad", "analisis": "grabaciones:atajo_analisis",
         "modelos": "grabaciones:atajo_modelos", "tiempo_en_tarea": "grabaciones:atajo_tiempo_en_tarea"}


def url_de(seccion, pk):
    """Dirección de una sección (calidad, analisis o modelos) de la grabación `pk`, o su atajo."""
    return reverse(NOMBRE_VISTA[seccion], args=[pk]) if pk else reverse(ATAJO[seccion])


def procesadas():
    """`[{pk, nombre, lote}]` de las grabaciones procesadas, en el orden en que se subieron."""
    return [{"pk": g["pk"], "nombre": g["nombre_original"], "lote": g["lote_id"],
             "condicion": g["condicion"]}
            for g in Grabacion.objects.filter(estado=Grabacion.Estado.PROCESADA)
            .order_by("pk").values("pk", "nombre_original", "lote_id", "condicion")]


def activa(request, lista):
    """La grabación activa (su `pk`, o None si no hay ninguna) para esta petición."""
    coincidencia = getattr(request, "resolver_match", None)
    if coincidencia and coincidencia.url_name in VISTAS and "pk" in coincidencia.kwargs:
        return coincidencia.kwargs["pk"]
    try:
        recordada = int(request.COOKIES.get(COOKIE, ""))
    except ValueError:
        recordada = None
    if recordada and (any(g["pk"] == recordada for g in lista)
                      or Grabacion.objects.filter(pk=recordada).exists()):
        return recordada
    return lista[-1]["pk"] if lista else None


def navegacion(request):
    """Variables de plantilla para la barra de navegación y el selector de grabación."""
    # La lista de la página se refresca sola cada pocos segundos: ahí no hace falta nada de esto.
    if request.headers.get("X-Requested-With") == "fetch":
        return {}
    lista = procesadas()
    pk = activa(request, lista)
    posicion = next((i for i, g in enumerate(lista) if g["pk"] == pk), None)
    nombre = next((g["nombre"] for g in lista if g["pk"] == pk), None)
    if pk and nombre is None:   # activa, pero todavía sin procesar
        nombre = Grabacion.objects.filter(pk=pk).values_list("nombre_original", flat=True).first()

    seccion = VISTAS.get(getattr(getattr(request, "resolver_match", None), "url_name", ""))
    # Dirección de cada grabación en la sección actual: la de una cualquiera con su número cambiado.
    modelo_url = reverse(NOMBRE_VISTA[seccion], args=[0]) if seccion else None
    grupos = []
    for g in lista:
        if modelo_url:
            g["url"] = modelo_url.replace("/0/", f"/{g['pk']}/", 1)
        if not grupos or grupos[-1]["lote"] != g["lote"]:
            grupos.append({"lote": g["lote"], "grabaciones": []})
        grupos[-1]["grabaciones"].append(g)

    contexto = {
        "nav_activa": {"pk": pk, "nombre": nombre} if pk else None,
        "nav_grupos": grupos,
        "nav_total": len(lista),
        "nav_posicion": None if posicion is None else posicion + 1,
        "nav_url_calidad": url_de("calidad", pk),
        "nav_url_analisis": url_de("analisis", pk),
        "nav_url_modelos": url_de("modelos", pk),
        "nav_url_tiempo_en_tarea": url_de("tiempo_en_tarea", pk),
    }
    if seccion and posicion is not None:
        contexto["nav_seccion"] = seccion
        if posicion > 0:
            contexto["nav_url_anterior"] = url_de(seccion, lista[posicion - 1]["pk"])
        if posicion < len(lista) - 1:
            contexto["nav_url_siguiente"] = url_de(seccion, lista[posicion + 1]["pk"])
    return contexto


def recordar(respuesta, grabacion):
    """Guarda en una cookie la grabación que se acaba de abrir (solo su número)."""
    respuesta.set_cookie(COOKIE, str(grabacion.pk), max_age=60 * 60 * 24 * 365, samesite="Lax")
    return respuesta
