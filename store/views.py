from django.shortcuts import render
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from .models import ContactInquiry, QuoteRequest, Image, Customer, Request
from .serializers import ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, ImageSerializer, CreateCustomerSerializer, CustomerSerializer, CreateRequestSerializer, RequestSerializer


class ContactInquiryViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ContactInquiry.objects.prefetch_related('images').all()
    serializer_class = ContactInquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAdminUser()]


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
        return [IsAdminUser()]


class RequestViewSet(ModelViewSet):
    queryset = Request.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRequestSerializer
        return RequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAdminUser()]


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.select_related('user').all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerSerializer
        return CreateCustomerSerializer

    serializer_class = CreateCustomerSerializer
