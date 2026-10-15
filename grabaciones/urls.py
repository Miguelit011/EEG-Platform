from django.urls import path

from grabaciones import views

app_name = "grabaciones"

urlpatterns = [
    path("", views.lista, name="lista"),
]
