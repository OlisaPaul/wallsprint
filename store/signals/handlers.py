import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from dotenv import load_dotenv
from ..models import FileExchange
from ..signals import file_transferred
from ..utils import get_base_url
from store.tasks import send_file_transfer_email_task


@receiver(file_transferred)
def send_file_transfer_email(sender, **kwargs):
    request = kwargs['request']
    instance = kwargs['file_transfer']
    base_url = get_base_url(request)

    subject = "File Transfer Notification"
    recipient = instance.recipient_email
    context = {
        'date': instance.created_at,
        'recipient_name': instance.recipient_name,
        'recipient_email': instance.recipient_email,
        'sender_name': instance.name,
        'sender_email': instance.email_address,
        'details': instance.details,
        'file_name': instance.file.name.replace("uploads/", "", 1),
        'file_size': instance.file.size,
        'file_url': f'{base_url}{instance.file.url}',
    }

    send_file_transfer_email_task.delay(subject, context, recipient)
