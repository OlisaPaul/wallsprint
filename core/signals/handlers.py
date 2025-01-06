from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from store.models import Customer, Request, FileTransfer, Order, ContactInquiry, QuoteRequest
from ..models import ExtendedGroup, StaffNotification
from core.tasks import send_notification_email_task


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

    # Enqueue email tasks
    for staff in staff_notifications:
        staff_email = staff['user__email']
        staff_name = staff['user__name']
        send_notification_email_task.delay(
            staff_email, staff_name, instance.name, request_type)


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
