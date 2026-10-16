from django.urls import path

from grabaciones import views

app_name = "grabaciones"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("subir/", views.subir, name="subir"),
    path("lista/", views.lista_parcial, name="lista_parcial"),
    path("grabaciones/<int:pk>/condicion/", views.cambiar_condicion, name="condicion"),
    path("grabaciones/<int:pk>/calidad/", views.calidad, name="calidad"),
    path("grabaciones/<int:pk>/analisis/", views.analisis, name="analisis"),
    path("grabaciones/<int:pk>/encolar/", views.encolar, name="encolar"),
    path("lotes/<int:pk>/reintentar/", views.reintentar_lote, name="reintentar_lote"),
]
