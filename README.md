# Secret room

A small real-time chat room built with Django, Bootstrap 5, HTML, CSS and a little JavaScript.
Pick a name and a room code. Anyone with the code can join. Messages are saved, and the last 50 show up when you enter.

The page talks to Django over plain HTTP (it checks for new messages every 1.5 seconds), so it works on any
host, including serverless ones like Vercel.

## Run it locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 in two browser windows, use the same room code, and chat.
Run the tests with `python manage.py test`.

## Deploy (Vercel, Render, etc.)

Serverless hosts have no writable disk, so use a free Postgres database (Neon, Supabase, Vercel Postgres, Render).

1. Create the database and copy its connection URL.
2. Set these environment variables on the host:
   - `DATABASE_URL` the Postgres URL
   - `DJANGO_SECRET_KEY` a long random string
   - `DJANGO_DEBUG` = `0`
3. Create the tables once, from your computer:
   ```bash
   DATABASE_URL="postgres://..." python manage.py migrate
   ```
4. Redeploy.

## Structure

- `config/` settings, URLs, WSGI/ASGI entry points
- `chat/models.py` `Message` and `Presence` (who is online / typing)
- `chat/views.py` home page, room page, and the JSON API (`poll`, `send`, `typing`)
- `templates/`, `static/` Bootstrap pages, custom CSS, and `room.js`
