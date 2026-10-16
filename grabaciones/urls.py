from django.urls import path

from grabaciones import views

app_name = "grabaciones"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("subir/", views.subir, name="subir"),
    path("grabaciones/<int:pk>/condicion/", views.cambiar_condicion, name="condicion"),
]
