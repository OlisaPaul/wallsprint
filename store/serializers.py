import os
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import ValidationError
from .models import ContactInquiry, QuoteRequest, Image, Customer, Request
from dotenv import load_dotenv

User = get_user_model()

load_dotenv()

image_fields = [
    'id', 'name', 'email_address', 'phone_number', 'address', 'fax_number',
    'company', 'city_state_zip', 'country', 'preferred_mode_of_response',
    'artwork_provided', 'project_name', 'project_due_date', 'additional_details',
    'images'
]

customer_fields = ['id', 'company', 'address', 'city', 'state', 'zip',
                   'phone_number', 'fax_number', 'pay_tax', 'third_party_identifier', 'name', 'email', 'password']


class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(method_name='get_url')

    class Meta:
        model = Image
        fields = ['path', 'url']

    def get_url(self, image: Image):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        path = image.path
        return f"https://res.cloudinary.com/{cloud_name}/{path}"


class QuoteRequestSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']


class CreateQuoteRequestSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']

    def create(self, validated_data):
        # Extract images from validated data
        images_data = validated_data.pop('images', [])
        with transaction.atomic():
            project_quote_request = QuoteRequest.objects.create(
                **validated_data)

            # Create Image objects for each uploaded file
            for image_data in images_data:
                Image.objects.create(
                    project=project_quote_request, path=image_data)

            return project_quote_request


class RequestSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = Request
        fields = image_fields
        read_only_fields = ['created_at']


class CreateRequestSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Request
        fields = image_fields + ["this_is_an", "you_are_a"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        # Extract images from validated data
        images_data = validated_data.pop('images', [])
        with transaction.atomic():
            project_quote_request = Request.objects.create(
                **validated_data)

            # Create Image objects for each uploaded file
            for image_data in images_data:
                Image.objects.create(
                    project=project_quote_request, path=image_data)

            return project_quote_request


class CustomerSerializer(serializers.ModelSerializer):
    # Include User-related fields
    email = serializers.SerializerMethodField(method_name='get_email')
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = customer_fields

    def get_email(self, customer: Customer):
        return customer.user.email


class CreateCustomerSerializer(serializers.ModelSerializer):
    # Include User-related fields
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = customer_fields

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        # Extract the user-related data
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        user = User.objects.create_user(email=email, password=password)
        customer = Customer.objects.create(user=user, **validated_data)

        return customer
