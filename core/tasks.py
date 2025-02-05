from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import BlacklistedToken
from datetime import datetime, timedelta
from django.template.loader import render_to_string


@shared_task
def send_notification_email_task(staff_email, instance_name, request_type):
    message = render_to_string('email/notification_email.html', {
        'instance_name': instance_name,
        'request_type': request_type,
    })

    send_mail(
        subject=f'Customer Request for Service – {instance_name}',
        message='',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=staff_email,
        fail_silently=False,
        html_message=message,
    )


@shared_task
def delete_expired_tokens_task():
    BlacklistedToken.objects.filter(
        created_at__lt=datetime.now() - timedelta(days=1)).delete()
