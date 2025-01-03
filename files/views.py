from django.shortcuts import render
from .task import notify_customers

# Create your views here.


def say_hello(request):
    notify_customers.delay('hello, we have a sale on now')
    return render(request, 'hello.html', {'name': 'Mosh'})
