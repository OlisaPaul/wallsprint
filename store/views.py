from django.shortcuts import render
from django.db import models
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import IsAdminUser, AllowAny, DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import ContactInquiry, QuoteRequest, Image, Customer, Request
from .serializers import ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, ImageSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer
from .permissions import FullDjangoModelPermissions
from .mixins import HandleImagesMixin


class ContactInquiryViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ContactInquiry.objects.prefetch_related('images').all()
    serializer_class = ContactInquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


class ImageViewSet(ListModelMixin, GenericViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


class QuoteRequestViewSet(ModelViewSet, HandleImagesMixin):
    def get_queryset(self):
        content_type = ContentType.objects.get_for_model(QuoteRequest)
        
        return QuoteRequest.objects.prefetch_related(
            models.Prefetch(
                'images',
                queryset=Image.objects.filter(content_type=content_type)
            )
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateQuoteRequestSerializer
        return QuoteRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


class RequestViewSet(GenericViewSet, DestroyModelMixin, CreateModelMixin, ListModelMixin):
    queryset = Request.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRequestSerializer
        return RequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [FullDjangoModelPermissions()]


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.select_related('user').all()
    permission_classes = [FullDjangoModelPermissions]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerSerializer
        return CreateCustomerSerializer

    serializer_class = CreateCustomerSerializer
