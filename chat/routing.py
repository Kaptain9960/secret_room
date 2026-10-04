from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/room/(?P<code>[a-z0-9-]{3,40})/$", consumers.RoomConsumer.as_asgi()),
]
