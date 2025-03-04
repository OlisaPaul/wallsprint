release: python manage.py migrate
web: daphne -b 0.0.0.0 -p $PORT wallsprint.asgi:application
worker: celery -A wallsprint worker