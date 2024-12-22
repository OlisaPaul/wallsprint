from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from store.models import Customer, Request, FileTransfer, Order, ContactInquiry
from ..models import ExtendedGroup, StaffNotification
from django.core.mail import send_mail


@receiver(post_save, sender=Group)
def create_extended_group(sender, instance, **kwargs):
    print("Called")
    if kwargs['created']:
        ExtendedGroup.objects.create(group=instance)


@receiver(post_delete, sender=Customer)
def delete_associated_user(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()


def send_notification_email(instance, model_name):
    print("Sending notification email")
    staff_emails = StaffNotification.objects.select_related(
        'user').values_list('user__email', flat=True)

    # Send email to staff
    send_mail(
        subject=f'New {model_name} Created',
        message=f'A new {model_name} has been created with ID: {instance.id}.',
        from_email='your_email@example.com',
        recipient_list=staff_emails,
        fail_silently=False,
    )

    # Send email to client
    client_email = instance.email_address
    client_name = instance.name
    send_mail(
        subject=f'Your {model_name} is being processed',
        message=f'Hello {client_name},\n\nYour {
            model_name} has been received and is currently being processed. We will update you shortly.\n\nThank you!',
        from_email='your_email@example.com',
        recipient_list=[client_email],
        fail_silently=False,
    )


@receiver(post_save, sender=Request)
def notify_on_request_creation(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'Request')


@receiver(post_save, sender=FileTransfer)
def notify_on_file_transfer_creation(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'FileTransfer')


@receiver(post_save, sender=Order)
def notify_on_order_creation(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'Order')


@receiver(post_save, sender=ContactInquiry)
def notify_on_contact_inquiry_creation(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'ContactInquiry')
