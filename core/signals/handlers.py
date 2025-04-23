import os
from django.conf import settings
from django.db.models.signals import post_save, post_delete, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group
import requests
from store.models import Customer, Request, FileTransfer, Order, ContactInquiry, QuoteRequest, OnlinePayment
from ..models import ExtendedGroup, StaffNotification
from core.tasks import send_notification_email_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from dotenv import load_dotenv

load_dotenv()

admin_group_name = 'Primary Administrator'

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


def send_html_email_with_attachments(subject, context, template_name, from_email, recipient_list, files=[]):
    # Render HTML and plain-text bodies
    html_content = render_to_string(template_name, context)
    # text_content = render_to_string(template_name, context)

    # Create email with HTML + plain text
    email = EmailMultiAlternatives(
        subject=subject,
        body='',
        from_email=from_email,
        to=recipient_list,
    )
    email.attach_alternative(html_content, "text/html")

    existing_filenames = set()

    for file in files:
        url = file.get("url")
        name = file.get("name")

        if not url:
            print("Skipping file with no URL.")
            continue

        try:
            response = requests.get(url)
            print(f"Fetching: {url} - Status: {response.status_code}")

            if response.status_code == 200:
                filename = name or os.path.basename(url.split('?')[0])
                
                # Ensure unique filename
                if filename in existing_filenames:
                    base, ext = os.path.splitext(filename)
                    count = 1
                    while f"{base}_{count}{ext}" in existing_filenames:
                        count += 1
                    filename = f"{base}_{count}{ext}"
                existing_filenames.add(filename)

                content_type = response.headers.get("Content-Type", "application/octet-stream")
                email.attach(filename, response.content, content_type)
                print(f"Attached: {filename} ({len(response.content)} bytes)")
            else:
                print(f"Failed to download: {url}")
        except Exception as e:
            print(f"Error attaching {url}: {e}")

    email.send()


def send_notification_email(instance, model_name):
    print("Sending notification email")
    staff_notifications = StaffNotification.objects.select_related(
        'user').values_list('user__email', flat=True)
    
    request_type = {
        'QuoteRequest': 'Estimate Request',
        'Request': 'New Design Order',
        'FileTransfer': 'Design-Ready Order',
        'Order': 'Design-Ready Order',
        'ContactInquiry': 'General Contact',
        'OnlinePayment': 'Payment Proof Submission'
    }.get(model_name, 'Service/Product Inquiry/Support')


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
    elif model_name == 'Order':
        template = 'email/order_confirmation_editable.html'
        subject = f"New Order - {instance.po_number}"
        context =  context = {
                'order_number': instance.po_number,
                'customer_name': instance.name,
                'response_days': 2,
                'wallsprinting_phone': os.getenv('WALLSPRINTING_PHONE'),
                'wallsprinting_website': os.getenv('WALLSPRINTING_WEBSITE'),
                'invoice_number': instance.po_number,
                'po_number': instance.po_number,
                'payment_submission_link': 'your_payment_submission_link_here'
            }
        attached_files = []
        order_items = instance.items.all()
        for item in order_items:
            if item.front_pdf:
                attached_files.append({'url':item.front_pdf.url, 'name': item.front_pdf_name})        
            if item.back_pdf:
                attached_files.append({'url':item.back_pdf.url, 'name': item.back_pdf_name})        

        send_html_email_with_attachments(
                subject=subject,
                context=context,
                template_name=template,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=list(staff_notifications),
                files=attached_files,
            )
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
