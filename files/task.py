from time import sleep
from celery import shared_task


@shared_task
def notify_customers(message):
    print('sending email to customers')
    print(message)
    sleep(10)
    print('email was sent')


message = 'hello, we have a sale on now'

notify_customers(message)
