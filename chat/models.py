from django.db import models


class Message(models.Model):
    room = models.CharField(max_length=40, db_index=True)
    username = models.CharField(max_length=20)
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"[{self.room}] {self.username}: {self.content[:30]}"

    def as_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "content": self.content,
            "time": self.created_at.isoformat(),
        }


class Presence(models.Model):
    """Who is in a room right now: refreshed every time their browser polls."""

    room = models.CharField(max_length=40)
    username = models.CharField(max_length=20)
    last_seen = models.DateTimeField()
    typing_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("room", "username")]
