import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from dotenv import load_dotenv
from ..models import FileExchange



@receiver(post_save, sender=FileExchange)
def send_file_transfer_email(sender, instance, created, **kwargs):
    base_url = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')
    if created:  # Only send email when a new transfer is created
        subject = "File Transfer Notification"
        recipient = instance.recipient_email
        context = {
            'date': instance.created_at,  # Assuming you have a created_at field
            'recipient_name': instance.recipient_name,
            'recipient_email': instance.recipient_email,
            'sender_name': instance.name,
            'sender_email': instance.email_address,
            'details': instance.details,
            'file_name': instance.file.name.replace("uploads/", "", 1),
            'file_size': instance.file.size,
            'file_url': f'{base_url}{instance.file.url}',
        }
        message = render_to_string('email/file_transfer.html', context)
        email = EmailMessage(
            subject=subject,
            body=message,
            to=[recipient],
            from_email=settings.DEFAULT_FROM_EMAIL,
        )
        email.content_subtype = "html"  # Send as HTML email
        email.send()
