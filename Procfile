release: python manage.py migrate
web: daphne wallsprint.asgi:application
worker: celery -A wallsprint worker