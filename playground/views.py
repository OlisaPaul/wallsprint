import json
from rest_framework.response import Response
from django.shortcuts import render
from .tasks import notify_customers
from django_celery_beat.models import PeriodicTask, CrontabSchedule

def say_hello(request):
    notify_customers.delay('hello, we have a sale on now')
    return render(request, 'hello.html', {'name': 'Mosh'})


def schedule_mail(request):
    schedule, created = CrontabSchedule.objects.get_or_create(hour=14, minute=37)
    task = PeriodicTask.objects.create(crontab=schedule, name='Send email' + '20', task='playground.tasks.notify_customers', args=json.dumps(['Hello World']), one_off=True)
    return render(request, 'hello.html', {'name': 'Paul Olisaeloka'})
