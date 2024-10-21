from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, GenericViewSet 
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from .models import ContactInquiry, ProjectQuoteRequest
from .serializers import ContactInquirySerializer

# Create your views here.

class ContactInquiryViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = ContactInquiry.objects.all()
    serializer_class = ContactInquirySerializer
