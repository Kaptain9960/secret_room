import json
import re
import secrets
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Message, Presence

ROOM_RE = re.compile(r"^[a-z0-9-]{3,40}$")
NAME_RE = re.compile(r"^[\w .-]{2,20}$")
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alike characters

HISTORY_LIMIT = 50
MAX_LEN = 1000
MIN_GAP = 0.4        # seconds between messages from one person
ONLINE_WINDOW = 12   # seen within this many seconds = in the room
TYPING_WINDOW = 4


def new_code():
    pick = lambda: "".join(secrets.choice(ALPHABET) for _ in range(3))
    return f"{pick()}-{pick()}"


def home(request):
    error = None
    room_code = request.GET.get("room", "").strip().lower()
    username = request.session.get("username", "")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        room_code = request.POST.get("room", "").strip().lower()
        if not NAME_RE.match(username):
            error = "Pick a name of 2 to 20 letters, numbers, spaces, dots or dashes."
        elif not ROOM_RE.match(room_code):
            error = "A room code is 3 to 40 lowercase letters, numbers or dashes."
        else:
            request.session["username"] = username
            return redirect("room", code=room_code)

    return render(
        request,
        "chat/home.html",
        {"error": error, "room": room_code or new_code(), "username": username},
    )


@ensure_csrf_cookie
def room(request, code):
    if not ROOM_RE.match(code):
        return redirect("home")
    username = request.session.get("username")
    if not username:
        return redirect(f"{reverse('home')}?room={code}")
    return render(
        request,
        "chat/room.html",
        {"code": code, "username": username, "csrf": str(get_token(request))},
    )


# ---------------- JSON API used by the room page ----------------

def _who(request, code):
    name = request.session.get("username")
    return name if name and ROOM_RE.match(code) else None


def _no_session():
    return JsonResponse({"error": "Pick a name first."}, status=401)


@require_GET
def poll(request, code):
    """Return new messages, who's online and who's typing. Also marks the caller as present."""
    name = _who(request, code)
    if not name:
        return _no_session()
    try:
        after = int(request.GET.get("after") or 0)
    except ValueError:
        after = 0

    now = timezone.now()
    Presence.objects.update_or_create(room=code, username=name, defaults={"last_seen": now})

    if after:
        rows = list(Message.objects.filter(room=code, id__gt=after).order_by("id")[:200])
    else:
        rows = list(reversed(Message.objects.filter(room=code).order_by("-id")[:HISTORY_LIMIT]))

    here = list(
        Presence.objects.filter(room=code, last_seen__gte=now - timedelta(seconds=ONLINE_WINDOW))
    )
    cutoff = now - timedelta(seconds=TYPING_WINDOW)
    return JsonResponse(
        {
            "messages": [m.as_dict() for m in rows],
            "users": sorted({p.username for p in here}, key=str.lower),
            "typing": [p.username for p in here if p.username != name and p.typing_at and p.typing_at >= cutoff],
        }
    )


@require_POST
def send(request, code):
    name = _who(request, code)
    if not name:
        return _no_session()
    try:
        text = str(json.loads(request.body).get("content", "")).strip()[:MAX_LEN]
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Bad request."}, status=400)
    if not text:
        return JsonResponse({"error": "Empty message."}, status=400)

    now = timezone.now()
    last = Message.objects.filter(room=code, username=name).order_by("-id").first()
    if last and (now - last.created_at).total_seconds() < MIN_GAP:
        return JsonResponse({"error": "Slow down a little."}, status=429)

    msg = Message.objects.create(room=code, username=name, content=text)
    Presence.objects.update_or_create(
        room=code, username=name, defaults={"last_seen": now, "typing_at": None}
    )
    return JsonResponse(msg.as_dict(), status=201)


@require_POST
def typing(request, code):
    name = _who(request, code)
    if not name:
        return _no_session()
    now = timezone.now()
    Presence.objects.update_or_create(
        room=code, username=name, defaults={"last_seen": now, "typing_at": now}
    )
    return JsonResponse({"ok": True})
