import os
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.validators import ValidationError
from .models import ContactInquiry, QuoteRequest, File, Customer, Request, FileTransfer
from .utils import create_instance_with_images

User = get_user_model()

load_dotenv()

general_fields = [
    'id', 'name', 'email_address', 'phone_number', 'address', 'fax_number',
    'company', 'city_state_zip', 'country', 'additional_details',
    'files'
]

image_fields = general_fields + \
    ['preferred_mode_of_response', 'artwork_provided',
        'project_name', 'project_due_date']

customer_fields = ['id', 'company', 'address', 'city', 'state', 'zip',
                   'phone_number', 'fax_number', 'pay_tax', 'third_party_identifier', 'name']


class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'


class FileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(method_name='get_url')

    class Meta:
        model = File
        fields = ['path', 'url']

    def get_url(self, image: File):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        path = image.path
        return f"https://res.cloudinary.com/{cloud_name}/{path}"


class QuoteRequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']


class CreateQuoteRequestSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_images(QuoteRequest, validated_data)


class RequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Request
        fields = image_fields + ['this_is_an']
        read_only_fields = ['created_at']


class CreateRequestSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Request
        fields = image_fields + ["this_is_an"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        # Extract images from validated data
        images_data = validated_data.pop('images', [])
        with transaction.atomic():
            project_quote_request = Request.objects.create(
                **validated_data)

            # Create Image objects for each uploaded file
            for image_data in images_data:
                File.objects.create(
                    project=project_quote_request, path=image_data)

            return project_quote_request


class FileTransferSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type"]
        read_only_fields = ['created_at']


class CreateFileTransferSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_images(FileTransfer, validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [*customer_fields, 'email', 'username']

    def get_email(self, customer: Customer):
        return customer.user.email
    
    def get_username(self, customer: Customer):
        return customer.user.username

    def get_name(self, customer: Customer):
        return customer.user.name


class UpdateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = customer_fields

    @transaction.atomic()
    def update(self, instance, validated_data):
        name = validated_data.pop('name')

        customer = super().update(instance, validated_data)

        if name:
            user = instance.user 
            user.name = name
            user.save()

        return customer


class CreateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = [*customer_fields, 'email', 'password']

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def get_name(self, customer: Customer):
        return customer.user.name

    @transaction.atomic()
    def create(self, validated_data):
        email = validated_data.pop('email')
        name = validated_data.pop('name')
        password = validated_data.pop('password')
        username = email

        user = User.objects.create_user(
            email=email, password=password, name=name, username=username)
        customer = Customer.objects.create(user=user, **validated_data)

        return customer
