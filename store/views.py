import csv
import os
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,  IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import Cart, CartItem, CatalogItem, ContactInquiry, PortalContentCatalog, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, Portal, Order, OrderItem, Note, ContentType, BillingInfo, Shipment, Transaction, PortalContent, Catalog
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CatalogItemSerializer, ContactInquirySerializer, CreateOrderSerializer, OrderSerializer, PortalContentCatalogSerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, FileSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer, FileTransferSerializer, CreateFileTransferSerializer, UpdateCartItemSerializer, UpdateCustomerSerializer, UpdateOrderSerializer, User, CSVUploadSerializer, CustomerGroupSerializer, CreateCustomerGroupSerializer, PortalSerializer, customer_fields, CreateOrUpdateCatalogItemSerializer, NoteSerializer, BillingInfoSerializer, ShipmentSerializer, TransactionSerializer, CopyCatalogSerializer, CopyCatalogItemSerializer, CopyPortalSerializer
from django.shortcuts import get_object_or_404
from .permissions import FullDjangoModelPermissions, create_permission_class
from .mixins import HandleImagesMixin
from .utils import get_queryset_for_models_with_files, get_base_url
from .utils import bulk_delete_objects, CustomModelViewSet
from store import models
from store import serializers

CanTransferFiles = create_permission_class('store.transfer_files')
PortalPermissions = create_permission_class('store.portals')
CustomerServicePermissions = create_permission_class('store.customers')
WebsiteUsersPermissions = create_permission_class('store.website_users')
OrderPermissions = create_permission_class('store.order')
MessageCenterPermissions = create_permission_class('store.message_center')


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
        [id, *fields_without_id] = customer_fields

        columns = ['name', 'email', 'password',
                   'username', 'is_active'] + fields_without_id

        try:
            if has_header:
                csv_reader = csv.DictReader(csv_content.splitlines())
            else:
                csv_reader = csv.DictReader(
                    csv_content.splitlines(), fieldnames=columns)

            rows = list(csv_reader)
        except csv.Error as e:
            return Response(
                {"error": f"CSV parsing error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not rows:
            return Response({"error": "The uploaded file contains no data."}, status=status.HTTP_400_BAD_REQUEST)

        errors = []
        customer_count = 0

        for row in rows:
            serializer = CreateCustomerSerializer(data=row)
            if serializer.is_valid():
                email = row.get('email')
                name = row.get('name')
                password = row.get('password')
                username = row.get('username')

                user = User(email=email, username=username)
                user.set_password(password)
                user.name = name
                user.save()

                customer_data = {**row}
                customer_data.pop('name')
                customer_data.pop('email')
                customer_data.pop('password')

                if customer_data['pay_tax'] == 'FALSE':
                    customer_data['pay_tax'] = False

                if customer_data['is_active'] == 'FALSE':
                    customer_data['is_active'] = False

                customer_data['pay_tax'] = bool(customer_data['pay_tax'])
                customer_data['is_active'] = bool(customer_data['is_active'])

                Customer.objects.create(user=user, **serializer.data)
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

    queryset = Portal.objects.prefetch_related(
        'content__customer_groups', 'content__customers', 'content__page', 'content__catalog_assignments').all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Portal.objects.prefetch_related(
                'content__customer_groups', 'content__customers',
                'content__page').all()

        try:
            customer = Customer.objects.get(user=user)
            return Portal.objects.prefetch_related(
                'content__customer_groups', 'content__customers',
                'content__page').filter(
                Q(customers=customer) | Q(customer_groups__customers=customer)
            ).distinct()
        except Customer.DoesNotExist:
            pass

    def get_permissions(self):
        if self.request.method == 'POST':
            return [PortalPermissions()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'copy':
            return CopyPortalSerializer
        if self.request.method == 'POST':
            return serializers.CreatePortalSerializer
        return PortalSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        portals = serializer.data
        for portal in portals:
            content = portal.get('content')
            content = [
                item for item in content
                if (item.get('can_user_access') or item['everyone'])
            ]
            portal['content'] = content

        return Response(portals)

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """
        Copy a portal with specified options.
        """
        portal = self.get_object()
        serializer = CopyPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_title = serializer.validated_data['title']
        copy_logo = serializer.validated_data['copy_logo']
        copy_users_and_groups = serializer.validated_data['copy_users_and_groups']
        copy_catalogs_and_items = serializer.validated_data['copy_catalogs_and_items']
        copy_proofing_categories = serializer.validated_data['copy_proofing_categories']
        new_logo = serializer.validated_data.get('new_logo')
        new_catalog_name = serializer.validated_data.get('new_catalog')
        new_proofing_category_name = serializer.validated_data.get(
            'new_proofing_category')
        users = serializer.validated_data.get('users')
        groups = serializer.validated_data.get('groups')

        # Create a new portal
        new_portal = Portal.objects.create(
            title=new_title,
            logo=portal.logo if copy_logo else new_logo,
            copy_from_portal_id=portal.id
        )

        if copy_users_and_groups:
            new_portal.customers.set(portal.customers.all())
            new_portal.customer_groups.set(portal.customer_groups.all())
        elif users:
            new_portal.customers.set(users)
        elif groups:
            new_portal.customer_groups.set(groups)

        for content in portal.content.all():
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

            if copy_catalogs_and_items:
                new_content.catalogs.set(content.catalogs.all())
            else:
                if new_catalog_name:
                    new_catalog = Catalog.objects.create(
                        title=new_catalog_name)
                    # new_content.catalogs.add(new_catalog)

            if copy_proofing_categories:
                # Implement logic to copy proofing categories if needed
                pass

        response_serializer = self.get_serializer(new_portal)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PortalContentViewSet(CustomModelViewSet):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [create_permission_class('portals')()]

    def get_queryset(self):
        portal_id = self.kwargs.get('portal_pk')
        return models.PortalContent.objects.filter(portal_id=portal_id).select_related('page', 'portal').prefetch_related('customers', 'customer_groups')

    def get_serializer_context(self):
        portal_id = self.kwargs.get('portal_pk')
        return {'portal_id': portal_id, 'request': self.request}

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.PortalContentSerializer
        return serializers.CreatePortalContentSerializer


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

        for request_order in online_orders:
            if request_order.this_is_an == 'Order Request':
                messages.append(create_message(
                    request_order,
                    'New Design Order',
                    calculate_file_size(request_order),
                    route='/requests/'
                ))

        messages.sort(key=lambda x: x['Date'], reverse=True)

        return Response(messages)


class CatalogItemViewSet(ModelViewSet):
    """
    A viewset for viewing and editing catalog items.
    """

    def get_serializer_class(self):
        if self.action == 'copy':
            return CopyCatalogItemSerializer
        if self.request.method in ['POST', 'PUT']:
            return CreateOrUpdateCatalogItemSerializer
        return CatalogItemSerializer

    def get_queryset(self):
        catalog_id = self.kwargs.get('catalog_pk')
        return CatalogItem.objects.filter(catalog_id=catalog_id).prefetch_related('attributes__options')

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
    queryset = Cart.objects.prefetch_related("items__catalog_item").all()
    serializer_class = CartSerializer

    def get_serializer_context(self):
        return {'user_id': self.request.user.id}

    @action(detail=False, methods=['get'], url_path='customer-cart')
    def get_customer_cart(self, request):
        user = self.request.user
        customer_id = request.query_params.get(
            'customer_id')  # Get customer_id from query params

        if user.is_staff and not customer_id:
            return Response(
                {"detail": "customer_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif not user.is_staff:
            try:
                customer_id = Customer.objects.only('id').get(user_id=user.id)
            except Customer.DoesNotExist:
                raise NotFound(f"No Customer found with id {user.id}.")

        cart = Cart.objects.prefetch_related(
            "items__catalog_item").filter(customer_id=customer_id).first()
        if not cart:
            raise NotFound(
                f"No cart found for customer with id {customer_id}.")

        serializer = self.get_serializer(cart)
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
        return CartItem.objects.filter(cart_id=cart_id).select_related("catalog_item")

    def get_serializer_context(self):
        cart_id = self.kwargs.get('cart_pk')
        return {"cart_id": cart_id, 'user_id': self.request.user.id}


class OrderViewSet(ModelViewSet):
    http_method_names = ['get', 'patch', 'delete', 'post', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'user_id': self.request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        elif self.request.method == 'PATCH':
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Order.objects.all().select_related('customer').prefetch_related('items__catalog_item')
        customer_id = Customer.objects.only(
            'id').get(user_id=user.id)
        return Order.objects.filter(customer_id=customer_id)


class OnlinePaymentViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'options']

    serializer_class = serializers.OnlinePaymentSerializer
    queryset = models.OnlinePayment.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]


class FileExchangeViewSet(ModelViewSet):
    queryset = models.FileExchange.objects.all()
    serializer_class = serializers.FileExchangeSerializer
    permission_classes = [CanTransferFiles]

    def get_serializer_context(self):
        return {'request': self.request}


class NoteViewSet(ModelViewSet):
    serializer_class = serializers.NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if 'request_pk' in self.kwargs:
            request_pk = self.kwargs.get('request_pk')
            return Note.objects.filter(
                content_type=ContentType.objects.get_for_model(Request),
                object_id=request_pk
            )
        elif 'file_transfer_pk' in self.kwargs:
            file_transfer_pk = self.kwargs.get('file_transfer_pk')
            return Note.objects.filter(
                content_type=ContentType.objects.get_for_model(FileTransfer),
                object_id=file_transfer_pk
            )
        return Note.objects.none()

    def perform_create(self, serializer):

        if 'request_pk' in self.kwargs:
            content_type = ContentType.objects.get_for_model(Request)
            object_id = self.kwargs.get('request_pk')
        elif 'file_transfer_pk' in self.kwargs:
            content_type = ContentType.objects.get_for_model(FileTransfer)
            object_id = self.kwargs.get('file_transfer_pk')

        serializer.save(
            author=self.request.user,
            content_type=content_type,
            object_id=object_id
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
        request_id = self.kwargs.get('request_pk')
        if request_id:
            return Shipment.objects.filter(requests__id=request_id)

        file_transfer_pk = self.kwargs.get('file_transfer_pk')
        if file_transfer_pk:
            return Shipment.objects.filter(
                content_type=ContentType.objects.get_for_model(FileTransfer),
                object_id=file_transfer_pk
            )

    def perform_create(self, serializer):
        request_id = self.kwargs.get('request_pk')
        if request_id:
            request_instance = get_object_or_404(Request, id=request_id)
            content_type = ContentType.objects.get_for_model(Request)
            object_id = request_id
            serializer.save(content_object=request_instance,
                            content_type=content_type, object_id=object_id)
        else:
            file_transfer_id = self.kwargs.get('file_transfer_pk')
            file_transfer_instance = get_object_or_404(
                FileTransfer, id=file_transfer_id)
            content_type = ContentType.objects.get_for_model(FileTransfer)
            object_id = file_transfer_id
            serializer.save(content_object=file_transfer_instance,
                            content_type=content_type, object_id=object_id)


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer

    def get_serializer_context(self):
        if 'request_pk' in self.kwargs:
            return {'content_type': ContentType.objects.get_for_model(Request), 'object_id': self.kwargs.get('request_pk')}
        elif 'file_transfer_pk' in self.kwargs:
            return {'content_type': ContentType.objects.get_for_model(FileTransfer), 'object_id': self.kwargs.get('file_transfer_pk')}
        return {}

    def get_queryset(self):
        request_id = self.kwargs.get('request_pk')
        file_transfer_id = self.kwargs.get('file_transfer_pk')

        if request_id:
            return Transaction.objects.filter(
                content_type=ContentType.objects.get_for_model(Request),
                object_id=request_id
            )
        elif file_transfer_id:
            return Transaction.objects.filter(
                content_type=ContentType.objects.get_for_model(FileTransfer),
                object_id=file_transfer_id
            )
        return Transaction.objects.none()

    def perform_create(self, serializer):
        request_id = self.kwargs.get('request_pk')
        file_transfer_id = self.kwargs.get('file_transfer_pk')

        if request_id:
            request_instance = get_object_or_404(Request, id=request_id)
            serializer.save(content_object=request_instance)
        elif file_transfer_id:
            file_transfer_instance = get_object_or_404(
                FileTransfer, id=file_transfer_id)
            serializer.save(content_object=file_transfer_instance)
