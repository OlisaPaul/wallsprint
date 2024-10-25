from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import ContactInquiry, QuoteRequest, File


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_address', 'phone_number', 'created_at']
    search_fields = ['name', 'email_address']


@admin.register(File)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['path', "upload_date"]


class ImageInline(GenericTabularInline):
    model = File
    min_num = 1
    max_num = 10
    extra = 0


@admin.register(QuoteRequest)
class ProjectQuoteRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_address', 'project_name', 'created_at']
    search_fields = ['name', 'email_address', 'project_name']
    inlines = [ImageInline]
