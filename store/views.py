import csv
from io import TextIOWrapper
from django.db import transaction
from django.shortcuts import render
from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import  AllowAny,  IsAuthenticated
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import ContactInquiry, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, Portal
from .serializers import ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, FileSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer, FileTransferSerializer, CreateFileTransferSerializer, UpdateCustomerSerializer, User, CSVUploadSerializer, CustomerGroupSerializer, CreateCustomerGroupSerializer, PortalSerializer, customer_fields
from .permissions import FullDjangoModelPermissions, create_permission_class
from .mixins import HandleImagesMixin
from .utils import get_queryset_for_models_with_files
from .utils import bulk_delete_objects, CustomModelViewSet
from store import models
from store import serializers

CanTransferFiles = create_permission_class('store.transfer_files')
PortalPermissions = create_permission_class('store.portals')


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
    permission_classes = [FullDjangoModelPermissions]

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

        serializer = CSVUploadSerializer(data=request.FILES)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        csv_content = serializer.validated_data['file']
        has_header = serializer.validated_data['has_header']

        csv_reader = csv.DictReader(csv_content.splitlines())
        rows = list(csv_reader)

        columns = ['name', 'email', 'password',
                   'username', 'is_active'] + customer_fields

        users = []
        errors = []
        customer_count = 0

        mapped_rows = []

        for row in rows:
            if not has_header:
                mapped_row = {
                    columns[index]: value for index, value in enumerate(row)}
                mapped_rows.append(mapped_row)
            else:
                mapped_rows.append(row)

        for row in mapped_row:
            serializer = CreateCustomerSerializer(data=row)
            if serializer.is_valid():
                email = row.get('email')
                name = row.get('name')
                password = row.get('password')
                username = email

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

                customer_data['pay_tax'] = bool(customer_data['pay_tax'])

                Customer.objects.create(user=user, **customer_data)
                customer_count += 1
            else:
                errors.append({**serializer.errors, "row": row})

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": f"{customer_count} customers created successfully."}, status=status.HTTP_201_CREATED)


class CustomerGroupViewSet(CustomModelViewSet):
    queryset = CustomerGroup.objects.prefetch_related('customers').all()
    permission_classes = [FullDjangoModelPermissions]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerGroupSerializer
        return CreateCustomerGroupSerializer


class PortalViewSet(CustomModelViewSet):
    queryset = Portal.objects.prefetch_related(
        'content__customer_groups', 'content__customers', 'content__html_file').all()
    
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
    queryset = models.PortalContent.objects.all()
    serializer_class = serializers.PortalContentSerializer


class HTMLFileViewSet(CustomModelViewSet):
    queryset = models.HTMLFile.objects.all()
    serializer_class = serializers.HTMLFileSerializer
