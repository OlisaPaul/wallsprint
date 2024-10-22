from uuid import uuid4
from django.conf import settings
from django.db import models
from cloudinary.models import CloudinaryField
import datetime

# Create your models here.


class CommonFields(models.Model):
    name = models.CharField(max_length=255)
    email_address = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    fax_number = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True)
    city_state_zip = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    preferred_mode_of_response = models.CharField(
        max_length=50,
        choices=[
            ('Email', 'Email'),
            ('Phone', 'Phone'),
            ('Fax', 'Fax')
        ],
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ContactInquiry(CommonFields):
    questions = models.TextField()
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - Inquiry"


class QuoteRequest(CommonFields):
    artwork_provided = models.CharField(
        max_length=50,
        choices=[
            ('None', 'None'),
            ('Online file transfer', 'Online file transfer'),
            ('On disk', 'On disk'),
            ('Hard copy', 'Hard copy'),
            ('Film provided', 'Film provided'),
            ('Please estimate for design', 'Please estimate for design')
        ],
        blank=True
    )
    project_name = models.CharField(max_length=255)
    project_due_date = models.DateField(default=datetime.date.today)
    additional_details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.project_name}"


class Request(CommonFields):
    artwork_provided = models.CharField(
        max_length=50,
        choices=[
            ('None', 'None'),
            ('Online file transfer', 'Online file transfer'),
            ('On disk', 'On disk'),
            ('Hard copy', 'Hard copy'),
            ('Film provided', 'Film provided'),
            ('Please estimate for design', 'Please estimate for design')
        ],
        blank=True
    )
    project_name = models.CharField(max_length=255)
    project_due_date = models.DateField(default=datetime.date.today)
    additional_details = models.TextField(blank=True)
    you_are_a = models.CharField(
        max_length=50,
        choices=[
            ('New Customer', 'New Customer'),
            ('Current Customer', 'Current Customer'),
        ],
    )

    this_is_an = models.CharField(
        max_length=50,
        choices=[
            ('Order Request', 'Order Request'),
            ('Estimate Request', 'Estimate Request'),
        ],
    )


class Image(models.Model):
    project = models.ForeignKey(
        QuoteRequest, related_name='images', on_delete=models.CASCADE)
    path = CloudinaryField('image', blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.project.project_name}"


class Customer(models.Model):
    company = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    fax_number = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    pay_tax = models.BooleanField()
    third_party_identifier = models.CharField(max_length=255)
    credit_balance = models.DecimalField(
        max_digits=9, decimal_places=2, default=0)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
