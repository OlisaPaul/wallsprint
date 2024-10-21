from django.shortcuts import render
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from .models import ContactInquiry, QuoteRequest, Image
from .serializers import ContactInquirySerializer, QuoteRequestSerializer, CreateQuoteRequestSerializer, ImageSerializer




class ContactInquiryViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ContactInquiry.objects.all()
    serializer_class = ContactInquirySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAdminUser()]




class ImageViewSet(ListModelMixin, GenericViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


class QuoteRequestViewSet(ModelViewSet, GenericViewSet):
    queryset = QuoteRequest.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateQuoteRequestSerializer
        return QuoteRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAdminUser()]
