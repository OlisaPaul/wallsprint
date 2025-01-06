from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string


@shared_task
def send_file_transfer_email_task(subject, context, recipient):
    message = render_to_string('email/file_transfer.html', context)
    email = EmailMessage(
        subject=subject,
        body=message,
        to=[recipient],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
    email.content_subtype = "html"
    email.send()
