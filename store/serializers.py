import os
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.validators import ValidationError
import csv
from io import TextIOWrapper
from .models import ContactInquiry, HTMLFile, Portal, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, PortalContent
from .utils import create_instance_with_files

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

customer_fields = ['id', 'company', 'address', 'city_state_zip',
                   'phone_number', 'fax_number', 'pay_tax',
                   'third_party_identifier', 'credit_balance']


def create_file_fields(num_files, allowed_extensions):
    return {
        f'file{i+1}': serializers.FileField(
            validators=[FileExtensionValidator(
                allowed_extensions=allowed_extensions)],
            required=False
        )
        for i in range(num_files)
    }


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


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )
    has_header = serializers.BooleanField()

    def validate_file(self, file):
        if file.content_type != 'text/csv':
            raise serializers.ValidationError(
                "Invalid file type. Please upload a CSV file.")

        file_data = file.read().decode('utf-8')

        try:
            csv_reader = csv.DictReader(file_data.splitlines())
            list(csv_reader)
        except csv.Error:
            raise serializers.ValidationError(
                "CSV parsing error. Ensure the file is a valid CSV with UTF-8 encoding.")

        return file_data


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
        return create_instance_with_files(QuoteRequest, validated_data)


class RequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Request
        fields = image_fields + ['this_is_an']
        read_only_fields = ['created_at']


class CreateRequestSerializer(serializers.ModelSerializer):
    allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
    files = serializers.ListField(
        child=serializers.FileField(
            validators=[FileExtensionValidator(
                allowed_extensions=allowed_extensions)]
        ),
        write_only=True,
        required=False
    )

    class Meta:
        model = Request
        fields = image_fields + ["this_is_an"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(Request, validated_data)


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
        return create_instance_with_files(FileTransfer, validated_data)


class SimpleCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title']


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    groups = SimpleCustomerGroupSerializer(many=True, read_only=True)
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [*customer_fields, 'groups', 'groups_count',
                  'name', 'email', 'username', 'is_active']

    def get_email(self, customer: Customer):
        return customer.user.email

    def get_groups_count(self, customer: Customer):
        return customer.groups.count()

    def get_is_active(self, customer: Customer):
        return customer.user.is_active

    def get_username(self, customer: Customer):
        return customer.user.username

    def get_name(self, customer: Customer):
        return customer.user.name


class SimpleCustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'company']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email


class UpdateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(write_only=True)

    class Meta:
        model = Customer
        fields = [*customer_fields, 'is_active', 'name']

    @transaction.atomic()
    def update(self, instance, validated_data):
        name = validated_data.pop('name')
        is_active = validated_data.pop('is_active')

        customer = super().update(instance, validated_data)

        if name is not None or isinstance(is_active, bool):
            user = instance.user

            if name:
                user.name = name
            if isinstance(is_active, bool):
                user.is_active = is_active
            user.save()

        return customer


class CreateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(write_only=True)
    is_active = serializers.BooleanField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})
    username = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = [*customer_fields, 'email',
                  'password', 'username', 'name', 'is_active']

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(username=value).exists():
            raise ValidationError("A user with this username already exists.")
        return value

    def get_name(self, customer: Customer):
        return customer.user.name

    @transaction.atomic()
    def create(self, validated_data):
        email = validated_data.pop('email')
        is_active = validated_data.pop('is_active')
        name = validated_data.pop('name')
        username = validated_data.pop('username')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            email=email, password=password, name=name, username=username, is_active=is_active)
        customer = Customer.objects.create(user=user, **validated_data)

        return customer


class CustomerGroupSerializer(serializers.ModelSerializer):
    customers = SimpleCustomerSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()

    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers', "date_created", "members"]

    def get_members(self, customer_group: CustomerGroup):
        return customer_group.customers.count()


class CreateCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers']


class BulkCreateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = [*customer_fields, 'name', 'email', 'password']

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value


class HTMLFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HTMLFile
        fields = ['id', 'title', 'link']


class PortalContentSerializer(serializers.ModelSerializer):
    customer_groups = CustomerGroupSerializer(many=True, read_only=True)
    customers = SimpleCustomerSerializer(many=True, read_only=True)
    can_user_access = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    html_file = HTMLFileSerializer()

    class Meta:
        model = PortalContent
        fields = ['id', 'html_file',
                  'customer_groups', 'everyone', 'can_user_access', 'customers', 'groups_count', 'user_count']

    def get_can_user_access(self, obj):
        request = self.context['request']
        user = request.user
        user = User.objects.get(id=request.user.id)

        if user.is_staff:
            return True

        customer = Customer.objects.get(user=user)
        customer_id = customer.id
        customer_ids = obj.get_accessible_customers()

        return customer_id in customer_ids

    def get_groups_count(self, portal_content: PortalContent):
        return portal_content.customer_groups.count()

    def get_user_count(self, portal_content: PortalContent):
        return portal_content.customers.count()


class CreatePortalContentSerializer(serializers.ModelSerializer):
    customer_groups = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    customers = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = PortalContent
        fields = ['id', 'html_file',
                  'customer_groups', 'everyone', 'customers']


class PortalSerializer(serializers.ModelSerializer):
    content = PortalContentSerializer(many=True)

    class Meta:
        model = Portal
        fields = ['id', 'name', 'content']


class CreatePortalSerializer(serializers.ModelSerializer):
    content = CreatePortalContentSerializer(many=True)

    class Meta:
        model = Portal
        fields = ['id', 'name', 'content']

    @transaction.atomic()
    def create(self, validated_data):
        content_data = validated_data.pop('content')
        portal = Portal.objects.create(**validated_data)

        for content in content_data:
            customer_group_data = []
            customer_data = []
            everyone = content.get('everyone')

            if isinstance(content.get('customer_groups'), list):
                customer_group_data = content.pop('customer_groups')

            if isinstance(content.get('customers'), list):
                customer_data = content.pop('customers')
            
            is_customer_or_customer_data = customer_group_data or customer_data

            if is_customer_or_customer_data and everyone:
                raise ValidationError(
                    "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only.")

            portal_content = PortalContent.objects.create(
                portal=portal, **content)

            if customer_group_data:
                portal_content.customer_groups.set(customer_group_data)

            if customer_data:
                portal_content.customers.set(customer_data)

        return portal
