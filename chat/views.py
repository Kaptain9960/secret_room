import re
import secrets

from django.shortcuts import redirect, render
from django.urls import reverse

ROOM_RE = re.compile(r"^[a-z0-9-]{3,40}$")
NAME_RE = re.compile(r"^[\w .-]{2,20}$")
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alike characters


def new_code():
    pick = lambda: "".join(secrets.choice(ALPHABET) for _ in range(3))
    return f"{pick()}-{pick()}"


def home(request):
    error = None
    room = request.GET.get("room", "").strip().lower()
    username = request.session.get("username", "")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        room = request.POST.get("room", "").strip().lower()
        if not NAME_RE.match(username):
            error = "Pick a name of 2 to 20 letters, numbers, spaces, dots or dashes."
        elif not ROOM_RE.match(room):
            error = "A room code is 3 to 40 lowercase letters, numbers or dashes."
        else:
            request.session["username"] = username
            return redirect("room", code=room)

    return render(
        request,
        "chat/home.html",
        {"error": error, "room": room or new_code(), "username": username},
    )


def room(request, code):
    if not ROOM_RE.match(code):
        return redirect("home")
    username = request.session.get("username")
    if not username:
        return redirect(f"{reverse('home')}?room={code}")
    return render(request, "chat/room.html", {"code": code, "username": username})
