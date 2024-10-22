from django.shortcuts import render
from rest_framework.permissions import IsAdminUser, AllowAny, DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from .models import ContactInquiry, QuoteRequest, Image, Customer, Request
from .serializers import ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, ImageSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer
from .permissions import FullDjangoModelPermissions


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


class QuoteRequestViewSet(ModelViewSet):
    queryset = QuoteRequest.objects.all()

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
