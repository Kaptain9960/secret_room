from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("room", "username", "short", "created_at")
    list_filter = ("room",)
    search_fields = ("username", "content")

    @admin.display(description="message")
    def short(self, obj):
        return obj.content[:60]
