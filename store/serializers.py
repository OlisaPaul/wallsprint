import csv
import os
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
from .models import AttributeOption, Attribute, Cart, CartItem, Catalog, CatalogItem, ContactInquiry, FileExchange, Page, OnlinePayment, OnlineProof, OrderItem, Portal, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, PortalContent, Order, OrderItem, PortalContentCatalog, Note, BillingInfo, Shipment, Transaction
from .utils import create_instance_with_files
from .signals import file_transferred

User = get_user_model()

load_dotenv()

catalog_item_fields = [
    'id', 'title', 'item_sku', 'description', 'short_description',
    'default_quantity', 'pricing_grid', 'thumbnail', 'preview_image', 'preview_file',
    'available_inventory', 'minimum_inventory', 'track_inventory_automatically',
    'restrict_orders_to_inventory', 'weight_per_piece_lb', 'weight_per_piece_oz',
    'exempt_from_shipping_charges', 'is_this_item_taxable', 'can_item_be_ordered',
    'details_page_per_layout', 'attributes'
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
        fields = ['path', 'url', 'file_size']

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
            'tracking_number', 'shipment_cost'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['amount', 'type', 'description']

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
            'state', 'city', 'zip_code'
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

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email


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


class CreatePortalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContent
        fields = ['id', 'title', 'location',
                  'page_redirect', 'include_in_site_map', 'display_in_site_navigation',
                  'customer_groups', 'customers', 'everyone', 'content', 'logo', 'payment_proof', 'order_history',
                  'redirect_page', 'redirect_file', 'redirect_url', 'redirect_code'
                  ]

    def validate(self, data):
        customer_group_data = data.get('customer_groups', [])
        customer_data = data.get('customers', [])
        everyone = data.get('everyone', None)
        page_redirect = data.get('page_redirect', None)
        redirect_page = data.get('redirect_page', None)
        redirect_file = data.get('redirect_file', None)
        redirect_url = data.get('redirect_url', None)
        
        # Validate customer group and everyone selection
        if (customer_group_data or customer_data) and everyone:
            raise ValidationError(
                "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only."
            )

        # Restrict customers to those in the parent portal
        portal_id = self.context['portal_id']
        portal = Portal.objects.prefetch_related('customers', 'customer_groups').get(id=portal_id)
        portal_customers = set(portal.customers.values_list('id', flat=True))
        portal_customer_ids = set()
        for group in portal.customer_groups.all():
            portal_customer_ids.update(group.customers.values_list('id', flat=True))

        customer_ids = set(customer.id if hasattr(customer, 'id') else customer for customer in customer_data)
        if not customer_ids.issubset(portal_customers.union(portal_customer_ids)):
            raise ValidationError(
                "All selected customers must be part of the parent portal."
            )

        # Restrict customer groups to those in the parent portal
        portal_customer_groups = set(
            portal.customer_groups.values_list('id', flat=True))
        customer_group_ids = set(customer_group_data)
        if not customer_group_ids.issubset(portal_customer_groups):
            raise ValidationError(
                "All selected customer groups must be part of the parent portal."
            )

        # Validate redirect fields based on page_redirect value
        if page_redirect == 'no_redirect':
            if redirect_page or redirect_file or redirect_url or not data.get('redirect_code') in ['default', None]:
                raise ValidationError(
                    "For 'no_redirect', 'redirect_page', 'redirect_file', 'redirect_url', and 'redirect_code' must be null."
                )
        elif page_redirect == 'external':
            if not redirect_url:
                raise ValidationError(
                    "For 'external', 'redirect_url' is required."
                )
            if redirect_page or redirect_file:
                raise ValidationError(
                    "For 'external', 'redirect_page' and 'redirect_file' must be null."
                )
        elif page_redirect == 'internal':
            if not redirect_page:
                raise ValidationError(
                    "For 'internal', 'redirect_page' is required."
                )
            if redirect_file or redirect_url:
                raise ValidationError(
                    "For 'internal', 'redirect_file' and 'redirect_url' must be null."
                )
        elif page_redirect == 'file':
            if not redirect_file:
                raise ValidationError(
                    "For 'file', 'redirect_file' is required."
                )
            if redirect_page or redirect_url:
                raise ValidationError(
                    "For 'file', 'redirect_page' and 'redirect_url' must be null."
                )

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
            Catalog.objects.create(title=catalog)

        if copy_an_existing_portal:
            try:
                if None in [same_permissions, same_catalogs, same_proofing_categories]:
                    return ValueError('Neither same_permissions, same_catalogs nor same_proofing_categories is allowed to be null')
                source_portal = Portal.objects.prefetch_related(
                    'content__customer_groups', 'content__customers'
                ).get(id=copy_from_portal_id)

                customers = source_portal.customers.all()
                customer_groups = source_portal.customer_groups.all()
            except Portal.DoesNotExist:
                raise ValidationError(
                    {"copy_from_portal_id": "The portal to copy from does not exist."})

            for source_content in source_portal.content.all():

                portal_content = PortalContent.objects.create(
                    portal=portal,
                    everyone=source_content.everyone,
                    page=source_content.page,
                )

                portal_content.customer_groups.set(
                    source_content.customer_groups.all())
                portal_content.customers.set(source_content.customers.all())

        # for content in content_data:

        #     customer_group_data = []
        #     customer_data = []
        #     everyone = content.get('everyone')

        #     customer_group_data = content.pop('customer_groups', None)
        #     customer_data = content.pop('customers', None)

        #     is_customer_or_customer_data = customer_group_data or customer_data

        #     if is_customer_or_customer_data and everyone:
        #         raise ValidationError(
        #             "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only.")

        #     portal_content = PortalContent.objects.create(
        #         portal=portal, **content)

        #     if customer_group_data:
        #         portal_content.customer_groups.set(customer_group_data)

        #     if customer_data:
        #         portal_content.customers.set(customer_data)

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
    # page = PageSerializer()
    catalog_assignments = ViewPortalContentCatalogSerializer(many=True)

    class Meta:
        model = PortalContent
        fields = ['id', 'title',
                  'customer_groups', 'everyone', 'can_user_access',
                  'customers', 'groups_count', 'user_count', 'catalog_assignments', 'content', 'logo', 'payment_proof', 'order_history']

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
    content = serializers.SerializerMethodField()
    # content = PortalContentSerializer(many=True, read_only=True)
    can_user_access = serializers.SerializerMethodField()
    customer_groups = PortalCustomerGroupSerializer(many=True, read_only=True)
    customers = PortalCustomerSerializer(many=True, read_only=True)

    class Meta:
        model = Portal
        fields = ['id', 'title', 'content', 'can_user_access',
                  'customers', 'customer_groups', 'created_at']
        
    def get_content(self, obj:PortalContent):
        customer_id = self.context.get('customer_id')
        
        if not customer_id:
            return PortalContentSerializer(obj.content.all(), many=True, context={'request': self.context['request']}).data

        filtered_content = [
            content for content in obj.content.all()
            if content.everyone or customer_id in content.customers.values_list('id', flat=True) or 
            any(customer_id in group.customers.values_list('id', flat=True) for group in content.customer_groups.all())
        ]
        return PortalContentSerializer(filtered_content, many=True, context={'request': self.context['request']}).data

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
        fields = ['id', 'option', 'alternate_display_text',
                  'price_modifier_type', 'pricing_tiers']


class AttributeSerializer(serializers.ModelSerializer):
    options = AttributeOptionSerializer(many=True)

    class Meta:
        model = Attribute
        fields = [
            'id', 'label', 'is_required', 'attribute_type', 'max_length',
            'pricing_tiers', 'price_modifier_scope', 'price_modifier_type', 'options'
        ]


class CatalogItemSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + ['created_at']


class CreateOrUpdateCatalogItemSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    attribute_data = AttributeSerializer(
        many=True, write_only=True, required=False)

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + ['attribute_data']

    def create(self, validated_data):
        catalog_id = self.context['catalog_id']
        attributes_data = validated_data.pop('attribute_data', [])
        catalog_item = CatalogItem.objects.create(
            catalog_id=catalog_id, **validated_data)
        for attribute_data in attributes_data:
            options_data = attribute_data.pop('options', [])
            attribute = Attribute.objects.create(
                catalog_item=catalog_item, **attribute_data)
            for option_data in options_data:
                AttributeOption.objects.create(
                    item_attribute=attribute, **option_data)
        return catalog_item

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attribute_data', [])
        instance.title = validated_data.get('title', instance.title)
        instance.parent_catalog = validated_data.get(
            'parent_catalog', instance.parent_catalog)
        instance.mark_as_favorite = validated_data.get(
            'mark_as_favorite', instance.mark_as_favorite)
        instance.item_sku = validated_data.get('item_sku', instance.item_sku)
        instance.description = validated_data.get(
            'description', instance.description)
        instance.short_description = validated_data.get(
            'short_description', instance.short_description)
        instance.default_quantity = validated_data.get(
            'default_quantity', instance.default_quantity)
        instance.pricing_grid = validated_data.get(
            'pricing_grid', instance.pricing_grid)
        instance.thumbnail = validated_data.get(
            'thumbnail', instance.thumbnail)
        instance.preview_image = validated_data.get(
            'preview_image', instance.preview_image)
        instance.available_inventory = validated_data.get(
            'available_inventory', instance.available_inventory)
        instance.minimum_inventory = validated_data.get(
            'minimum_inventory', instance.minimum_inventory)
        instance.track_inventory_automatically = validated_data.get(
            'track_inventory_automatically', instance.track_inventory_automatically)
        instance.restrict_orders_to_inventory = validated_data.get(
            'restrict_orders_to_inventory', instance.restrict_orders_to_inventory)
        instance.weight_per_piece_lb = validated_data.get(
            'weight_per_piece_lb', instance.weight_per_piece_lb)
        instance.weight_per_piece_oz = validated_data.get(
            'weight_per_piece_oz', instance.weight_per_piece_oz)
        instance.exempt_from_shipping_charges = validated_data.get(
            'exempt_from_shipping_charges', instance.exempt_from_shipping_charges)
        instance.is_this_item_taxable = validated_data.get(
            'is_this_item_taxable', instance.is_this_item_taxable)
        instance.can_item_be_ordered = validated_data.get(
            'can_item_be_ordered', instance.can_item_be_ordered)
        instance.details_page_per_layout = validated_data.get(
            'details_page_per_layout', instance.details_page_per_layout)
        instance.save()

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

        return instance


class SimpleCatalogItemSerializer(serializers.ModelSerializer):
    catalog = SimpleCatalogSerializer()

    class Meta:
        model = CatalogItem
        fields = [
            'id', 'title', 'item_sku', 'description', 'short_description',
            'default_quantity', 'thumbnail', 'preview_image', 'catalog'
        ]


class CartItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()
    sub_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'catalog_item', 'quantity', 'sub_total']

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
        fields = ["id", "items", "total_price", "customer_id", 'customer']

    def validate_customer_id(self, value):
        if not Customer.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "No customer with the given customer_id")

        if Cart.objects.filter(customer_id=value).exists():
            raise serializers.ValidationError(
                "The customer already has an active cart")

        return value

    def validate(self, attrs):
        customer = attrs.get('customer_id', None)
        user = User.objects.get(id=self.context['user_id'])
        is_staff = user.is_staff

        if is_staff and not customer:
            raise serializers.ValidationError(
                {"customer_id": "A valid integer field is required"})

        return attrs

    def get_total_price(self, cart: Cart):
        return sum(
            (
                cart_item.quantity * next(
                    (entry['unit_price'] for entry in cart_item.catalog_item.pricing_grid
                     if entry['minimum_quantity'] == cart_item.quantity),
                    0
                ) or cart_item.sub_total
            )
            for cart_item in cart.items.all()
        )


class AddCartItemSerializer(serializers.ModelSerializer):
    catalog_item_id = serializers.IntegerField()

    def validate_catalog_item_id(self, value):
        if not CatalogItem.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "No catalog_item with the given ID")
        return value

    def validate(self, attrs):
        catalog_item_id = attrs.get('catalog_item_id')
        quantity = attrs.get('quantity')

        try:
            catalog_item = CatalogItem.objects.get(pk=catalog_item_id)
        except CatalogItem.DoesNotExist:
            raise serializers.ValidationError("Invalid catalog item ID.")

        pricing_grid = catalog_item.pricing_grid
        if not isinstance(pricing_grid, list):
            raise serializers.ValidationError(
                "No pricing grid for this catalog item"
            )
        if not any(entry["minimum_quantity"] == quantity for entry in pricing_grid):
            raise serializers.ValidationError(
                {"quantity": "The quantity provided is not in the pricing grid."}
            )
        return attrs

    def save(self, **kwargs):
        cart_id = self.context["cart_id"]
        catalog_item_id = self.validated_data['catalog_item_id']
        quantity = self.validated_data['quantity']
        catalog_item = CatalogItem.objects.get(pk=catalog_item_id)

        pricing_grid = catalog_item.pricing_grid
        item = next(
            (entry for entry in pricing_grid if entry["minimum_quantity"] == quantity), None)
        sub_total = item['minimum_quantity'] * item['unit_price']
        self.validated_data['sub_total'] = sub_total

        try:
            cart_item = CartItem.objects.get(
                cart_id=cart_id, catalog_item_id=catalog_item_id, quantity=quantity)
            cart_item.quantity += quantity
            cart_item.sub_total += sub_total
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(
                cart_id=cart_id, **self.validated_data)

        return self.instance

    class Meta:
        model = CartItem
        fields = ["id", "catalog_item_id", "quantity"]


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]


class OrderItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'catalog_item', 'unit_price', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = SimpleCustomerSerializer()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'payment_status', 'placed_at', "items"]


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status']


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError(
                {'cart_id': 'No cart with the given cart ID was found'})
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('The cart is empty')
        return cart_id

    @transaction.atomic()
    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            cart_items = CartItem.objects.select_related(
                "catalog_item").filter(cart_id=cart_id)
            cart = Cart.objects.get(id=cart_id)
            print(cart.customer_id)

            order = Order.objects.create(customer=cart.customer)

            order_items = [
                OrderItem(
                    order=order,
                    catalog_item=item.catalog_item,
                    unit_price=item.quantity * next(
                        (entry['unit_price'] for entry in item.catalog_item.pricing_grid
                         if entry['minimum_quantity'] == item.quantity),
                        0
                    ) or item.sub_total,
                    quantity=item.quantity
                ) for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            Cart.objects.filter(pk=cart_id).delete()

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

    def validate_payment_method(self, value):
        """
        Ensure the selected payment method is valid.
        """
        if value not in dict(OnlinePayment.PAYMENT_METHOD_CHOICES).keys():
            raise serializers.ValidationError("Invalid payment method.")
        return value


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
    same_permissions
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
