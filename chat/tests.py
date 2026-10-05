import json

from django.test import Client, TestCase

from chat.models import Message




class RoomTests(TestCase):
    def login(self, name, room="abc-123"):
        c = Client()
        self.assertRedirects(c.post("/", {"username": name, "room": room}), f"/room/{room}/")
        return c

    def post(self, c, path, data):
        return c.post(path, json.dumps(data), content_type="application/json")

    def test_pages_and_validation(self):
        self.assertEqual(Client().get("/").status_code, 200)
        self.assertContains(Client().post("/", {"username": "x", "room": "A B"}), "Pick a name")
        self.assertEqual(Client().get("/room/abc-123/").status_code, 302)  # needs a name first

    def test_api_requires_name(self):
        self.assertEqual(Client().get("/api/room/abc-123/poll/").status_code, 401)
        self.assertEqual(self.post(Client(), "/api/room/abc-123/send/", {"content": "hi"}).status_code, 401)

    def test_send_poll_presence_typing(self):
        ada, bo = self.login("Ada"), self.login("Bo")
        self.assertEqual(ada.get("/api/room/abc-123/poll/").json()["messages"], [])
        bo.get("/api/room/abc-123/poll/")

        r = self.post(ada, "/api/room/abc-123/send/", {"content": "<b>hi</b>"})
        self.assertEqual(r.status_code, 201)

        data = bo.get("/api/room/abc-123/poll/?after=0").json()
        self.assertEqual([m["content"] for m in data["messages"]], ["<b>hi</b>"])
        self.assertEqual(data["users"], ["Ada", "Bo"])
        last = data["messages"][-1]["id"]
        self.assertEqual(bo.get(f"/api/room/abc-123/poll/?after={last}").json()["messages"], [])

        self.post(ada, "/api/room/abc-123/typing/", {})
        self.assertEqual(bo.get(f"/api/room/abc-123/poll/?after={last}").json()["typing"], ["Ada"])

    def test_empty_rate_limit_and_rooms_isolated(self):
        ada = self.login("Ada")
        self.assertEqual(self.post(ada, "/api/room/abc-123/send/", {"content": "   "}).status_code, 400)
        self.assertEqual(self.post(ada, "/api/room/abc-123/send/", {"content": "one"}).status_code, 201)
        self.assertEqual(self.post(ada, "/api/room/abc-123/send/", {"content": "two"}).status_code, 429)
        self.assertEqual(Message.objects.filter(room="other-room").count(), 0)
        self.assertEqual(ada.get("/api/room/other-room/poll/").json()["messages"], [])

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/api/room/abc-123/send/", "{}", content_type="application/json").status_code, 403)
