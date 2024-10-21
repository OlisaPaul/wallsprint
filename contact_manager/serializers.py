from rest_framework import serializers
from .models import ContactInquiry, ProjectQuoteRequest, Image
import cloudinary.uploader

class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'image_url', 'upload_date']

class ProjectQuoteRequestSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = ProjectQuoteRequest
        fields = ['name', 'email', 'phone_number', 'company', 'city_state_zip', 'country', 
                  'preferred_mode_of_response', 'artwork_provided', 'project_name', 
                  'additional_details', 'uploaded_files', 'images']

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        project_quote_request = ProjectQuoteRequest.objects.create(**validated_data)

        # Upload files to Cloudinary and create Image instances
        for file in uploaded_files:
            result = cloudinary.uploader.upload(file)
            Image.objects.create(project=project_quote_request, image_url=result['url'])

        return project_quote_request