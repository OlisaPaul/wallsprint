import csv
import os
import subprocess
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.http import HttpResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
import io
from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,  IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import Cart, CartItem, CatalogItem, ContactInquiry, PortalContentCatalog, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, Portal, Order, OrderItem, Note, ContentType, BillingInfo, Shipment, Transaction, PortalContent, Catalog, TemplateField
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CatalogItemSerializer, ContactInquirySerializer, CreateOrderSerializer, OrderSerializer, PortalContentCatalogSerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, FileSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer, FileTransferSerializer, CreateFileTransferSerializer, UpdateCartItemSerializer, UpdateCustomerSerializer, UpdateOrderSerializer, User, CSVUploadSerializer, CustomerGroupSerializer, CreateCustomerGroupSerializer, PortalSerializer, customer_fields, CreateOrUpdateCatalogItemSerializer, NoteSerializer, BillingInfoSerializer, ShipmentSerializer, TransactionSerializer, CopyCatalogSerializer, CopyCatalogItemSerializer, CopyPortalSerializer, TemplateFieldSerializer, CreateTemplateFieldSerializer, BusinessCardSerializer
from .permissions import FullDjangoModelPermissions, create_permission_class
from .mixins import HandleImagesMixin
from .utils import get_queryset_for_models_with_files, get_base_url
from .utils import bulk_delete_objects, CustomModelViewSet
from store import models
from store import serializers
from reportlab.graphics import renderPM
import tempfile
# import cairosvg
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
import tempfile

CanTransferFiles = create_permission_class('store.transfer_files')
PortalPermissions = create_permission_class('store.portals')
CustomerServicePermissions = create_permission_class('store.customers')
WebsiteUsersPermissions = create_permission_class('store.website_users')
OrderPermissions = create_permission_class('store.order')
MessageCenterPermissions = create_permission_class('store.message_center')


class BusinessCardViewSet(viewsets.ViewSet):
    def create(self, request):
        """
        Handle POST request to generate a business card as an SVG or PNG.
        """
        serializer = BusinessCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        name = validated_data["name"]
        phone = validated_data["phone"]
        email = validated_data["email"]
        business_name = validated_data["business_name"]
        output_format = validated_data["format"]

        # Render the SVG template
        template = Template(SVG_TEMPLATE)
        context = Context({
            "name": name,
            "phone": phone,
            "email": email,
            "business_name": business_name,
        })
        svg_output = template.render(context)

        # if output_format == "png":
        #     try:
        #         # Convert SVG string to a file-like object
        #         svg_file = io.StringIO(svg_output)
        #         # Convert SVG to ReportLab Graphics object
        #         drawing = svg2rlg(svg_file)
        #         # Create a bytes buffer for the PNG
        #         png_buffer = io.BytesIO()
        #         # Render the drawing as PNG to the buffer
        #         renderPM.drawToFile(drawing, png_buffer, fmt="PNG")
        #         # Get the PNG bytes
        #         png_output = png_buffer.getvalue()
        #         return HttpResponse(png_output, content_type="image/png")
        #     except Exception as e:
        #         return Response(
        #             {"error": f"Failed to convert SVG to PNG: {str(e)}"},
        #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
        #         )

        # print(svg_output)
        return HttpResponse(svg_output, content_type="image/svg+xml")


@csrf_exempt  # Remove this if using CSRF tokens properly
def generate_business_card(request, editable_item_id):
    editable_item = models.CatalogItem.objects.filter(
        pk=editable_item_id).first()

    SVG_TEMPLATE = editable_item.front_svg_code or serializers.SVG_TEMPLATE
    template_fields = editable_item.template_fields.all() or serializers.TEMPLATE_FIELDS

    context_data = {}
    for field in template_fields:
        # Get the value from request.GET with a default empty string
        field_value = request.GET.get(field.label, "")
        context_data[field.label] = field_value or field.placeholder

    output_format = request.GET.get("format", "svg")

    # Render the SVG template
    template = Template(SVG_TEMPLATE)
    context = Context(context_data)
    svg_output = template.render(context)

    if output_format == "png":
        try:
            # Convert SVG to PNG using CairoSVG
            png_output = io.BytesIO()
            cairosvg.svg2png(bytestring=svg_output.encode('utf-8'), write_to=png_output)
            return HttpResponse(png_output.getvalue(), content_type="image/png")
        except Exception as e:
            print(f"SVG to PNG conversion error: {e}")
            return HttpResponse(
                {"error": f"Failed to convert SVG to PNG: {str(e)}"},
                status=500
            )

    return HttpResponse(svg_output, content_type="image/svg+xml")

model_map = {
    'request_pk': Request,
    'file_transfer_pk': FileTransfer,
    'order_pk': Order,
    'item_pk': CartItem,
}


def get_content_type_and_id(kwargs):
    """Helper function to get content type and ID from kwargs"""
    for key, model in model_map.items():
        if key in kwargs:
            return ContentType.objects.get_for_model(model), kwargs[key]
    return None, None


def get_queryset_for_content_types(kwargs, model_class):
    """Get queryset filtered by content type and object ID"""
    content_type, object_id = get_content_type_and_id(kwargs)
    if content_type and object_id:
        return model_class.objects.filter(
            content_type=content_type,
            object_id=object_id
        )
    return model_class.objects.none()


def create_for_content_types(kwargs, serializer):
    """Create object with content type relationship"""
    content_type, object_id = get_content_type_and_id(kwargs)
    print(content_type, object_id)
    if content_type and object_id:
        instance = get_object_or_404(content_type.model_class(), id=object_id)
        print(instance)
        serializer.save(content_object=instance)


def get_serializer_context_for_content_types(kwargs):
    """Get serializer context with content type info"""
    content_type, object_id = get_content_type_and_id(kwargs)
    if content_type and object_id:
        return {
            "content_type": content_type,
            "object_id": object_id
        }
    return {}


class CustomerCreationHandler:
    def __init__(self, user, customer_data):
        self.user = user
        self.customer_data = customer_data

    def create_customer(self):
        """Creates a Customer instance using the associated User."""
        return Customer(user=self.user, **self.customer_data)


class ContactInquiryViewSet(CustomModelViewSet):
    queryset = ContactInquiry.objects.all()
    serializer_class = ContactInquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [MessageCenterPermissions()]


class ImageViewSet(ListModelMixin, GenericViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer


class QuoteRequestViewSet(ModelViewSet, HandleImagesMixin):
    queryset = get_queryset_for_models_with_files(QuoteRequest)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateQuoteRequestSerializer
        return QuoteRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [MessageCenterPermissions()]


class RequestViewSet(CustomModelViewSet):
    queryset = get_queryset_for_models_with_files(
        Request).prefetch_related('transactions', 'shipments', 'notes__author').select_related('billing_info')

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRequestSerializer
        if self.request.method in ['PUT', 'PATCH']:
            return serializers.UpdateRequestSerializer
        return RequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


class OnlineProofViewSet(ModelViewSet):
    queryset = get_queryset_for_models_with_files(models.OnlineProof)
    permission_classes = [create_permission_class('store.online_proofing')]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.CreateOnlineProofSerializer
        return serializers.OnlineProofSerializer


class FileTransferViewSet(CustomModelViewSet):
    queryset = get_queryset_for_models_with_files(FileTransfer).prefetch_related(
        'transactions', 'shipments', 'notes__author').select_related('billing_info')

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateFileTransferSerializer
        if self.request.method in ['PUT', 'PATCH']:
            return serializers.UpdateFileTransferSerializer
        return FileTransferSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [CanTransferFiles()]


class CustomerViewSet(CustomModelViewSet):
    queryset = Customer.objects.select_related(
        'user').prefetch_related('groups').all()
    permission_classes = [WebsiteUsersPermissions]

    def get_serializer_class(self):
        if self.action == 'bulk_upload':
            return CSVUploadSerializer
        elif self.request.method == "POST":
            return CreateCustomerSerializer
        elif self.request.method in ["PUT", "PATCH"]:
            return UpdateCustomerSerializer
        return CustomerSerializer

    @action(detail=False, methods=['post'], url_path='bulk-upload', url_name='bulk_upload')
    @transaction.atomic()
    def bulk_upload(self, request):
        """
        Handles bulk upload of data from a CSV file.

        This method accepts a file upload through a POST request and processes it as a CSV.
        Each row in the CSV is read and converted to a dictionary format using `csv.DictReader`.

        Expects:
            - The uploaded file to be in CSV format with UTF-8 encoding.
            - A file uploaded with the key 'file' in the request.

        Returns:
            - HTTP 400 response with an error message if the file is missing, is not a CSV, 
            or there is a CSV parsing error.
            - HTTP 200 response indicating success once the file is processed.
        """

        serializer = CSVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        csv_content = serializer.validated_data['file']
        has_header = serializer.validated_data['has_header']
        columns = ['name', 'email', 'password',
                   'username', 'is_active'] + customer_fields[1:]

        try:
            csv_reader = csv.DictReader(csv_content.splitlines(
            ), fieldnames=columns if not has_header else None)
            rows = list(csv_reader)
        except csv.Error as e:
            return Response({"error": f"CSV parsing error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({"error": "The uploaded file contains no data."}, status=status.HTTP_400_BAD_REQUEST)

        errors = []
        customer_count = 0

        for row in rows:
            serializer = CreateCustomerSerializer(data=row)
            if serializer.is_valid():
                user = User(email=row['email'], username=row['username'])
                user.set_password(row['password'])
                user.name = row['name']
                user.save()

                customer_data = {**row}
                customer_data.pop('name', None)
                customer_data.pop('email', None)
                customer_data.pop('password', None)

                customer_data['pay_tax'] = row.get(
                    'pay_tax', 'FALSE') == 'TRUE'
                customer_data['is_active'] = row.get(
                    'is_active', 'FALSE') == 'TRUE'

                Customer.objects.create(user=user, **customer_data)
                customer_count += 1
            else:
                errors.append({**serializer.errors, "row": row})

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": f"{customer_count} customers created successfully."}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["GET", "PUT"], permission_classes=[IsAuthenticated])
    def me(self, request):
        try:
            customer = Customer.objects.get(
                user_id=request.user.id)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if request.method == "GET":
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class CustomerGroupViewSet(CustomModelViewSet):
    queryset = CustomerGroup.objects.prefetch_related('customers').all()
    permission_classes = [WebsiteUsersPermissions]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerGroupSerializer
        if self.request.method in ["PUT", "PATCH"]:
            return serializers.UpdateCustomerGroupSerializer
        return CreateCustomerGroupSerializer


class PortalViewSet(CustomModelViewSet):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [create_permission_class('portals')()]

    def get_queryset(self):
        prefetch_array = [
            'contents__customer_groups__customers__user', 'contents__customers__user',
            'contents__catalogs', 'cart_set__items',
            'customers__user', 'customer_groups__customers__user'
        ]

        user = self.request.user
        if user.is_staff:
            return Portal.objects.prefetch_related(*prefetch_array).all()
        else:
            try:
                customer = Customer.objects.get(user=user)
                self.request.customer = customer
                return Portal.objects.prefetch_related(*prefetch_array).filter(
                    Q(customers=customer) | Q(
                        customer_groups__customers=customer)
                ).distinct()
            except Customer.DoesNotExist:
                return Portal.objects.none()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [PortalPermissions()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'copy':
            return CopyPortalSerializer
        if self.request.method == 'PATCH':
            return serializers.PatchPortalSerializer
        if self.request.method == 'POST':
            return serializers.CreatePortalSerializer
        return PortalSerializer

    def get_serializer_context(self):
        customer_id = self.request.customer.id if hasattr(
            self.request, 'customer') else None

        return {'request': self.request, 'customer_id': customer_id}

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())

    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)

    #     serializer = self.get_serializer(queryset, many=True)

    #     portals = serializer.data
    #     for portal in portals:
    #         content = portal.get('content')
    #         nav_view = True if request.user.is_staff else content.get('display_in_site_navigation')
    #         content = [
    #             item for item in content
    #             if (nav_view and (item.get('can_user_access') or item['everyone']))
    #         ]
    #         portal['content'] = content

    #     return Response(portals)

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """
        Copy a portal with specified options.
        """
        portal = self.get_object()
        serializer = serializers.CopyPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ['id', 'title', 'logo',
         'same_permissions', 'copy_the_logo', 'same_catalogs', 'same_proofing_categories',
         'customers', 'customer_groups', 'catalog',
         ]

        new_title = serializer.validated_data['title']
        copy_the_logo = serializer.validated_data['copy_the_logo']
        same_permissions = serializer.validated_data['same_permissions']
        same_catalogs = serializer.validated_data['same_catalogs']
        same_proofing_categories = serializer.validated_data['same_proofing_categories']
        logo = serializer.validated_data.get('logo')
        catalog = serializer.validated_data.get('new_catalog')
        new_proofing_category_name = serializer.validated_data.get(
            'new_proofing_category')
        customers = serializer.validated_data.get('customers')
        customer_groups = serializer.validated_data.get('customer_groups')

        # Create a new portal
        new_portal = Portal.objects.create(
            title=new_title,
            logo=portal.logo if copy_the_logo else logo,
            copy_from_portal_id=portal.id
        )

        if same_permissions:
            new_portal.customers.set(portal.customers.all())
            new_portal.customer_groups.set(portal.customer_groups.all())
        elif customers:
            new_portal.customers.set(customers)
        elif customer_groups:
            new_portal.customer_groups.set(customer_groups)

        serializers._implement_permission_change(
            serializer, new_portal, customers)

        for content in portal.contents.all():
            new_content = PortalContent.objects.create(
                portal=new_portal,
                title=content.title,
                content=content.content,
                page=content.page,
                everyone=content.everyone,
                display_in_site_navigation=content.display_in_site_navigation,
                include_in_site_map=content.include_in_site_map,
                page_redirect=content.page_redirect,
                location=content.location,
                logo=content.logo,
                payment_proof=content.payment_proof,
                order_history=content.order_history
            )

            if same_catalogs:
                new_content.catalogs.set(content.catalogs.all())
            else:
                if catalog:
                    Catalog.objects.create(title=catalog)
                    # new_content.catalogs.add(new_catalog)

            if same_proofing_categories:
                # Implement logic to copy proofing categories if needed
                pass

        response_serializer = self.get_serializer(new_portal)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        portal = self.get_object()
        serializers._implement_permission_change(
            {"customers": [1]}, portal, portal.customers.all())
        return super().destroy(request, *args, **kwargs)


class PortalContentViewSet(CustomModelViewSet):
    allowed_http_methods = ['get', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [create_permission_class('portals')()]

    def get_queryset(self):
        portal_id = self.kwargs.get('portal_pk')
        if not portal_id.isdigit():
            raise ValidationError("portal_pk must be an integer.")
        return models.PortalContent.objects.filter(portal_id=portal_id).select_related('page', 'portal').prefetch_related('customers__user', 'customer_groups__customers__user', 'catalogs', 'content__catalogs')

    def get_serializer_context(self):
        portal_id = self.kwargs.get('portal_pk')
        return {'portal_id': portal_id, 'request': self.request}

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.PortalContentSerializer
        return serializers.UpdatePortalContentSerializer

    def destroy(self, request, *args, **kwargs):
        portal_content = self.get_object()
        serializers._implement_permission_change(
            {"customers": [1]}, portal_content.portal, portal_content.portal.all())
        return super().destroy(request, *args, **kwargs)


class PortalContentCatalogViewSet(ModelViewSet):
    serializer_class = PortalContentCatalogSerializer

    def get_serializer_context(self):
        content_id = self.kwargs.get('content_pk')
        return {'content_id': content_id}

    def get_queryset(self):
        content_id = self.kwargs.get('content_pk')
        return PortalContentCatalog.objects.filter(portal_content_id=content_id)

    def create(self, request, *args, **kwargs):
        # Check if the input data is a list for bulk creation
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
        else:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()


class HTMLFileViewSet(CustomModelViewSet):
    queryset = models.Page.objects.all()
    serializer_class = serializers.PageSerializer


class CatalogViewSet(CustomModelViewSet):
    queryset = models.Catalog.objects.all()

    def get_serializer_class(self):
        if self.action == 'copy':
            return CopyCatalogSerializer
        return serializers.CatalogSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """
        Copy a catalog with a new title and optionally its items.
        """
        print(request.data)
        catalog = self.get_object()
        serializer = CopyCatalogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_title = serializer.validated_data['title']
        copy_items = serializer.validated_data['copy_items']
        print(copy_items)

        # Create a new catalog with the provided title
        new_catalog = models.Catalog.objects.create(
            title=new_title,
            parent_catalog=catalog.parent_catalog,
            specify_low_inventory_message=catalog.specify_low_inventory_message,
            recipient_emails=catalog.recipient_emails,
            subject=catalog.subject,
            message_text=catalog.message_text,
            description=catalog.description,
            display_items_on_same_page=catalog.display_items_on_same_page
        )

        # Optionally copy catalog items
        if copy_items:
            for item in catalog.catalog_items.all():
                item.pk = None  # Reset primary key to create a new object
                item.catalog = new_catalog
                item.save()

        response_serializer = self.get_serializer(new_catalog)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def favorites(self, request, pk=None):
        """
        Retrieve all favorite items in the catalog.
        """
        catalog = self.get_object()
        favorite_items = catalog.catalog_items.filter(
            is_favorite=True)  # Assuming there's an 'is_favorite' field

        response_serializer = serializers.CatalogItemSerializer(
            favorite_items, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class MessageCenterViewSet(ModelViewSet):
    serializer_class = serializers.MessageCenterSerializer
    # ordering = ['-date']

    def get_queryset(self):
        queryset = []
        queryset.extend(list(Request.objects.all()))
        queryset.extend(list(ContactInquiry.objects.all()))
        queryset.extend(list(FileTransfer.objects.all()))
        return sorted(queryset, key=lambda x: x.created_at, reverse=True)


class MessageCenterView(APIView):
    permission_classes = [create_permission_class('store.message_center')]

    def get(self, request):
        base_url = get_base_url(request)
        messages = []

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        date_filter = Q()
        if start_date:
            start_date = parse_datetime(start_date)
            date_filter &= Q(created_at__gte=start_date)
        if end_date:
            end_date = parse_datetime(end_date)
            date_filter &= Q(created_at__lte=end_date)

        online_file_transfers = get_queryset_for_models_with_files(
            FileTransfer).filter(date_filter)
        online_orders = get_queryset_for_models_with_files(
            Request).filter(date_filter)
        general_contacts = ContactInquiry.objects.filter(date_filter)
        online_requests = get_queryset_for_models_with_files(
            QuoteRequest).filter(date_filter)
        online_payments = models.OnlinePayment.objects.filter(date_filter)
        online_proofs = models.OnlineProof.objects.filter(date_filter)
        file_transfers = models.FileExchange.objects.filter(date_filter)

        def calculate_file_size(instance):
            file_size_in_bytes = sum(
                [file.file_size for file in instance.files.all() if file.file_size]) if not isinstance(instance, models.FileExchange) else instance.file_size

            if not file_size_in_bytes:
                return '0KB'
            if file_size_in_bytes >= 1024 * 1024:
                return f"{file_size_in_bytes / (1024 * 1024):.2f} MB"
            return f"{file_size_in_bytes / 1024:.2f} KB"

        def create_message(instance, title, attachments='n/a', route=''):
            files = []
            if hasattr(instance, 'files') and instance.files.exists():
                files = [
                    file.path.url if file else '' for file in instance.files.all()]
            elif hasattr(instance, 'file'):
                file = instance.file.url
                url = f'{base_url}{file}'
                files = [url]

            return {
                'id': instance.id,
                'Date': instance.created_at,
                'title_and_tracking': title,
                'From': instance.name,
                'Email': instance.email_address,
                'Attachments': attachments,
                'Path': f'{base_url}/api/v1/store{route}{instance.id}',
                "Files": files
            }

        # for online_proof in file_transfers:
        #     messages.append(create_message(
        #         online_proof,
        #         'File Transfer',
        #         calculate_file_size(online_proof)
        #     ))

        # for online_proof in online_proofs:
        #     messages.append(create_message(
        #         online_proof,
        #         'Online Proof',
        #         calculate_file_size(online_proof)
        #     ))

        for online_request in online_requests:
            messages.append(create_message(
                online_request,
                'Quote Request',
                calculate_file_size(online_request),
                route='/quote-requests/'
            ))

        # Online orders
        for online_order in online_orders:
            if online_order.this_is_an == 'Estimate Request':
                messages.append(create_message(
                    online_order,
                    'Estimate Request',
                    calculate_file_size(online_order),
                    route='/requests/'
                ))

        # General contacts
        for general_contact in general_contacts:
            messages.append(create_message(
                general_contact,
                'General Contact',
                route='/contact-us/'
            ))

        # for online_payment in online_payments:
        #     messages.append(create_message(
        #         online_payment,
        #         'Online Payment',
        #     ))

        messages.sort(key=lambda x: x['Date'], reverse=True)

        return Response(messages)


class OrderView(APIView):
    permission_classes = [OrderPermissions]

    def get(self, request):
        base_url = get_base_url(request)
        messages = []

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        date_filter = Q()
        if start_date:
            start_date = parse_datetime(start_date)
            date_filter &= Q(created_at__gte=start_date)
        if end_date:
            end_date = parse_datetime(end_date)
            date_filter &= Q(created_at__lte=end_date)

        online_file_transfers = get_queryset_for_models_with_files(
            FileTransfer).filter(date_filter)
        online_orders = get_queryset_for_models_with_files(
            Request).filter(date_filter)
        orders = get_queryset_for_models_with_files(Order).filter(date_filter)

        def calculate_file_size(instance):
            file_size_in_bytes = sum(
                [file.file_size for file in instance.files.all() if file.file_size]) if not isinstance(instance, models.FileExchange) else instance.file_size

            if not file_size_in_bytes:
                return '0KB'
            if file_size_in_bytes >= 1024 * 1024:
                return f"{file_size_in_bytes / (1024 * 1024):.2f} MB"
            return f"{file_size_in_bytes / 1024:.2f} KB"

        def create_message(instance, title, attachments='n/a', route=''):
            files = []
            if hasattr(instance, 'files') and instance.files.exists():
                files = [
                    file.path.url if file else '' for file in instance.files.all()]
            elif hasattr(instance, 'file'):
                file = instance.file.url
                url = f'{base_url}{file}'
                files = [url]

            return {
                'id': instance.id,
                'Date': instance.created_at,
                'title_and_tracking': title,
                'From': instance.name,
                'Email': instance.email_address,
                'Attachments': attachments,
                'Path': f'{base_url}/api/v1/store{route}{instance.id}',
                'Status': instance.status,
                "Files": files
            }

        # File transfers
        for online_proof in online_file_transfers:
            messages.append(create_message(
                online_proof,
                'Design-Ready Order',
                calculate_file_size(online_proof),
                route='/file-transfers/'
            ))

        for order in online_orders:
            if order.this_is_an == 'Order Request':
                messages.append(create_message(
                    order,
                    'New Design Order',
                    calculate_file_size(order),
                    route='/requests/'
                ))

        for order in orders:
            messages.append(create_message(
                order,
                'Portal order',
                calculate_file_size(order),
                route='/orders/'
            ))

        messages.sort(key=lambda x: x['Date'], reverse=True)

        return Response(messages)


class CatalogItemViewSet(ModelViewSet):
    """
    A viewset for viewing and editing catalog items.
    """

    def get_permissions(self):
        catalog_id = self.kwargs.get('catalog_pk')
        if catalog_id:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'copy':
            return CopyCatalogItemSerializer
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return CreateOrUpdateCatalogItemSerializer
        return CatalogItemSerializer

    def get_queryset(self):
        catalog_id = self.kwargs.get('catalog_pk')
        queryset = CatalogItem.objects.filter(
            status=CatalogItem.APPROVED).prefetch_related('attributes__options')
        if catalog_id:
            queryset = queryset.filter(catalog_id=catalog_id)
        return queryset

    def get_serializer_context(self):
        catalog_id = self.kwargs.get('catalog_pk')
        return {'catalog_id': catalog_id}

    def create(self, request, *args, **kwargs):
        """
        Override create to handle nested attributes.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Override update to handle nested attributes.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='get-catalog-items-for-portal')
    def get_catalog_items_for_portal(self, request):
        """
        Returns all catalog items associated with the portal.
        """
        portal_id = self.request.query_params.get('portal_id')
        if not portal_id:
            return Response({'detail': 'Portal ID query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = CatalogItem.objects.filter(
            catalog__portal_contents__portal_id=portal_id, status=CatalogItem.APPROVED
        ).prefetch_related('attributes__options').select_related('catalog')

        serializer = CatalogItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @transaction.atomic()
    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None, catalog_pk=None):
        """
        Copy a catalog item with a new title and assign it to a parent catalog.
        """
        catalog_item = self.get_object()
        serializer = CopyCatalogItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_title = serializer.validated_data['title']
        catalog = serializer.validated_data['catalog']

        # Create a new catalog item with the provided title and parent catalog
        new_catalog_item = CatalogItem.objects.create(
            title=new_title,
            catalog=catalog,
            item_sku=catalog_item.item_sku,
            description=catalog_item.description,
            short_description=catalog_item.short_description,
            default_quantity=catalog_item.default_quantity,
            pricing_grid=catalog_item.pricing_grid,
            thumbnail=catalog_item.thumbnail,
            preview_image=catalog_item.preview_image,
            preview_file=catalog_item.preview_file,
            available_inventory=catalog_item.available_inventory,
            minimum_inventory=catalog_item.minimum_inventory,
            track_inventory_automatically=catalog_item.track_inventory_automatically,
            restrict_orders_to_inventory=catalog_item.restrict_orders_to_inventory,
            weight_per_piece_lb=catalog_item.weight_per_piece_lb,
            weight_per_piece_oz=catalog_item.weight_per_piece_oz,
            exempt_from_shipping_charges=catalog_item.exempt_from_shipping_charges,
            is_this_item_taxable=catalog_item.is_this_item_taxable,
            can_item_be_ordered=catalog_item.can_item_be_ordered,
            details_page_per_layout=catalog_item.details_page_per_layout,
        )

        new_catalog_item.attributes.set(catalog_item.attributes.all())

        response_serializer = self.get_serializer(new_catalog_item)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CartViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Cart.objects.select_related(
        "customer__user").prefetch_related("items__catalog_item").all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        customer_id = None
        if not self.request.user.is_staff:
            user_id = self.request.user.id
            try:
                customer_id = Customer.objects.only(
                    'id').get(user_id=self.request.user.id).id
            except Customer.DoesNotExist:
                raise NotFound(f"No Customer found with id {user_id}.")
        return {'user_id': self.request.user.id, 'customer_id': customer_id}

    @action(detail=False, methods=['get'], url_path='customer-cart-per-portal')
    def get_customer_cart(self, request):
        user = self.request.user
        customer_id = request.query_params.get('customer_id', '').strip('/')
        portal_id = request.query_params.get('portal_id', '').strip('/')

        if not portal_id:
            return Response(
                {"detail": "portal_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_staff and not customer_id:
            return Response(
                {"detail": "customer_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif not user.is_staff:
            try:
                customer_id = Customer.objects.only('id').get(user_id=user.id)
                self.customer_id = customer_id
            except Customer.DoesNotExist:
                raise NotFound(f"No Customer found with id {user.id}.")

        cart = Cart.objects.prefetch_related(
            "items__catalog_item").filter(customer_id=customer_id, portal_id=portal_id).first()
        if not cart:
            raise NotFound(
                f"No cart found for customer with id {customer_id}.")

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='customer-carts')
    def get_customer_carts(self, request):
        user = self.request.user
        customer_id = request.query_params.get('customer_id')

        if user.is_staff and not customer_id:
            return Response(
                {"detail": "customer_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif not user.is_staff:
            try:
                customer_id = Customer.objects.only('id').get(user_id=user.id)
                self.customer_id = customer_id
            except Customer.DoesNotExist:
                raise NotFound(f"No Customer found with id {user.id}.")

        cart = Cart.objects.prefetch_related(
            "items__catalog_item").filter(customer_id=customer_id)

        serializer = self.get_serializer(cart, many=True)
        return Response(serializer.data)


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_queryset(self):
        cart_id = self.kwargs.get('cart_pk')
        return CartItem.objects.filter(cart_id=cart_id).select_related("catalog_item", 'details')

    def get_serializer_context(self):
        cart_id = self.kwargs.get('cart_pk')
        return {"cart_id": cart_id, 'user_id': self.request.user.id}


class OrderViewSet(ModelViewSet):
    http_method_names = ['get', 'patch', 'delete', 'post', 'head', 'options']
    prefetch_related = ['items__catalog_item__catalog',
                        'notes__author', 'shipments', 'billing_info', 'transactions']

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
  
    def get_customer(self):
        self.customer = None
        if self.request.user.is_staff:
            return
        else:
            try:
                self.customer = Customer.objects.only(
                    'id').get(user=self.request.user)
                return
            except Customer.DoesNotExist:
                return

    def get_serializer_context(self):
        if not hasattr(self, 'customer'):
            self.get_customer()
        return {'customer': self.customer}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        elif self.request.method == 'PATCH':
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(self, 'customer'):
            self.get_customer()

        queryset = get_queryset_for_models_with_files(Order)\
            .select_related('customer__user')\
            .prefetch_related(*self.prefetch_related)

        if user.is_staff:
            return queryset
        return queryset.filter(customer=self.customer)


class OrderItemViewSet(ModelViewSet):
    # http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializers.OrderItemSerializer
        if self.request.method in ['PATCH', 'PUT']:
            return serializers.UpdateOrderItemSerializer
        return serializers.CreateOrderItemSerializer

    def get_queryset(self):
        order_id = self.kwargs.get('order_pk')
        return OrderItem.objects.filter(order_id=order_id).select_related('catalog_item__catalog')

    def get_serializer_context(self):
        order_id = self.kwargs.get('order_pk')
        return {"order_id": order_id, 'id': order_id, 'model': OrderItem, 'is_new': True}


class OnlinePaymentViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'options']

    serializer_class = serializers.OnlinePaymentSerializer
    queryset = models.OnlinePayment.objects.all()
    permission_classes = [IsAuthenticated]

    def get_customer(self):
        try:
            self.customer = Customer.objects.only(
                'id').get(user=self.request.user)
        except Customer.DoesNotExist:
            self.customer = None

    def get_serializer_context(self):
        if not hasattr(self, 'customer'):
            self.get_customer()
        return {'request': self.request, 'customer': self.customer}

    def create(self, request, *args, **kwargs):
        if not hasattr(self, 'customer'):
            self.get_customer()

        if not self.customer:
            return Response(
                {"detail": "You do not have permission to access this resource"},
                status=status.HTTP_404_NOT_FOUND
            )

        return super().create(request, *args, **kwargs)


class FileExchangeViewSet(ModelViewSet):
    queryset = models.FileExchange.objects.all()
    serializer_class = serializers.FileExchangeSerializer
    permission_classes = [CanTransferFiles]

    def get_serializer_context(self):
        return {'request': self.request}


class NoteViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.NoteSerializer
        return serializers.CreateNoteSerializer

    def get_queryset(self):
        return get_queryset_for_content_types(self.kwargs, Note)

    def perform_create(self, serializer):
        content_type, object_id = get_content_type_and_id(self.kwargs)
        content_object = content_type.get_object_for_this_type(id=object_id)
        serializer.save(
            author=self.request.user,
            content_object=content_object
        )


class BillingInfoViewSet(ModelViewSet):
    serializer_class = BillingInfoSerializer

    def perform_create(self, serializer):
        request_id = self.kwargs.get('request_pk')
        file_transfer_id = self.kwargs.get('file_transfer_pk')

        if request_id:
            instance = get_object_or_404(Request, id=request_id)
            instance.billing_info = serializer.save()
            instance.save()
        elif file_transfer_id:
            print('file_transfer_id', file_transfer_id)
            instance = get_object_or_404(FileTransfer, id=file_transfer_id)
            instance.billing_info = serializer.save()
            instance.save()

    def get_queryset(self):
        request_id = self.kwargs.get('request_pk')
        file_transfer_id = self.kwargs.get('file_transfer_pk')

        if request_id:
            return BillingInfo.objects.filter(requests__id=request_id)
        elif file_transfer_id:
            return BillingInfo.objects.filter(file_transfers__id=file_transfer_id)
        return BillingInfo.objects.none()


class ShipmentViewSet(ModelViewSet):
    serializer_class = ShipmentSerializer

    def get_queryset(self):
        return get_queryset_for_content_types(self.kwargs, Shipment)

    def perform_create(self, serializer):
        return create_for_content_types(self.kwargs, serializer)


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer

    def get_serializer_context(self):
        return get_serializer_context_for_content_types(self.kwargs)

    def get_queryset(self):
        return get_queryset_for_content_types(self.kwargs, Transaction)

    def perform_create(self, serializer):
        return create_for_content_types(self.kwargs, serializer)


class ItemDetailsViewSet(ModelViewSet):
    serializer_class = serializers.ItemDetailsSerializer

    def get_queryset(self):
        item_id = self.kwargs.get('item_pk')
        oder_item_id = self.kwargs.get('order_item_pk')

        if item_id:
            return models.ItemDetails.objects.filter(cart_items__id=item_id)
        elif oder_item_id:
            return models.ItemDetails.objects.filter(order_items__id=oder_item_id)

    def get_serializer_context(self, *args, **kwargs):
        order_item_id = self.kwargs.get('order_item_pk')
        cart_item_id = self.kwargs.get('item_pk')
        model = OrderItem if order_item_id else CartItem
        id = order_item_id or cart_item_id

        return {'model': model, 'id': id}


class AttributeViewSet(ModelViewSet):
    def get_serializer_context(self):
        catalog_item_id = self.kwargs['catalog_item_pk']
        return {'catalog_item_id': catalog_item_id}

    def get_queryset(self):
        catalog_item_id = self.kwargs.get('catalog_item_pk')
        queryset = models.Attribute.objects.filter(
            catalog_item_id=catalog_item_id)

        return queryset.prefetch_related('options')

    serializer_class = serializers.AttributeSerializer


class AttributeOptionViewSet(ModelViewSet):
    def get_serializer_context(self):
        attribute_id = self.kwargs['attribute_pk']
        return {'attribute_id': attribute_id}

    def get_queryset(self):
        attribute_id = self.kwargs.get('attribute_pk')
        return models.AttributeOption.objects.filter(item_attribute_id=attribute_id)

    serializer_class = serializers.AttributeOptionSerializer


class TemplateFieldViewSet(CustomModelViewSet):
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateTemplateFieldSerializer
        return TemplateFieldSerializer

    def get_queryset(self):
        # catalog_item_id = self.kwargs.get('catalog_item_pk')
        editable_item_id = self.kwargs.get('editable_item_pk')
        return TemplateField.objects.filter(catalog_item_id=editable_item_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['catalog_item_id'] = self.kwargs.get('catalog_item_pk')
        context['editable_item_id'] = self.kwargs.get('editable_item_pk')
        return context

    def create(self, request, *args, **kwargs):
        # Check if the input data is a list for bulk creation
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditableCatalogItemViewSet(ModelViewSet):
    queryset = CatalogItem.objects.filter(Q(file_name__isnull=False)).prefetch_related(
        'template_fields').select_related('catalog')
    serializer_class = serializers.CreateEditableCatalogItemFileSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.CreateEditableCatalogItemFileSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return serializers.UpdateEditableCatalogItemFileSerializer
        return serializers.EditableCatalogItemFileSerializer
