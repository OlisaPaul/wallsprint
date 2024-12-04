import csv
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,  IsAuthenticated
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import Cart, CartItem, CatalogItem, ContactInquiry, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, Portal
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CatalogItemSerializer, ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, FileSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer, FileTransferSerializer, CreateFileTransferSerializer, UpdateCartItemSerializer, UpdateCustomerSerializer, User, CSVUploadSerializer, CustomerGroupSerializer, CreateCustomerGroupSerializer, PortalSerializer, customer_fields, CreateOrUpdateCatalogItemSerializer
from .permissions import FullDjangoModelPermissions, create_permission_class
from .mixins import HandleImagesMixin
from .utils import get_queryset_for_models_with_files
from .utils import bulk_delete_objects, CustomModelViewSet
from store import models
from store import serializers

CanTransferFiles = create_permission_class('store.transfer_files')
PortalPermissions = create_permission_class('store.portals')
CustomerServicePermissions = create_permission_class('store.customers')


class CustomerCreationHandler:
    def __init__(self, user, customer_data):
        self.user = user
        self.customer_data = customer_data

    def create_customer(self):
        """Creates a Customer instance using the associated User."""
        return Customer(user=self.user, **self.customer_data)


class ContactInquiryViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ContactInquiry.objects.prefetch_related('files').all()
    serializer_class = ContactInquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


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
        return [FullDjangoModelPermissions()]


class RequestViewSet(GenericViewSet, DestroyModelMixin, CreateModelMixin, ListModelMixin):
    queryset = get_queryset_for_models_with_files(Request)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRequestSerializer
        return RequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


class FileTransferViewSet(GenericViewSet, DestroyModelMixin, CreateModelMixin, ListModelMixin):
    queryset = get_queryset_for_models_with_files(FileTransfer)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateFileTransferSerializer
        return FileTransferSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [CanTransferFiles()]


class CustomerViewSet(CustomModelViewSet):
    queryset = Customer.objects.select_related(
        'user').prefetch_related('groups').all()
    permission_classes = [CustomerServicePermissions]

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
        customer = Customer.objects.get(
            user_id=request.user.id)
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
    permission_classes = [CustomerServicePermissions]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerGroupSerializer
        return CreateCustomerGroupSerializer


class PortalViewSet(CustomModelViewSet):
    queryset = Portal.objects.prefetch_related(
        'content__customer_groups', 'content__customers', 'content__html_file').all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Portal.objects.prefetch_related(
                'content__customer_groups', 'content__customers',
                'content__html_file').all()

        try:
            customer = Customer.objects.get(user=user)
            return Portal.objects.prefetch_related(
                'content__customer_groups', 'content__customers',
                'content__html_file').filter(
                Q(customers=customer) | Q(customer_groups__customers=customer)
            ).distinct()
        except Customer.DoesNotExist:
            pass

    def get_permissions(self):
        if self.request.method == 'POST':
            return [PortalPermissions()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
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


class PortalContentViewSet(CustomModelViewSet):
    def get_queryset(self):
        return models.PortalContent.objects.filter(portal_id=self.kwargs['portal_pk']).select_related('html_file', 'portal').prefetch_related('customers', 'customer_groups')

    def get_serializer_context(self):
        return {'portal_id': self.kwargs['portal_pk'], 'request': self.request}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.CreatePortalContentSerializer
        return serializers.PortalContentSerializer


class HTMLFileViewSet(CustomModelViewSet):
    queryset = models.HTMLFile.objects.all()
    serializer_class = serializers.HTMLFileSerializer


class CatalogViewSet(CustomModelViewSet):
    queryset = models.Catalog.objects.all()
    serializer_class = serializers.CatalogSerializer


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
    def get(self, request):
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

        file_transfers = get_queryset_for_models_with_files(
            FileTransfer).filter(date_filter)
        online_orders = get_queryset_for_models_with_files(
            Request).filter(date_filter)
        general_contacts = ContactInquiry.objects.filter(date_filter)

        def calculate_file_size(instance):
            file_size_in_bytes = sum(
                [file.file_size for file in instance.files.all() if file.file_size])
            if file_size_in_bytes >= 1024 * 1024:
                return f"{file_size_in_bytes / (1024 * 1024):.2f} MB"
            return f"{file_size_in_bytes / 1024:.2f} KB"

        def create_message(instance, title, attachments='n/a'):
            return {
                'id': instance.id,
                'Date': instance.created_at,
                'title_and_tracking': title,
                'From': instance.name,
                'Email': instance.email_address,
                'Attachments': attachments,
            }

        # File transfers
        for file_transfer in file_transfers:
            messages.append(create_message(
                file_transfer,
                'Online File Transfer',
                calculate_file_size(file_transfer)
            ))

        # Online orders
        for online_order in online_orders:
            title = 'Online Order' if online_order.this_is_an == 'Order Request' else 'Estimate Request'
            messages.append(create_message(
                online_order,
                title,
                calculate_file_size(online_order)
            ))

        # General contacts
        for general_contact in general_contacts:
            messages.append(create_message(
                general_contact,
                'General Contact',
            ))

        messages.sort(key=lambda x: x['Date'], reverse=True)

        return Response(messages)


class CatalogItemViewSet(ModelViewSet):
    """
    A viewset for viewing and editing catalog items.
    """

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT']:
            return CreateOrUpdateCatalogItemSerializer
        return CatalogItemSerializer

    def get_queryset(self):
        return CatalogItem.objects.filter(catalog_id=self.kwargs['catalog_pk']).prefetch_related('attributes__options')

    def get_serializer_context(self):
        return {'catalog_id': self.kwargs['catalog_pk']}

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

class CartViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Cart.objects.prefetch_related("items__catalog_item").all()
    serializer_class = CartSerializer


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk']).select_related("catalog_item")

    def get_serializer_context(self):
        return {"cart_id": self.kwargs["cart_pk"]}
