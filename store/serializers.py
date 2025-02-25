import csv
import os
import re
import json
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.contrib.contenttypes.models import ContentType
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.validators import ValidationError
from io import TextIOWrapper
from django.core.mail import send_mail
from .models import AttributeOption, Attribute, Cart, CartItem, Catalog, CatalogItem, ContactInquiry, FileExchange, Page, OnlinePayment, OnlineProof, OrderItem, Portal, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, PortalContent, Order, OrderItem, PortalContentCatalog, Note, BillingInfo, Shipment, Transaction, CartDetails, ItemDetails
from .utils import create_instance_with_files, validate_catalog, save_item
from .signals import file_transferred
from decimal import Decimal
from django.template.loader import render_to_string

User = get_user_model()

load_dotenv()


def send_email(user, context, subject, template):
    message = render_to_string(template, context)
    send_mail(
        subject,
        message,
        os.getenv('EMAIL_HOST_USER'),
        [user.email],
        fail_silently=False,
        html_message=message
    )


catalog_item_fields = [
    'id', 'title', 'item_sku', 'description', 'short_description',
    'default_quantity', 'pricing_grid', 'thumbnail', 'preview_image', 'preview_file',
    'available_inventory', 'minimum_inventory', 'track_inventory_automatically',
    'restrict_orders_to_inventory', 'weight_per_piece_lb', 'weight_per_piece_oz',
    'exempt_from_shipping_charges', 'is_this_item_taxable', 'can_item_be_ordered',
    'details_page_per_layout', 'is_favorite', 'attributes', 'item_type'
]

online_proof_fields = [
    "name",
    "email_address",
    "created_at",
    "tracking_number",
    "proof_status",
    "recipient_name",
    "recipient_email",
    "project_title",
    "project_details",
    "proof_due_date",
    "additional_info",
    "files",
    "created_at"
]

general_fields = [
    'id', 'name', 'email_address', 'phone_number', 'address', 'fax_number',
    'company', 'city_state_zip', 'country', 'additional_details', 'portal',
    'files'
]

image_fields = general_fields + \
    ['preferred_mode_of_response', 'artwork_provided',
        'project_name', 'project_due_date']

customer_fields = ['id', 'company', 'address', 'city_state_zip',
                   'phone_number', 'fax_number', 'pay_tax',
                   'third_party_identifier', 'credit_balance', 'user_id']


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
        fields = ['path', 'url', 'file_size', 'file_name']

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


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'first_name', 'last_name', 'email_address', 'phone_number',
            'fax_number', 'company', 'address', 'address_line_2',
            'state', 'city', 'zip_code', 'status', 'send_notifications',
            'tracking_number', 'shipment_cost', 'created_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'type', 'description', 'created_at']

    def validate(self, data):
        if data['type'] == 'refund':
            content_type = self.context['content_type']
            object_id = self.context['object_id']
            if not Transaction.objects.filter(content_type=content_type, object_id=object_id, type='payment').exists():
                raise serializers.ValidationError(
                    {"type": "Refund cannot be made without an existing payment."})
        return data


class BillingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingInfo
        fields = [
            'first_name', 'last_name', 'email_address', 'phone_number',
            'fax_number', 'company', 'address', 'address_line_2',
            'state', 'city', 'zip_code', 'created_at'
        ]


class TitlePortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['title']


class QuoteRequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()

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


class NoteAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class NoteSerializer(serializers.ModelSerializer):
    author = NoteAuthorSerializer(read_only=True)

    class Meta:
        model = Note
        fields = ['id', 'content', 'created_at', 'author']
        read_only_fields = ['created_at', 'author']


class CreateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'content']


class RequestSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()
    notes = NoteSerializer(many=True, read_only=True)
    billing_info = BillingInfoSerializer()

    class Meta:
        model = Request
        fields = image_fields + ['this_is_an', 'status',
                                 'notes', 'billing_info', 'shipments', 'transactions']
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


class OnlineProofSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = OnlineProof
        fields = online_proof_fields
        read_only_fields = ['created_at']


class CreateOnlineProofSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = OnlineProof
        fields = online_proof_fields
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(OnlineProof, validated_data)


class FileTransferSerializer(serializers.ModelSerializer):
    shipments = ShipmentSerializer(many=True, read_only=True)
    billing_info = BillingInfoSerializer()
    transactions = TransactionSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type", "status", "notes", "billing_info", "shipments", "transactions"]
        read_only_fields = ['created_at']


class CreateFileTransferSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=True
    )

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(FileTransfer, validated_data)


def validate_status_transition(instance, new_status):
    # Define the allowed status progression
    allowed_transitions = {
        'New': ['Pending'],
        'Pending': ['New', 'Processing'],
        'Processing': ['New', 'Pending', 'Completed'],
        'Completed': ['New', 'Pending', 'Processing', 'Shipped'],
        'Shipped': ['New', 'Pending', 'Processing', 'Completed']
    }

    # Get the current instance's status
    if instance:
        current_status = instance.status

        # Check if the transition is valid
        if current_status in allowed_transitions and new_status not in allowed_transitions[current_status]:
            raise serializers.ValidationError(
                f"Invalid status transition from \
                    {current_status} to {new_status}."
                f"You can only change it to one of \
                    {allowed_transitions[current_status]}."
            )

    return new_status


class UpdateFileTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileTransfer
        fields = ['status']

    def validate_status(self, value):
        return validate_status_transition(self.instance, value)


class UpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['status']

    def validate_status(self, value):
        return validate_status_transition(self.instance, value)


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
        fields = ['id', 'name', 'email', 'company', 'fax_number',
                  'city_state_zip', 'address', 'phone_number']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email


class PortalCustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'username']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email

    def get_username(self, customer: Customer):
        return customer.user.username


class UpdateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(write_only=True)

    class Meta:
        model = Customer
        fields = [*customer_fields, 'groups', 'is_active', 'name']

    @transaction.atomic()
    def update(self, instance, validated_data):
        name = validated_data.pop('name')
        is_active = validated_data.pop('is_active')
        groups = validated_data.pop('groups')

        customer = super().update(instance, validated_data)

        if groups:
            customer.groups.set(groups)

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
        fields = [*customer_fields, 'groups', 'email',
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
        groups = validated_data.pop('groups', [])

        user = User.objects.create_user(
            email=email, password=password, name=name, username=username, is_active=is_active)
        customer = Customer.objects.create(user=user, **validated_data)

        subject = "Welcome to Walls Printing!"
        template = "email/welcome_email.html"
        context = {
            "user": user,
            "temporary_password": password,
            "login_url": os.getenv('CUSTOMER_LOGIN_URL')
        }

        send_email(user=user, context=context,
                   subject=subject, template=template)

        if groups:
            customer.groups.set(groups)

        return customer


class CustomerGroupSerializer(serializers.ModelSerializer):
    customers = SimpleCustomerSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()

    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers', "date_created", "members"]

    def get_members(self, customer_group: CustomerGroup):
        return customer_group.customers.count()


class PortalCustomerGroupSerializer(serializers.ModelSerializer):
    customers = PortalCustomerSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers',]


class CreateCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers']

    def validate_title(self, attrs):
        title = attrs.lower()
        if CustomerGroup.objects.filter(title__iexact=title).exists():
            raise serializers.ValidationError("Group name already exists")
        return attrs


class UpdateCustomerGroupSerializer(serializers.ModelSerializer):
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


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'title', 'content']


class UpdatePortalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContent
        fields = ['id', 'customer_groups', 'customers', 'everyone', 'content',
                  'display_in_site_navigation', 'catalogs', 'logo'
                  #   'logo', 'payment_proof', 'order_history', 'page_redirect',
                  #   'redirect_page', 'redirect_file', 'redirect_url', 'redirect_code'
                  #   'include_in_site_map', 'location',
                  ]
        logo = serializers.ImageField(required=False)

    def validate(self, data):
        customer_groups_data = data.get('customer_groups', [])
        customer_data = data.get('customers', [])
        catalogs = data.get('catalogs', [])
        everyone = data.get('everyone', None)
        # page_redirect = data.get('page_redirect', None)
        # redirect_page = data.get('redirect_page', None)
        # redirect_file = data.get('redirect_file', None)
        # redirect_url = data.get('redirect_url', None)

        # Validate customer group and everyone selection
        if (customer_groups_data or customer_data) and everyone:
            raise ValidationError(
                "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only."
            )

        portal_id = self.context['portal_id']
        portal = Portal.objects.prefetch_related(
            'customers', 'customer_groups').get(id=portal_id)
        portal_customers = set(portal.customers.values_list('id', flat=True))
        portal_customer_ids = set()
        for group in portal.customer_groups.all():
            portal_customer_ids.update(
                group.customers.values_list('id', flat=True))

        customer_ids = set(customer.id if hasattr(
            customer, 'id') else customer for customer in customer_data)
        if not customer_ids.issubset(portal_customers.union(portal_customer_ids)):
            raise ValidationError(
                "All selected customers must be part of the parent portal."
            )

        # Restrict customer groups to those in the parent portal
        portal_customer_groups = set(
            portal.customer_groups.values_list(flat=True))
        customer_group_ids = set(customer_group.id if hasattr(
            customer_group, 'id') else customer_group for customer_group in customer_groups_data)

        if not customer_group_ids.issubset(portal_customer_groups):
            raise ValidationError(
                "All selected customer groups must be part of the parent portal."
            )

        if not self.instance.can_have_catalogs and catalogs:
            raise ValidationError(
                {"catalogs": "You can't assign catalogs for this page."})

        # # Validate redirect fields based on page_redirect value
        # if page_redirect == 'no_redirect':
        #     if redirect_page or redirect_file or redirect_url or not data.get('redirect_code') in ['default', None]:
        #         raise ValidationError(
        #             "For 'no_redirect', 'redirect_page', 'redirect_file', 'redirect_url', and 'redirect_code' must be null."
        #         )
        # elif page_redirect == 'external':
        #     if not redirect_url:
        #         raise ValidationError(
        #             "For 'external', 'redirect_url' is required."
        #         )
        #     if redirect_page or redirect_file:
        #         raise ValidationError(
        #             "For 'external', 'redirect_page' and 'redirect_file' must be null."
        #         )
        # elif page_redirect == 'internal':
        #     if not redirect_page:
        #         raise ValidationError(
        #             "For 'internal', 'redirect_page' is required."
        #         )
        #     if redirect_file or redirect_url:
        #         raise ValidationError(
        #             "For 'internal', 'redirect_file' and 'redirect_url' must be null."
        #         )
        # elif page_redirect == 'file':
        #     if not redirect_file:
        #         raise ValidationError(
        #             "For 'file', 'redirect_file' is required."
        #         )
        #     if redirect_page or redirect_url:
        #         raise ValidationError(
        #             "For 'file', 'redirect_page' and 'redirect_url' must be null."
        #         )

        return data

    @transaction.atomic()
    def create(self, validated_data):
        portal_id = self.context['portal_id']
        customer_group_data = []
        customer_data = []
        customer_group_data = validated_data.pop('customer_groups', None)
        customer_data = validated_data.pop('customers', None)

        portal_content = PortalContent.objects.create(
            portal_id=portal_id, **validated_data)

        if customer_group_data:
            portal_content.customer_groups.set(customer_group_data)
        if customer_data:
            portal_content.customers.set(customer_data)

        return portal_content


class CreatePortalSerializer(serializers.ModelSerializer):
    # content = CreatePortalContentSerializer(many=True, required=False)
    copy_an_existing_portal = serializers.BooleanField(default=False)
    copy_from_portal_id = serializers.IntegerField(
        required=False, allow_null=True)
    copy_the_logo = serializers.BooleanField(default=False)
    same_permissions = serializers.BooleanField(required=False)
    same_catalogs = serializers.BooleanField(required=False)
    same_proofing_categories = serializers.BooleanField(required=False)
    catalog = serializers.CharField(required=False)
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
        model = Portal
        fields = ['id', 'title', 'logo', 'copy_an_existing_portal', 'copy_from_portal_id',
                  'same_permissions', 'copy_the_logo', 'same_catalogs', 'same_proofing_categories',
                  'customers', 'customer_groups', 'catalog',
                  ]

    def validate_title(self, value):
        if Portal.objects.filter(title__iexact=value).exists():
            if self.instance is None:
                raise serializers.ValidationError(
                    "A Portal with this title already exists.")
            else:
                if Portal.objects.get(title__iexact=value).id != self.instance.id:
                    raise serializers.ValidationError(
                        "A Portal with this title already exists.")
        return value

    def validate_catalog(self, value):
        if Catalog.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "Catalog already exists with title.")
        return value

    def validate(self, data):
        copy_an_existing_portal = data.get('copy_an_existing_portal', False)
        copy_the_logo = data.get('copy_the_logo', False)
        same_permissions = data.get('same_permissions', False)
        customers = data.get('customers', False)
        customer_groups = data.get('customer_groups', False)
        logo = data.get('logo', None)

        if not copy_an_existing_portal:
            invalid_fields = {
                field: data.get(field)
                for field in ['copy_from_portal_id', 'same_permissions', 'same_catalogs', 'same_proofing_categories', 'copy_the_logo']
                if data.get(field) is True
            }
            if invalid_fields:
                raise serializers.ValidationError(
                    {
                        field: f"Must be false when 'copy_an_existing_portal' is False."
                        for field in invalid_fields
                    }
                )
        else:
            if logo and copy_the_logo:
                raise serializers.ValidationError(
                    {
                        field: f"No need to specify the logo when you are copying a logo from a another portal"
                        for field in ['logo', 'copy_the_logo']
                    }
                )

            if same_permissions and (customers or customer_groups):
                raise serializers.ValidationError(
                    {
                        field: f"No need to specify the logo when you are copying a logo from a another portal"
                        for field in ['customer', 'copy_the_logo']
                    }
                )

        return data

    @transaction.atomic()
    def create(self, validated_data):
        catalog = validated_data.pop('catalog', None)
        copy_an_existing_portal = validated_data.pop(
            'copy_an_existing_portal', False)
        validated_data.pop('copy_the_logo', False)
        customers = validated_data.pop('customers', [])
        customer_groups = validated_data.pop('customer_groups', [])
        copy_from_portal_id = validated_data.pop('copy_from_portal_id', False)
        same_permissions = validated_data.pop('same_permissions', None)
        same_catalogs = validated_data.pop('same_catalogs', None)
        same_proofing_categories = validated_data.pop(
            'same_proofing_categories', None)
        portal = Portal.objects.create(**validated_data)

        if customer_groups and copy_from_portal_id:
            raise ValidationError(
                "You cannot specify both 'customer_groups' and 'copy_from_portal_id'. Choose one option."
            )

        if catalog:
            catalog = Catalog.objects.create(title=catalog)

        if copy_an_existing_portal:
            try:
                if None in [same_permissions, same_catalogs, same_proofing_categories]:
                    return ValueError('Neither same_permissions, same_catalogs nor same_proofing_categories is allowed to be null')
                source_portal = Portal.objects.prefetch_related(
                    'contents__customer_groups', 'contents__customers'
                ).get(id=copy_from_portal_id)

                customers = source_portal.customers.all()
                customer_groups = source_portal.customer_groups.all()
            except Portal.DoesNotExist:
                raise ValidationError(
                    {"copy_from_portal_id": "The portal to copy from does not exist."})

            portal_contents = []

            for source_content in source_portal.contents.all():
                portal_contents.append(PortalContent(
                    portal=portal,
                    everyone=source_content.everyone,
                    page=source_content.page,
                    title=source_content.title,
                    can_have_catalogs=source_content.can_have_catalogs,
                ))

            PortalContent.objects.bulk_create(portal_contents)
            created_portal_contents = PortalContent.objects.filter(
                portal=portal, title__in=[content.title for content in portal_contents])

            for portal_content, source_content in zip(created_portal_contents, source_portal.contents.all()):
                portal_content.customer_groups.set(
                    source_content.customer_groups.all())
                portal_content.customers.set(source_content.customers.all())

                if portal_content.can_have_catalogs and same_catalogs:
                    portal_content.catalogs.set(source_content.catalogs.all())
                elif portal_content.can_have_catalogs and catalog:
                    portal_content.catalogs.set([catalog])
        else:
            allowed_titles = ['Welcome', 'Online payments', 'Order approval',]
            existing_titles = PortalContent.objects.filter(
                portal=portal).values_list('title', flat=True)

            online_orders_content = [
                PortalContent(portal=portal, title='Online orders',
                              url='online-orders.html', can_have_catalogs=True)
            ]
            order_history_content = [
                PortalContent(portal=portal, title='Order history',
                              url='order-history.html', order_history=True)
            ]

            portal_contents = online_orders_content + order_history_content + [
                PortalContent(portal=portal, title=title,
                              url=f'{title.lower().replace(" ", "-")}.html')
                for title in allowed_titles
                if title not in existing_titles
            ]

            if portal_contents:
                PortalContent.objects.bulk_create(portal_contents)

            if catalog:
                created_portal_contents = PortalContent.objects.get(
                    portal=portal, can_have_catalogs=True)
                created_portal_contents.catalogs.set([catalog])

        portal.customers.set(customers)
        portal.customer_groups.set(customer_groups)
        return portal


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = [
            'id',
            'title',
            'parent_catalog',
            'specify_low_inventory_message',
            'recipient_emails',
            'subject',
            'message_text',
            'description',
            'display_items_on_same_page',
            'created_at',
        ]

    def validate_title(self, value):
        request = self.context['request']
        if Catalog.objects.filter(title__iexact=value).exists():
            if request.method == 'POST':
                raise serializers.ValidationError(
                    "A catalog with this title already exists.")
            elif request.method in ['PATCH', 'PUT']:
                if Catalog.objects.get(title__iexact=value).id != self.instance.id:
                    raise serializers.ValidationError(
                        "A catalog with this title already exists.")
        return value

    def validate_recipient_emails(self, value):
        """
        Validate the recipient_emails field.
        """
        if not value:
            return value

        emails = [email.strip() for email in value.split(',')]
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise serializers.ValidationError(
                    f"'{email}' is not a valid email address.")

        return value

    def validate(self, data):
        """
        Validate the fields related to 'specify_low_inventory_message'.
        """
        if data.get('specify_low_inventory_message'):
            if not data.get('recipient_emails'):
                raise serializers.ValidationError(
                    {"recipient_emails": "This field is required when specifying a low inventory message."})
            if not data.get('subject'):
                raise serializers.ValidationError(
                    {"subject": "This field is required when specifying a low inventory message."})
            if not data.get('message_text'):
                raise serializers.ValidationError(
                    {"message_text": "This field is required when specifying a low inventory message."})
        else:
            if data.get('recipient_emails') or data.get('subject') or data.get('message_text'):
                raise serializers.ValidationError(
                    "Low inventory message fields should not be filled if 'specify_low_inventory_message' is disabled.")
        return data


class SimpleCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = [
            'id',
            'title',
            'parent_catalog',
            'description',
            'display_items_on_same_page',
        ]


class ViewPortalContentCatalogSerializer(serializers.ModelSerializer):
    catalog = CatalogSerializer()

    class Meta:
        model = PortalContentCatalog
        fields = ['catalog', 'is_active', 'order_approval']


class PortalContentSerializer(serializers.ModelSerializer):
    customer_groups = PortalCustomerGroupSerializer(many=True, read_only=True)
    customers = PortalCustomerSerializer(many=True, read_only=True)
    can_user_access = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    catalogs = CatalogSerializer(many=True, read_only=True)
    logo = serializers.ImageField(required=False)
    # page = PageSerializer()
    # catalog_assignments = ViewPortalContentCatalogSerializer(many=True)

    class Meta:
        model = PortalContent
        fields = ['id', 'title',
                  'customer_groups', 'everyone', 'can_user_access', 'can_have_catalogs',
                  'customers', 'groups_count', 'user_count', 'catalogs', 'content', 'logo', 'payment_proof', 'order_history']

    def get_can_user_access(self, obj):
        return True
        request = self.context['request']
        user = request.user
        # user = User.objects.get(id=request.user.id)

        if user.is_staff:
            return True

        try:
            customer = Customer.objects.get(user=user)
            customer_id = customer.id
            customer_ids = obj.get_accessible_customers()

            return customer_id in customer_ids
        except Customer.DoesNotExist:
            return False

    def get_groups_count(self, portal_content: PortalContent):
        return portal_content.customer_groups.count()

    def get_user_count(self, portal_content: PortalContent):
        return portal_content.customers.count()


class PortalSerializer(serializers.ModelSerializer):
    contents = serializers.SerializerMethodField()
    can_user_access = serializers.SerializerMethodField()
    customer_groups = PortalCustomerGroupSerializer(many=True, read_only=True)
    customers = PortalCustomerSerializer(many=True, read_only=True)
    logo = serializers.ImageField(required=False)
    number_of_cart_items = serializers.SerializerMethodField()

    class Meta:
        model = Portal
        fields = ['id', 'title', 'contents', 'can_user_access',
                  'customers', 'customer_groups', 'created_at', 'logo', 'number_of_cart_items']

    def get_contents(self, obj: Portal):
        customer_id = self.context.get('customer_id')

        if not customer_id:
            return PortalContentSerializer(obj.contents.all(), many=True, context={'request': self.context['request']}).data

        filtered_content = [
            content for content in obj.contents.all()
            if content.everyone or customer_id in content.customers.values_list('id', flat=True) or
            any(customer_id in group.customers.values_list('id', flat=True)
                for group in content.customer_groups.all())
        ]
        return PortalContentSerializer(filtered_content, many=True, context={'request': self.context['request']}).data

    def get_can_user_access(self, obj):
        return True
    def get_number_of_cart_items(self, obj: Portal):
        customer_id = self.context.get('customer_id')

        carts = obj.cart_set.all().prefetch_related('items')
        if customer_id:
            carts = carts.filter(customer_id=customer_id)            
        
        return sum([cart.items.count() for cart in carts])


class PatchPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['title', 'customers', 'customer_groups', 'logo']


class BulkPortalContentCatalogSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        content_id = self.context['content_id']
        for item in validated_data:
            item['portal_content_id'] = content_id

        return PortalContentCatalog.objects.bulk_create([
            PortalContentCatalog(**item) for item in validated_data
        ])

    def validate(self, data):
        # Validate for duplicates in the incoming data
        seen_pairs = set()
        for item in data:
            pair = (self.context['content_id'], item['catalog'].id)
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    f"Duplicate portal_content-catalog pair found: {pair}."
                )
            seen_pairs.add(pair)

        # Validate for duplicates in the database
        existing_pairs = PortalContentCatalog.objects.filter(
            portal_content_id=self.context['content_id'],
            catalog__in=[item['catalog'] for item in data]
        ).values_list('portal_content_id', 'catalog_id')

        for pair in existing_pairs:
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    f"Duplicate pair found in the database: {pair}."
                )

        return data


class PortalContentCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContentCatalog
        fields = ['catalog', 'is_active', 'order_approval']
        list_serializer_class = BulkPortalContentCatalogSerializer

    def create(self, validated_data):
        portal_content_id = self.context['content_id']

        return PortalContentCatalog.objects.create(portal_content_id=portal_content_id, **validated_data)

    def validate(self, data):
        if PortalContentCatalog.objects.filter(
            portal_content_id=self.context['content_id'], catalog=data['catalog']
        ).exists():
            raise serializers.ValidationError(
                "This portal_content-catalog combination already exists."
            )
        return data


class MessageCenterSerializer(serializers.ModelSerializer):
    title_and_tracking = serializers.SerializerMethodField()

    class Meta:
        model = None  # This is a composite serializer, not tied to a single model
        fields = ['created_at', 'title_and_tracking', 'your_name', 'files']

    def get_title_and_tracking(self, obj):
        if isinstance(obj, FileTransfer):
            return 'Online File Transfer'
        elif isinstance(obj, Request):
            if obj.this_is_an == 'Estimate Request':
                return 'Estimate Request'
            else:
                return 'Online Order'
        # elif isinstance(obj, EcommerceOrder):
        #     return 'Ecommerce Order'
        elif isinstance(obj, ContactInquiry):
            return 'General Contact'
        else:
            return ''


class AttributeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeOption
        fields = [
            'id', 'option', 'alternate_display_text',
            'price_modifier_type', 'pricing_tiers',
        ]

    def create(self, validated_data):
        attribute_id = self.context['attribute_id']
        validated_data['item_attribute_id'] = attribute_id

        return super().create(validated_data)


class AttributeSerializer(serializers.ModelSerializer):
    options_data = serializers.JSONField(write_only=True, required=False)
    options = AttributeOptionSerializer(read_only=True, many=True)

    class Meta:
        model = Attribute
        fields = [
            'id', 'label', 'is_required', 'attribute_type',
            'max_length', 'pricing_tiers', 'price_modifier_scope',
            'price_modifier_type', 'options', 'options_data'
        ]

    def validate_options_data(self, options_data):
        options_data = options_data or []
        if options_data and not self.instance:
            for option_data in options_data:
                serializer = AttributeOptionSerializer(data=option_data)
                serializer.is_valid(raise_exception=True)

        return options_data

    def validate(self, attrs):
        attribute_type = attrs.get('attribute_type', 'text_field')
        max_length = attrs.get('max_length')
        options = attrs.get('options_data')
        pricing_tiers = attrs.get('pricing_tiers')
        price_modifier_type = attrs.get('price_modifier_type')

        if self.instance and options:
            raise serializers.ValidationError(
                {"options_data": "Options can only be set during creation"})

        select_list = ['checkboxes', 'radio_buttons', 'select_menu']

        if attribute_type == 'text_field' and not max_length:
            raise serializers.ValidationError(
                {"max_length": "Max length is required for text fields"})

        if attribute_type != 'text_field' and max_length:
            raise serializers.ValidationError(
                {"max_length": "Max length can only be set for text fields"})

        if attribute_type in select_list:
            if pricing_tiers:
                raise serializers.ValidationError(
                    {"pricing_tiers": "Pricing tiers can only be set for text fields, file upload and text areas types"})
            if price_modifier_type:
                raise serializers.ValidationError(
                    {"price_modifier_type": "Price modifier type can only be set for text fields, file upload and text areas types"})
        else:
            if options:
                raise serializers.ValidationError(
                    {"options": "Options can only be set for checkboxes, radio buttons, and select menus"})

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        options_data = validated_data.pop('options_data', [])
        self.validate_options_data(options_data)

        catalog_item_id = self.context['catalog_item_id']
        validated_data['catalog_item_id'] = catalog_item_id
        attribute = super().create(validated_data)

        options = [
            AttributeOption(item_attribute=attribute, **option_data)
            for option_data in options_data
        ]
        AttributeOption.objects.bulk_create(options)

        return attribute


class ItemDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDetails
        fields = ['id', 'title', 'name', 'email_address',
                  'phone_number', 'office_number', 'extension',
                    'description', 'created_at'
                  ]


class CartDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartDetails
        fields = ['id', 'title', 'name', 'email_address',
                  'phone_number', 'office_number', 'extension',
                    'description', 'created_at'
                  ]

    def create(self, validated_data):
        cart_item_id = self.context['cart_item_id']

        cart_item = CartItem.objects.filter(
            id=cart_item_id,
            catalog_item__can_be_edited=True
        ).first()

        if not cart_item:
            if not CartItem.objects.filter(id=cart_item_id).exists():
                raise serializers.ValidationError(
                    "No cart item with the given ID was found")
            else:
                raise serializers.ValidationError(
                    "This item in the cart cannot be edited")

        cart_details = CartDetails.objects.create(
            cart_item=cart_item, **validated_data)
        return cart_details


class CatalogItemSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    preview_image = serializers.SerializerMethodField()
    preview_file = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    catalog = SimpleCatalogSerializer()

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + \
            ['created_at', 'can_be_edited', 'catalog']

    def get_url(self, field):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not field:
            return None

        url = field.url
        if not field.url:
            return url

        if 'http' in url:
            return url

        return f"https://res.cloudinary.com/{cloud_name}/{url}"

    def get_preview_image(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_image)

    def get_preview_file(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_file)

    def get_thumbnail(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.thumbnail)


class CreateOrUpdateCatalogItemSerializer(serializers.ModelSerializer):
    preview_image = serializers.ImageField()
    thumbnail = serializers.ImageField()
    preview_file = serializers.FileField()
    attributes = AttributeSerializer(many=True, read_only=True)
    attribute_data = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + \
            ['attribute_data', 'can_be_edited', 'item_type']

    def validate_attribute_data(self, attributes_data):
        if attributes_data and self.instance:
            for attribute_data in attributes_data:
                serializer = AttributeSerializer(data=attribute_data)
                serializer.is_valid(raise_exception=True)
            return attributes_data

    def validate(self, attrs):
        attributes_data = attrs.pop('attribute_data', [])
        if self.instance and attributes_data:
            raise serializers.ValidationError(
                {"attribute_data": "Attribute data not allowed during updates"})

        catalog_id = self.context['catalog_id']
        if not Catalog.objects.filter(pk=catalog_id).exists():
            raise serializers.ValidationError(
                "No catalog with the given catalog_id was found")
        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        attributes_data = validated_data.pop('attribute_data', [])
        self.validate_attribute_data(attributes_data)
        catalog_id = self.context['catalog_id']
        catalog_item = CatalogItem.objects.create(
            catalog_id=catalog_id, **validated_data)

        options_to_bulk_create = []

        for attribute_data in attributes_data:
            options_data = attribute_data.pop('options', [])
            attribute = Attribute.objects.create(
                catalog_item=catalog_item, **attribute_data)

            attribute_options = [
                AttributeOption(item_attribute_id=attribute.id, **option_data)
                for option_data in options_data
            ]

            options_to_bulk_create += attribute_options

        AttributeOption.objects.bulk_create(options_to_bulk_create)

        return catalog_item

    @transaction.atomic()
    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attribute_data', [])
        # Validate attribute_data
        self.validate_attribute_data(attributes_data)

        for attribute_data in attributes_data:
            options_data = attribute_data.pop('options', [])
            attribute_id = attribute_data.get('id')
            if attribute_id:
                attribute = Attribute.objects.get(
                    id=attribute_id, catalog_item=instance)
                for key, value in attribute_data.items():
                    setattr(attribute, key, value)
                attribute.save()
                for option_data in options_data:
                    option_id = option_data.get('id')
                    if option_id:
                        option = AttributeOption.objects.get(
                            id=option_id, item_attribute=attribute)
                        for key, value in option_data.items():
                            setattr(option, key, value)
                        option.save()
                    else:
                        AttributeOption.objects.create(
                            item_attribute=attribute, **option_data)
            else:
                attribute = Attribute.objects.create(
                    catalog_item=instance, **attribute_data)
                for option_data in options_data:
                    AttributeOption.objects.create(
                        item_attribute=attribute, **option_data)

        return super().update(instance, validated_data)


class SimpleCatalogItemSerializer(serializers.ModelSerializer):
    catalog = SimpleCatalogSerializer()
    preview_image = serializers.SerializerMethodField()
    preview_file = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = CatalogItem
        fields = [
            'id', 'title', 'item_sku',
            'description', 'short_description', 'default_quantity',
            'thumbnail', 'preview_image', 'catalog',
            'preview_file', 'pricing_grid'
        ]

    def get_url(self, field):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not field:
            return None

        url = field.url
        if not field.url:
            return url

        if 'http' in url:
            return url

        return f"https://res.cloudinary.com/{cloud_name}/{url}"

    def get_preview_image(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_image)

    def get_preview_file(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_file)

    def get_thumbnail(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.thumbnail)


class CartItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()
    sub_total = serializers.SerializerMethodField()
    details = CartDetailsSerializer()

    class Meta:
        model = CartItem
        fields = ['id', 'catalog_item', 'quantity',
                  'sub_total', 'unit_price', 'details']

    def get_sub_total(self, cart_item: CartItem):
        pricing_grid = cart_item.catalog_item.pricing_grid
        quantity = cart_item.quantity
        item = next(
            (entry for entry in pricing_grid if entry["minimum_quantity"] == quantity), None)
        total_price = (quantity * item['unit_price']
                       ) if item else cart_item.sub_total
        return total_price


class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    customer = SimpleCustomerSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    customer_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price",
                  "customer_id", 'customer', 'portal']

    def validate_customer_id(self, value):
        if not Customer.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "No customer with the given customer_id")
        customer_id = self.context['customer_id']
        if customer_id and customer_id != value:
            raise serializers.ValidationError(
                "You can only create your own cart")
        return value

    def validate(self, attrs):
        customer_id = attrs.get('customer_id', None)
        portal = attrs.get('portal', None)

        customer = attrs.get('customer_id', None)
        user = User.objects.get(id=self.context['user_id'])
       
        if user.is_staff and not customer:
            raise serializers.ValidationError(
                {"customer_id": "A valid integer field is required"})

        if Cart.objects.filter(customer_id=customer_id, portal=portal).exists():
            raise serializers.ValidationError(
                "The customer already has an active cart for this portal")

        return attrs

    def get_total_price(self, cart: Cart):
        return sum(
            Decimal(
                cart_item.quantity * next(
                    (entry['unit_price'] for entry in cart_item.catalog_item.pricing_grid
                     if entry['minimum_quantity'] == cart_item.quantity),
                    0
                ) or cart_item.sub_total
            )
            for cart_item in cart.items.all()
        )


class AddCartItemSerializer(serializers.ModelSerializer):
    # catalog_item = serializers.IntegerField()

    # def validate_catalog_item_id(self, value):
    #     return validate_catalog_item_id(value)

    def validate(self, attrs):
        return validate_catalog(self.context, attrs, Cart, 'cart', self.instance)
    
    
    @transaction.atomic()
    def create(self, validated_data):
        return save_item(self.context, validated_data, CartItem, 'cart_id', self.instance)

    class Meta:
        model = CartItem
        fields = ["id", "catalog_item", "quantity"]


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]


class OrderItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'catalog_item', 'unit_price',
                  'quantity', 'sub_total', 'tax', 'status',
                  'created_at'
                ]


class CreateOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'catalog_item', 'quantity']

    def validate(self, attrs):
        return validate_catalog(self.context, attrs, Order, 'order', self.instance)

    def create(self, validated_data):
        validated_data['order_id'] = self.context['order_id']
        return super().create(validated_data)


class UpdateOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'tax', 'status']

    def validate(self, attrs):
        return validate_catalog(self.context, attrs, Order, 'order', self.instance)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer = SimpleCustomerSerializer()
    transactions = TransactionSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    tax = serializers.SerializerMethodField()
    shipment_cost = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'payment_status',
            'placed_at', 'items', 'name',
            'email_address', 'address', 'shipping_address',
            'phone_number', 'company', 'city_state_zip',
            'po_number', 'project_due_date', 'notes',
            'shipments', 'transactions', 'status',
            'tracking_number', 'tax', 'shipment_cost',
            'sub_total', 'total_paid', 'balance',
            "total_price"
        ]

    def get_sub_total(self, obj: Order):
        total_price = sum([item.sub_total for item in obj.items.all()])
        return total_price

    def get_tax(self, obj: Order):
        return sum([item.sub_total * (item.tax / 100) for item in obj.items.all()])

    def get_shipment_cost(self, obj: Order):
        return sum([shipment.shipment_cost for shipment in obj.shipments.all()])

    def get_total_paid(self, obj: Order):
        total_paid = sum([
            transaction.amount if transaction.type == 'payment' else (
                -1 * transaction.amount)
            for transaction in obj.transactions.all()
        ])
        return total_paid

    def get_total_price(self, obj: Order):
        return self.get_sub_total(obj) + self.get_tax(obj) + self.get_shipment_cost(obj)

    def get_balance(self, obj: Order):
        return self.get_total_price(obj) - self.get_total_paid(obj)


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status', 'status']


class CreateOrderSerializer(serializers.ModelSerializer):
    cart_id = serializers.UUIDField(write_only=True)
    auto_send_proof = serializers.BooleanField(default=False)

    class Meta:
        model = Order
        fields = [
            'cart_id', 'name', 'email_address',
            'address', 'shipping_address', 'phone_number',
            'company', 'city_state_zip', 'po_number',
            'project_due_date', 'auto_send_proof',
        ]

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError(
                {'cart_id': 'No cart with the given cart ID was found'})
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('The cart is empty')

        if self.context['customer'] and not Cart.objects.filter(customer=self.context['customer'], pk=cart_id).exists():
            raise serializers.ValidationError(
                'The cart does not belong to the customer')

        return cart_id

    def validate(self, attrs):
        cart_id = attrs.get('cart_id')
        cart_items = CartItem.objects.select_related(
            "catalog_item").filter(cart_id=cart_id)

        for item in cart_items:
            catalog_item = item.catalog_item
            quantity = item.quantity

            if not catalog_item.can_item_be_ordered:
                raise serializers.ValidationError(
                    f"{catalog_item.title} cannot be ordered.")
            if quantity > catalog_item.available_inventory:
                raise serializers.ValidationError(f"The quantity of\
                            {catalog_item.title} in the cart is more than the available inventory.")

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        auto_send_proof = validated_data.pop('auto_send_proof')
        cart_id = validated_data.pop('cart_id')
        cart_items = CartItem.objects.select_related(
            "catalog_item").filter(cart_id=cart_id)
        cart = Cart.objects.get(id=cart_id)

        order = Order.objects.create(customer=cart.customer, **validated_data)

        order_items = []
        catalog_items = []

        for item in cart_items:
            catalog_item = item.catalog_item
            quantity = item.quantity

            if catalog_item.restrict_orders_to_inventory:
                catalog_item.available_inventory -= quantity
                catalog_items.append(catalog_item)

            if catalog_item.track_inventory_automatically and catalog_item.available_inventory < catalog_item.minimum_inventory:
                catalog = catalog_item.catalog
                if catalog.specify_low_inventory_message:
                    send_mail(
                        subject=catalog.subject,
                        message=catalog.message_text,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[
                            email.strip() for email in catalog.recipient_emails.split(",")],
                        fail_silently=False,
                    )

            unit_price = next(
                (entry['unit_price'] for entry in item.catalog_item.pricing_grid if entry['minimum_quantity'] == item.quantity), item.unit_price)
            sub_total = item.quantity * unit_price

            order_items.append(OrderItem(
                order=order,
                catalog_item=item.catalog_item,
                sub_total=sub_total,
                unit_price=unit_price,
                quantity=item.quantity
            ))

        if catalog_items:
            CatalogItem.objects.bulk_update(
                catalog_items, ['available_inventory'])
        if order_items:
            OrderItem.objects.bulk_create(order_items)

        Cart.objects.filter(pk=cart_id).delete()

        if auto_send_proof:
            subject = f"Your Walls Printing Order Confirmation - {order.po_number}"
            message = render_to_string('email/order_confirmation.html', {
                'customer_name': order.name,
                'invoice_number': order.po_number,
                'po_number': order.po_number,
                'payment_submission_link': 'your_payment_submission_link_here'
            })
            send_mail(
                subject=subject,
                message='',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[order.email_address],
                html_message=message,
                fail_silently=False,
            )

        return order


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = [
            'id',
            'name',
            'email_address',
            'payment_method',
            'invoice_number',
            'po_number',
            'amount',
            'additional_instructions',
        ]

    def validate_po_number(self, value):
        customer = self.context['customer']

        if not value:
            return value
        if not re.match(r'^[a-zA-Z0-9]*$', value):
            raise serializers.ValidationError(
                "PO number can only contain letters and numbers.")
        if not Order.objects.filter(customer=customer, po_number=value).exists():
            raise serializers.ValidationError("The PO# submitted is invalid")

        return value

    def validate_payment_method(self, value):
        """
        Ensure the selected payment method is valid.
        """
        if value not in dict(OnlinePayment.PAYMENT_METHOD_CHOICES).keys():
            raise serializers.ValidationError("Invalid payment method.")
        return value

    def create(self, validated_data):
        payment = super().create(validated_data)

        # Send email to the customer
        subject = f"Payment Proof Submitted Successfully - Order {payment.po_number}"
        message = render_to_string('email/payment_confirmation.html', {
            'customer_name': payment.name,
            'po_number': payment.po_number,
            'amount': payment.amount,
        })
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[payment.email_address],
            html_message=message,
            fail_silently=False,
        )

        return payment


class FileExchangeSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = FileExchange
        fields = [
            "name",
            "email_address",
            "recipient_name",
            "recipient_email",
            "details",
            "file",
            "file_size",
            "created_at"
        ]

    def save(self, **kwargs):
        file_transfer = super().save(**kwargs)
        file_transferred.send_robust(
            self.__class__, request=self.context['request'], file_transfer=file_transfer)
        return file_transfer


class CopyCatalogSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    copy_items = serializers.BooleanField(default=False)

    def validate_title(self, value):
        if Catalog.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A catalog with this title already exists.")
        return value


class CopyCatalogItemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    catalog = serializers.PrimaryKeyRelatedField(
        queryset=Catalog.objects.all())

    def validate_title(self, value):
        if CatalogItem.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A catalog item with this title already exists.")
        return value


class CopyPortalSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    copy_the_logo = serializers.BooleanField(default=False)
    same_permissions = serializers.BooleanField(default=False)
    same_catalogs = serializers.BooleanField(default=False)
    same_proofing_categories = serializers.BooleanField(default=False)
    logo = serializers.ImageField(required=False, allow_null=True)
    catalog = serializers.CharField(max_length=255, required=False)
    new_proofing_category = serializers.CharField(
        max_length=255, required=False)
    customers = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), many=True, required=False)
    customer_groups = serializers.PrimaryKeyRelatedField(
        queryset=CustomerGroup.objects.all(), many=True, required=False)

    def validate_title(self, value):
        if Portal.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A portal with this title already exists.")
        return value

    def validate(self, data):
        if data['copy_the_logo'] and data.get('logo'):
            raise serializers.ValidationError(
                "You cannot select both 'copy_the_logo' and provide a 'logo'.")

        if data['same_catalogs'] and data.get('catalog'):
            raise serializers.ValidationError(
                "You cannot select both 'same_catalogs' and provide a 'catalog'.")
        if not data['same_catalogs'] and not data.get('catalog'):
            raise serializers.ValidationError(
                "You must provide a 'catalog' if 'same_catalogs' is false.")
        if data.get('catalog') and Catalog.objects.filter(title__iexact=data['catalog']).exists():
            raise serializers.ValidationError(
                "A catalog with this title already exists.")

        if data['same_proofing_categories'] and data.get('new_proofing_category'):
            raise serializers.ValidationError(
                "You cannot select both 'same_proofing_categories' and provide a 'new_proofing_category'.")
        if not data['same_proofing_categories'] and not data.get('new_proofing_category'):
            raise serializers.ValidationError(
                "You must provide a 'new_proofing_category' if 'same_proofing_categories' is false.")

        if data['same_permissions'] and (data.get('customers') or data.get('customer_groups')):
            raise serializers.ValidationError(
                "You cannot provide 'customers' or 'customer_groups' when 'same_permissions' is true.")

        return data
