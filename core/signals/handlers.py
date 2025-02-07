from django.conf import settings
from django.db.models.signals import post_save, post_delete, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group
from store.models import Customer, Request, FileTransfer, Order, ContactInquiry, QuoteRequest, OnlinePayment
from ..models import ExtendedGroup, StaffNotification
from core.tasks import send_notification_email_task
from django.core.mail import send_mail
from django.template.loader import render_to_string

admin_group_name = 'super_user'

@receiver(post_migrate)
def create_superuser_group(sender, **kwargs):
    """Ensure the 'superuser' group exists after migrations."""
    Group.objects.get_or_create(name=admin_group_name)

@receiver(post_save, sender=Group)
def create_extended_group(sender, instance, **kwargs):
    if kwargs['created']:
        for_superuser = instance.name == admin_group_name
        ExtendedGroup.objects.create(group=instance, for_superuser=for_superuser)


@receiver(post_delete, sender=Customer)
def delete_associated_user(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()


def send_notification_email(instance, model_name):
    print("Sending notification email")
    staff_notifications = StaffNotification.objects.select_related(
        'user').values_list('user__email', flat=True)

    if model_name == 'OnlinePayment':
        # Prepare email content
        subject = f"New Payment Proof Submission - Order {instance.po_number}"
        message = render_to_string('email/team_payment_notification.html', {
            'po_number': instance.po_number,
            'customer_name': instance.name,
            'amount': instance.amount,
        })

        # Send email to all staff members
        send_mail(
            subject=subject,
            message='',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=list(staff_notifications),
            html_message=message,
            fail_silently=False,
        )
    else:
        # Handle other model types
        request_type = {
            'QuoteRequest': 'Estimate Request',
            'Request': 'New Design Order',
            'FileTransfer': 'Design-Ready Order',
            'Order': 'Design-Ready Order',
            'ContactInquiry': 'General Contact'
        }.get(model_name, 'Service/Product Inquiry/Support')

    # Enqueue email tasks
    name = instance.name if hasattr(instance, 'name') else instance.customer.user.name
    send_notification_email_task(
        list(staff_notifications),
        instance_name=name, 
        request_type=request_type
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


@receiver(post_save, sender=OnlinePayment)
def notify_on_online_payment(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance, 'OnlinePayment')
