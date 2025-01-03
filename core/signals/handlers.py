from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from store.models import Customer, Request, FileTransfer, Order, ContactInquiry, QuoteRequest
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
    staff_notifications = StaffNotification.objects.select_related(
        'user').values('user__email', 'user__name')

    # Determine the request type based on the instance type
    request_type = {
        'QuoteRequest': 'Estimate Request',
        'Request': 'New Design Order',
        'FileTransfer': 'Design-Ready Order',
        'Order': 'Design-Ready Order',
        'ContactInquiry': 'General Contact'
    }.get(model_name, 'Service/Product Inquiry/Support')

    # Send email to staff
    for staff in staff_notifications:
        staff_email = staff['user__email']
        staff_name = staff['user__name']
        send_mail(
            subject=f'Customer Request for Service – {instance.name}',
            message=f'Dear {staff_name},\n\n'
            f'We have received a request from {instance.name} regarding {request_type}. '
            f'Please review the details below:\n\n'
            f'Customer Name: {instance.name}\n'
            f'Request Type: {request_type}\n'
            f'Kindly take the necessary steps to assist them at your earliest convenience.\n\n'
            f'Best regards,\n'
            f'The WallsPrinting Team\n'
            f'{settings.EMAIL_HOST_USER}',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[staff_email],
            fail_silently=False,
        )

    # Send email to client
    client_email = instance.email_address
    client_name = instance.name
    send_mail(
        subject=f'Your {model_name} is being processed',
        message=f'Hello {client_name},\n\nYour {model_name} has been received and is currently being processed. We will update you shortly.\n\nThank you!',
        from_email='your_email@example.com',
        recipient_list=[client_email],
        fail_silently=False,
    )


@receiver(post_save, sender=QuoteRequest)
def notify_on_request_creation(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'QuoteRequest')


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
