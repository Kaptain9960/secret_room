import time
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Message

HISTORY_LIMIT = 50
MAX_LEN = 1000
MIN_GAP = 0.3  # seconds between messages from one connection

# room code -> {channel_name: username}
# Lives in process memory, which matches the in-memory channel layer.
# With Redis and several workers, keep presence in Redis instead.
ONLINE = defaultdict(dict)


@database_sync_to_async
def get_username(session):
    # Real sessions load lazily from the DB, so read them in a sync thread.
    return session.get("username") if session is not None else None


@database_sync_to_async
def load_history(code):
    rows = Message.objects.filter(room=code).order_by("-id")[:HISTORY_LIMIT]
    return [m.as_dict() for m in reversed(list(rows))]


@database_sync_to_async
def save_message(code, username, content):
    return Message.objects.create(room=code, username=username, content=content).as_dict()


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.group = f"room_{self.code}"
        self.username = await get_username(self.scope.get("session"))
        self.last_sent = 0.0

        if not self.username:
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        ONLINE[self.code][self.channel_name] = self.username
        await self.send_json({"type": "history", "messages": await load_history(self.code)})
        await self.channel_layer.group_send(self.group, {"type": "presence.update"})

    async def disconnect(self, code):
        if not getattr(self, "username", None):
            return
        ONLINE[self.code].pop(self.channel_name, None)
        if not ONLINE[self.code]:
            ONLINE.pop(self.code, None)
        await self.channel_layer.group_discard(self.group, self.channel_name)
        await self.channel_layer.group_send(self.group, {"type": "presence.update"})

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")

        if kind == "message":
            text = str(content.get("content", "")).strip()[:MAX_LEN]
            now = time.monotonic()
            if not text or now - self.last_sent < MIN_GAP:
                return
            self.last_sent = now
            payload = await save_message(self.code, self.username, text)
            await self.channel_layer.group_send(
                self.group, {"type": "chat.message", "payload": payload}
            )

        elif kind == "typing":
            await self.channel_layer.group_send(
                self.group,
                {"type": "chat.typing", "username": self.username, "sender": self.channel_name},
            )

    # ---- group event handlers ----
    async def chat_message(self, event):
        await self.send_json({"type": "message", **event["payload"]})

    async def chat_typing(self, event):
        if event["sender"] != self.channel_name:
            await self.send_json({"type": "typing", "username": event["username"]})

    async def presence_update(self, event):
        users = sorted(set(ONLINE.get(self.code, {}).values()), key=str.lower)
        await self.send_json({"type": "presence", "users": users})
