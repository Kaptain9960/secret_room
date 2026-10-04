# Secret room

A small real-time chat room built with Django, Django Channels (WebSockets), Bootstrap 5, HTML and CSS.
Pick a name and a room code. Anyone with the code can join. Messages are saved, and the last 50 show up when you enter.

## Run it

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 in two browser windows, use the same room code, and chat.

Run the tests with `python manage.py test`.

## Structure

- `config/` settings, URLs, ASGI entry point (HTTP + WebSocket routing)
- `chat/models.py` the `Message` model
- `chat/views.py` home page (name + room code) and room page
- `chat/consumers.py` WebSocket logic: history, messages, typing, who's online
- `templates/`, `static/` Bootstrap pages, custom CSS, and `room.js`

## Before putting it online

- Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=yourdomain.com`
- Switch to Redis so several workers share one room: `pip install channels-redis`, then in `settings.py`:
  `CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [("127.0.0.1", 6379)]}}}`
  Also move the `ONLINE` presence dict in `chat/consumers.py` into Redis.
- Run with `daphne config.asgi:application` behind HTTPS (the client switches to `wss://` automatically)
# secret_room
