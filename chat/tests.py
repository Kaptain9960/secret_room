from channels.testing import WebsocketCommunicator
from django.test import Client, TransactionTestCase

from chat.models import Message
from channels.routing import URLRouter

from chat.routing import websocket_urlpatterns

# Test the consumer directly; the real stack adds session + origin middleware.
application = URLRouter(websocket_urlpatterns)


def make(username, code="abc-123"):
    comm = WebsocketCommunicator(application, f"/ws/room/{code}/")
    comm.scope["session"] = {"username": username}
    return comm


class RoomTests(TransactionTestCase):
    def test_home_and_join_flow(self):
        c = Client()
        self.assertEqual(c.get("/").status_code, 200)
        r = c.post("/", {"username": "Ada", "room": "abc-123"})
        self.assertRedirects(r, "/room/abc-123/")
        self.assertEqual(c.get("/room/abc-123/").status_code, 200)
        self.assertEqual(Client().get("/room/abc-123/").status_code, 302)  # no name yet

    def test_bad_input_rejected(self):
        r = Client().post("/", {"username": "x", "room": "A B"})
        self.assertContains(r, "Pick a name")

    async def test_two_users_chat_and_history(self):
        a, b = make("Ada"), make("Bo")
        self.assertTrue((await a.connect())[0])
        self.assertEqual((await a.receive_json_from())["type"], "history")
        self.assertEqual((await a.receive_json_from())["users"], ["Ada"])

        self.assertTrue((await b.connect())[0])
        await b.receive_json_from()  # history
        self.assertEqual((await b.receive_json_from())["users"], ["Ada", "Bo"])
        await a.receive_json_from()  # presence update for Ada

        await a.send_json_to({"type": "message", "content": "<b>hi</b>"})
        got = await b.receive_json_from()
        self.assertEqual((got["type"], got["username"], got["content"]), ("message", "Ada", "<b>hi</b>"))
        self.assertEqual(await Message.objects.acount(), 1)

        await a.disconnect()
        await b.disconnect()

        c = make("Cy")
        await c.connect()
        hist = await c.receive_json_from()
        self.assertEqual(hist["messages"][0]["content"], "<b>hi</b>")
        await c.disconnect()

    async def test_no_username_rejected(self):
        comm = WebsocketCommunicator(application, "/ws/room/abc-123/")
        comm.scope["session"] = {}
        connected, _ = await comm.connect()
        self.assertFalse(connected)
