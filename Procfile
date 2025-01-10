release: python manage.py migrate
web: gunicorn wallsprint.wsgi
worker: celery -A wallsprint worker