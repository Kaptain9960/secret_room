from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("room/<str:code>/", views.room, name="room"),
    path("api/room/<str:code>/poll/", views.poll, name="poll"),
    path("api/room/<str:code>/send/", views.send, name="send"),
    path("api/room/<str:code>/typing/", views.typing, name="typing"),
]
