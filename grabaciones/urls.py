from django.urls import path
from django.views.generic import RedirectView

from grabaciones import views

app_name = "grabaciones"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("grabaciones/", views.lista, name="lista"),
    path("subir/", views.subir, name="subir"),
    path("lista/", views.lista_parcial, name="lista_parcial"),
    path("calidad/", views.atajo, {"seccion": "calidad"}, name="atajo_calidad"),
    path("analisis/", views.atajo, {"seccion": "analisis"}, name="atajo_analisis"),
    path("modelos/", views.atajo, {"seccion": "modelos"}, name="atajo_modelos"),
    path("tiempo-en-tarea/", views.atajo, {"seccion": "tiempo_en_tarea"}, name="atajo_tiempo_en_tarea"),
    path("modelos/resumen/", views.modelos_resumen, name="modelos_resumen"),
    path("grabaciones/<int:pk>/condicion/", views.cambiar_condicion, name="condicion"),
    path("grabaciones/<int:pk>/calidad/", views.calidad, name="calidad"),
    path("grabaciones/<int:pk>/analisis/", views.analisis, name="analisis"),
    path("grabaciones/<int:pk>/modelos/", views.modelos_grabacion, name="modelos_grabacion"),
    path("grabaciones/<int:pk>/tiempo-en-tarea/", views.tiempo_en_tarea, name="tiempo_en_tarea"),
    path("grabaciones/<int:pk>/csv/", views.csv_grabacion, name="csv_grabacion"),
    path("lotes/<int:pk>/csv/", views.csv_lote, name="csv_lote"),
    path("grabaciones/<int:pk>/eliminar/", views.eliminar_grabacion, name="eliminar_grabacion"),
    path("lotes/<int:pk>/eliminar/", views.eliminar_lote, name="eliminar_lote"),
    path("grabaciones/<int:pk>/encolar/", views.encolar, name="encolar"),
    path("lotes/<int:pk>/reintentar/", views.reintentar_lote, name="reintentar_lote"),
    # Direcciones antiguas (antes del 2026-11-05 la pestaña se llamaba de otra forma).
    path("fatiga-aguda/", RedirectView.as_view(pattern_name="grabaciones:atajo_tiempo_en_tarea",
                                               permanent=True)),
    path("grabaciones/<int:pk>/fatiga-aguda/", RedirectView.as_view(
        pattern_name="grabaciones:tiempo_en_tarea", permanent=True)),
]
