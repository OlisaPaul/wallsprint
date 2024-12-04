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
from .models import AttributeOption, Attribute, Cart, CartItem, Catalog, CatalogItem, ContactInquiry, HTMLFile, OrderItem, Portal, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, PortalContent, Order, OrderItem
from .utils import create_instance_with_files

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
        fields = ['id', 'name', 'email', 'company', 'fax_number',
                  'city_state_zip', 'address', 'phone_number']

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
                  'customer_groups', 'everyone', 'can_user_access',
                  'customers', 'groups_count', 'user_count',]

    def get_can_user_access(self, obj):
        request = self.context['request']
        user = request.user
        user = User.objects.get(id=request.user.id)

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


class CreatePortalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContent
        fields = ['id', 'html_file', 'location',
                  'page_redirect', 'include_in_site_map', 'display_in_site_navigation',
                  'customer_groups', 'customers', 'everyone'
                  ]

    def create(self, validated_data):
        portal_id = self.context['portal_id']
        customer_group_data = []
        customer_data = []
        everyone = validated_data.get('everyone')

        customer_group_data = validated_data.pop('customer_groups', None)
        customer_data = validated_data.pop('customers', None)

        is_customer_or_customer_data = customer_group_data or customer_data

        if is_customer_or_customer_data and everyone:
            raise ValidationError(
                "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only.")

        portal_content = PortalContent.objects.create(
            portal_id=portal_id, **validated_data)

        if customer_group_data:
            portal_content.customer_groups.set(customer_group_data)
        if customer_data:
            portal_content.customers.set(customer_data)

        return portal_content


class PortalSerializer(serializers.ModelSerializer):
    content = PortalContentSerializer(many=True)
    can_user_access = serializers.SerializerMethodField()

    class Meta:
        model = Portal
        fields = ['id', 'title', 'content', 'can_user_access',
                  'customers', 'customer_groups']

    def get_can_user_access(self, obj):
        request = self.context['request']
        user = request.user
        user = User.objects.get(id=request.user.id)

        if user.is_staff:
            return True

        try:
            customer = Customer.objects.get(user=user)
            customer_id = customer.id
            customer_ids = obj.get_accessible_customers()

            return customer_id in customer_ids
        except Customer.DoesNotExist:
            return False


class CreatePortalSerializer(serializers.ModelSerializer):
    # content = CreatePortalContentSerializer(many=True, required=False)
    copy_an_existing_portal = serializers.BooleanField(default=False)
    copy_from_portal_id = serializers.IntegerField(
        required=False, allow_null=True)
    copy_the_logo = serializers.BooleanField(default=False)
    same_permissions = serializers.BooleanField(required=False)
    same_catalogs = serializers.BooleanField(required=False)
    same_proofing_categories = serializers.BooleanField(required=False)
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
                  'customers', 'customer_groups',
                  ]

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
                    html_file=source_content.html_file,
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
        ]

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
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price"]

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
                {'cart_id':'No cart with the given cart ID was found'})
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('The cart is empty')
        return cart_id

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            cart_items = CartItem.objects.select_related(
                "catalog_item").filter(cart_id=cart_id)

            customer = Customer.objects.get(
                user_id=self.context['user_id'])
            order = Order.objects.create(customer=customer)

            order_items = [
                OrderItem(
                    order=order,
                    catalog_item=item.catalog_item,
                    unit_price= item.quantity * next(
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
