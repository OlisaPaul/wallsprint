import re
from uuid import uuid4
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField
import datetime


def validate_pricing_grid(value):
    if not isinstance(value, list):
        raise ValidationError("The pricing_grid must be a list.")

    for tier in value:
        if not isinstance(tier, dict):
            raise ValidationError("Each pricing tier must be a dictionary.")
        if set(tier.keys()) != {'minimum_quantity', 'unit_price'}:
            raise ValidationError(
                "Each pricing tier must only contain 'minimum_quantity' and 'unit_price' as keys."
            )
        if 'minimum_quantity' not in tier or 'unit_price' not in tier:
            raise ValidationError(
                "Each pricing tier must contain 'minimum_quantity' and 'unit_price'.")
        if not isinstance(tier['minimum_quantity'], int) or tier['minimum_quantity'] <= 0:
            raise ValidationError(
                "The 'minimum_quantity' in each pricing tier must be a positive integer.")
        if not isinstance(tier['unit_price'], (int, float)) or tier['unit_price'] < 0:
            raise ValidationError(
                "The 'unit_price' in each pricing tier must be a non-negative number.")


def validate_number(value):
    if not re.match(r'^\+?[\d\s\-\(\)]{7,20}$', value):
        raise ValidationError("Enter a valid fax number.")


def validate_phone_number(value):
    if not re.match(r'^\+?[\d\s\-\(\)]{7,20}$', value):
        raise ValidationError("Enter a valid phone number.")


class CommonFields(models.Model):
    name = models.CharField(max_length=255)
    email_address = models.EmailField()
    phone_number = models.CharField(
        max_length=255, blank=True, null=True, validators=[validate_phone_number])
    address = models.CharField(max_length=255, blank=True, null=True)
    fax_number = models.CharField(
        max_length=255, blank=True, null=True, validators=[validate_number])
    company = models.CharField(max_length=255, blank=True, null=True)
    city_state_zip = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)
    portal = models.ForeignKey("Portal", on_delete=models.SET_NULL, null=True)
    preferred_mode_of_response = models.CharField(
        max_length=50,
        choices=[
            ('Email', 'Email'),
            ('Phone', 'Phone'),
            ('Fax', 'Fax')
        ],
        blank=True,
        null=True
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
    files = GenericRelation(
        "File", related_query_name='quote_requests', null=True)
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
        blank=True,
        null=True
    )
    project_name = models.CharField(max_length=255, null=True)
    project_due_date = models.DateField(default=datetime.date.today)
    additional_details = models.TextField(blank=True, null=True)
    this_is_an = models.CharField(
        max_length=50,
        choices=[
            ('Order Request', 'Order Request'),
            ('Quote Request', 'Quote Request'),
        ],
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.name} - {self.project_name}"


class OnlineProof(models.Model):
    name = models.CharField(max_length=255)
    email_address = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    tracking_number = models.CharField(max_length=255, blank=True, null=True)
    proof_status = models.CharField(max_length=255)
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField()
    project_title = models.CharField(max_length=255, blank=True, null=True)
    project_details = models.TextField(blank=True, null=True)
    proof_due_date = models.DateField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    files = GenericRelation(
        "File", related_query_name='online_proofs', null=True)

    def __str__(self):
        return f"Proof Approval for {self.project_title or 'Untitled Project'} - {self.recipient_name}"

    class Meta:
        permissions = [
            ('online_proofing', "Online Proofing")
        ]


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
    additional_details = models.TextField(blank=True, null=True)
    you_are_a = models.CharField(
        max_length=50,
        choices=[
            ('New Customer', 'New Customer'),
            ('Current Customer', 'Current Customer'),
        ],
    )
    files = GenericRelation(
        "File", related_query_name='quote_requests', null=True)
    this_is_an = models.CharField(
        max_length=50,
        choices=[
            ('Order Request', 'Order Request'),
            ('Estimate Request', 'Estimate Request'),
        ],
    )


class File(models.Model):
    path = CloudinaryField("auto", blank=True, null=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"File related to {self.content_object}"


class Customer(models.Model):
    company = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True)
    city_state_zip = models.CharField(max_length=255, null=True)
    phone_number = models.CharField(
        max_length=255, null=True, validators=[validate_phone_number])
    fax_number = models.CharField(
        max_length=255, null=True, validators=[validate_number])
    pay_tax = models.BooleanField(default=False)
    third_party_identifier = models.CharField(max_length=255, null=True)
    credit_balance = models.DecimalField(
        max_digits=9, decimal_places=2, default=0)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        permissions = [
            ('customers', "Customer Service")
        ]

    def __str__(self):
        return self.user.name


class CustomerGroup(models.Model):
    title = models.CharField(max_length=255, unique=True)
    customers = models.ManyToManyField(Customer, related_name='groups')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FileTransfer(CommonFields):
    additional_details = models.TextField(blank=True, null=True)
    file_type = models.CharField(
        max_length=50,
        choices=[
            ('PC', 'PC'),
            ('MACINTOSH', 'MACINTOSH'),
        ],
    )
    files = GenericRelation(
        "File", related_query_name='quote_requests', null=True)
    application_type = models.CharField(
        max_length=255,
        choices=[
            ('MULTIPLE', 'MULTIPLE (COMPRESSED)'),
            ('ACROBAT', 'ACROBAT (PDF)'),
            ('CORELDRAW', 'CORELDRAW'),
            ('EXCEL', 'EXCEL'),
            ('FONTS', 'FONTS'),
            ('FREEHAND', 'FREEHAND'),
            ('ILLUSTRATOR', 'ILLUSTRATOR'),
            ('INDESIGN', 'INDESIGN'),
            ('PAGEMAKER', 'PAGEMAKER'),
            ('PHOTOSHOP', 'PHOTOSHOP'),
            ('POWERPOINT', 'POWERPOINT'),
            ('PUBLISHER', 'PUBLISHER'),
            ('WORD', 'WORD'),
            ('QUARKXPRESS', 'QUARKXPRESS'),
            ('OTHER', 'OTHER'),
        ],
    )
    other_application_type = models.CharField(
        max_length=255, blank=True, null=True)

    class Meta:
        permissions = [
            ('transfer_files', "Transfer Files")
        ]


class Portal(models.Model):
    title = models.CharField(max_length=255)
    logo = models.FileField(upload_to='logos/', null=True)
    copy_from_portal_id = models.IntegerField(null=True, blank=True)
    customers = models.ManyToManyField(
        Customer, blank=True, related_name='portals')
    customer_groups = models.ManyToManyField(
        CustomerGroup, blank=True, related_name='portals')

    def __str__(self):
        return self.title

    class Meta:
        permissions = [
            ('portals', "Portals")
        ]

    def get_accessible_customers(self):
        """
        Returns the customers who can access the content.
        If the content is public, all customers have access.
        """
        direct_customers = self.customers.values_list('id', flat=True)
        group_customers = Customer.objects.filter(
            groups__in=self.customer_groups.all()).values_list('id', flat=True)

        accessible_customer_ids = direct_customers.union(group_customers)
        return accessible_customer_ids


class Page(models.Model):
    content = models.TextField(default='')
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class PortalSection(models.Model):
    portal = models.ForeignKey(
        Portal, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    location = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    display_in_site_navigation = models.BooleanField(default=True)
    include_in_site_map = models.BooleanField(default=True)


class Catalog(models.Model):
    title = models.CharField(
        max_length=255, verbose_name="Title", help_text="Enter the catalog title.")
    parent_catalog = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Parent Catalog",
        help_text="Select the parent catalog if applicable."
    )
    specify_low_inventory_message = models.BooleanField(
        default=False,
        verbose_name="Specify Low Inventory Message?",
        help_text="Enable to specify a low inventory message."
    )
    recipient_emails = models.TextField(
        blank=True,
        null=True,
        verbose_name="Recipient Email(s)",
        help_text="Enter recipient email addresses separated by commas."
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Subject",
        help_text="Enter the subject for the low inventory message."
    )
    message_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message Text",
        help_text="Enter the message text for low inventory warnings."
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="Provide a description for the catalog."
    )
    display_items_on_same_page = models.BooleanField(
        default=False,
        verbose_name="Display Items on the Same Page as the Catalog?",
        help_text="Enable to display items on the same page as the catalog."
    )

    def __str__(self):
        return self.title

    def clean(self):
        """Custom validation to ensure low inventory fields are only filled if enabled."""
        if self.specify_low_inventory_message:
            if not self.recipient_emails or not self.subject or not self.message_text:
                raise ValidationError(
                    "All low inventory message fields must be filled if enabled.")
        else:
            if self.recipient_emails or self.subject or self.message_text:
                raise ValidationError(
                    "Low inventory message fields should not be filled if disabled.")


class PortalContent(models.Model):
    title = models.CharField(max_length=255)
    content=models.TextField(null=True)
    portal = models.ForeignKey(
        Portal, on_delete=models.CASCADE, related_name='content')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True)
    customer_groups = models.ManyToManyField(
        CustomerGroup, blank=True, related_name='accessible_content')
    customers = models.ManyToManyField(
        Customer, blank=True, related_name='portal_content')
    everyone = models.BooleanField(default=False)
    display_in_site_navigation = models.BooleanField(default=True)
    include_in_site_map = models.BooleanField(default=True)
    page_redirect = models.CharField(max_length=50,
                                     choices=[
                                         ('no_redirect', 'No Redirect'),
                                         ('external', 'To a page on another website'),
                                         ('internal', 'To another page on your site'),
                                         ('file', 'To a downloadable file'),
                                     ],
                                     default='no_redirect')
    location = models.OneToOneField(
        PortalSection, on_delete=models.CASCADE, null=True, blank=True, related_name='content')
    catalogs = models.ManyToManyField(
        Catalog,
        through='PortalContentCatalog',
        related_name='portal_contents'
    )

    def __str__(self):
        return self.page.title

    def clean(self):
        if self.everyone and (self.customer_groups or self.customers):
            raise ValidationError(
                "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only.")
        if not self.everyone and not (self.customer_groups or self.customers):
            raise ValidationError(
                "You must set either 'customer_group' or 'everyone'.")

    def get_accessible_customers(self):
        """
        Returns the customers who can access the content.
        If the content is public, all customers have access.
        """
        if self.everyone:
            return Customer.objects.values_list('id', flat=True)
        direct_customers = self.customers.values_list('id', flat=True)
        group_customers = Customer.objects.filter(
            groups__in=self.customer_groups.all()).values_list('id', flat=True)

        accessible_customer_ids = direct_customers.union(group_customers)
        return accessible_customer_ids


class PortalContentCatalog(models.Model):
    portal_content = models.ForeignKey(
        PortalContent, on_delete=models.CASCADE, related_name='catalog_assignments')
    catalog = models.ForeignKey(
        Catalog, on_delete=models.CASCADE, related_name='content_assignments')
    is_active = models.BooleanField(default=False)
    order_approval = models.BooleanField(default=False)

    class Meta:
        unique_together = ('portal_content', 'catalog')

    def __str__(self):
        return f"{self.portal_content} - {self.catalog}"


class CatalogItem(models.Model):
    title = models.CharField(max_length=255)
    catalog = models.ForeignKey(
        'Catalog', null=True, blank=True, on_delete=models.SET_NULL, related_name='catalog_items'
    )
    item_sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=255, blank=True)
    default_quantity = models.PositiveIntegerField(default=1)
    pricing_grid = models.JSONField(
        default=list, validators=[validate_pricing_grid])
    thumbnail = models.ImageField(
        upload_to='thumbnails/', blank=True, null=True)
    preview_image = models.ImageField(
        upload_to='previews/', blank=True, null=True)
    preview_file = models.FileField(
        upload_to='preview_files/', blank=True, null=True)
    available_inventory = models.PositiveIntegerField(default=0)
    minimum_inventory = models.PositiveIntegerField(default=0)
    track_inventory_automatically = models.BooleanField(default=False)
    restrict_orders_to_inventory = models.BooleanField(default=False)
    weight_per_piece_lb = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    weight_per_piece_oz = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    exempt_from_shipping_charges = models.BooleanField(default=False)
    is_this_item_taxable = models.BooleanField(default=False)
    can_item_be_ordered = models.BooleanField(default=False)
    details_page_per_layout = models.CharField(
        max_length=255, default='default')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Attribute(models.Model):
    TEXT_FIELD = 'text_field'
    TEXT_AREA = 'text_area'
    CHECKBOXES = 'checkboxes'
    RADIO_BUTTONS = 'radio_buttons'
    SELECT_MENU = 'select_menu'
    FILE_UPLOAD = 'file_upload'

    ATTRIBUTE_TYPE_CHOICES = [
        (TEXT_FIELD, 'Text field'),
        (TEXT_AREA, 'Text area'),
        (CHECKBOXES, 'Checkboxes'),
        (RADIO_BUTTONS, 'Radio buttons'),
        (SELECT_MENU, 'Select menu'),
        (FILE_UPLOAD, 'File upload'),
    ]

    PER_UNIT = 'per_unit'
    ALL_UNITS = 'all_units'

    PRICE_MODIFIER_SCOPE_CHOICES = [
        (PER_UNIT, 'Per Unit'),
        (ALL_UNITS, 'All units as a whole'),
    ]

    label = models.CharField(max_length=255)
    is_required = models.BooleanField(default=False)
    attribute_type = models.CharField(
        max_length=20, choices=ATTRIBUTE_TYPE_CHOICES, default=TEXT_FIELD
    )
    max_length = models.PositiveIntegerField(null=True, blank=True)

    pricing_tiers = models.JSONField(
        default=list, blank=True,
        help_text="List of dictionaries with 'quantity' and 'price_modifier' keys.",
        validators=[validate_pricing_grid]
    )
    catalog_item = models.ForeignKey(
        CatalogItem, on_delete=models.CASCADE, related_name='attributes')
    price_modifier_scope = models.CharField(
        max_length=20, choices=PRICE_MODIFIER_SCOPE_CHOICES, default=PER_UNIT
    )
    price_modifier_type = models.CharField(
        max_length=10, choices=[('dollar', 'Dollar'), ('percentage', 'Percentage')],
        default='dollar'
    )

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if self.pricing_tiers:
            self.pricing_tiers = sorted(
                self.pricing_tiers, key=lambda x: x.get('quantity', 0))
        super().save(*args, **kwargs)


class AttributeOption(models.Model):
    option = models.CharField(max_length=255)
    alternate_display_text = models.CharField(max_length=255)
    price_modifier_type = models.CharField(
        max_length=10, choices=[('dollar', 'Dollar'), ('percentage', 'Percentage')],
        default='dollar'
    )
    pricing_tiers = models.JSONField(
        default=list, blank=True,
        help_text="List of dictionaries with 'quantity' and 'price_modifier' keys.",
        validators=[validate_pricing_grid]
    )
    item_attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name='options')

    def __str__(self):
        return self.option

    def save(self, *args, **kwargs):
        if self.pricing_tiers:
            self.pricing_tiers = sorted(
                self.pricing_tiers, key=lambda x: x.get('quantity', 0))
        super().save(*args, **kwargs)



class PrintReadyFiles(models.Model):
    class Meta:
        permissions = [
            ('print_ready_files', "Print-Ready Files")
        ]


class MessageCenter(models.Model):
    class Meta:
        permissions = [
            ('message_center', "Message Center")
        ]


class WebsiteUsers(models.Model):
    class Meta:
        permissions = [
            ('website_users', "Website Users")
        ]


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    customer = models.OneToOneField(
        Customer, on_delete=models.PROTECT, null=True, blank=True)


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items")
    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    sub_total = models.DecimalField(
        max_digits=9, decimal_places=2, default=0.00)

    class Meta:
        unique_together = [["catalog_item", "cart", "quantity"]]


class Order(models.Model):
    PAYMENT_STATUS_PENDING = 'P'
    PAYMENT_STATUS_COMPLETE = 'C'
    PAYMENT_STATUS_FAILED = 'F'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_COMPLETE, 'Complete'),
        (PAYMENT_STATUS_FAILED, 'Failed')
    ]

    placed_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=1, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date_needed = models.DateField(default=timezone.now)

    class Meta:
        permissions = [
            ('order', "Order Administration")
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="items")
    catalog_item = models.ForeignKey(
        CatalogItem, on_delete=models.PROTECT, related_name="orderitems")
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)


class OnlinePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Use My Credit Card On File'),
        ('debit_card', 'Use My Debit Account On File'),
    ]

    name = models.CharField(max_length=255, verbose_name="Your Name")
    email_address = models.EmailField(verbose_name="Email Address")
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Payment Method"
    )
    invoice_number = models.CharField(max_length=100, verbose_name="Invoice #")
    po_number = models.CharField(
        max_length=100, verbose_name="P.O. #", blank=True, null=True)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Amount")
    additional_instructions = models.TextField(
        blank=True, null=True, verbose_name="Additional Instructions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment by {self.name} - {self.invoice_number}"

    class Meta:
        verbose_name = "Online Payment"
        verbose_name_plural = "Online Payments"


class FileExchange(models.Model):
    name = models.CharField(max_length=255, default="System Account")
    email_address = models.EmailField()
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField()
    details = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='uploads/')
    file_size = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer to {self.recipient_name} from {self.name}"
