from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import BlacklistedToken
from datetime import datetime, timedelta


@shared_task
def send_notification_email_task(staff_email, instance_name, request_type):
    send_mail(
        subject=f'Customer Request for Service – {instance_name}',
        message=f'Dear Team,\n\n'
        f'We have received a request from \
            {instance_name} regarding {request_type}. '
        f'Please review the details below:\n\n'
        f'Customer Name: {instance_name}\n'
        f'Request Type: {request_type}\n'
        f'Kindly take the necessary steps to assist them at your earliest convenience.\n\n'
        f'Best regards,\n'
        f'The WallsPrinting Team\n'
        f'{settings.EMAIL_HOST_USER}',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=staff_email,
        fail_silently=False,
    )


@shared_task
def delete_expired_tokens_task():
    BlacklistedToken.objects.filter(
        created_at__lt=datetime.now() - timedelta(days=1)).delete()
