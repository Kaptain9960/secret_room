from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("room/<str:code>/", views.room, name="room"),
]
