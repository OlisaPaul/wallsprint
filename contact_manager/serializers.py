import os
from django.db import transaction
from rest_framework import serializers
from .models import ContactInquiry, QuoteRequest, Image
from dotenv import load_dotenv
load_dotenv()

image_fields = [
    'id', 'name', 'email_address', 'phone_number', 'address', 'fax_number',
    'company', 'city_state_zip', 'country', 'preferred_mode_of_response',
    'artwork_provided', 'project_name', 'project_due_date', 'additional_details',
    'images'
]


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
