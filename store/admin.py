from django.contrib import admin
from .models import ContactInquiry, QuoteRequest, Image


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_address', 'phone_number', 'created_at']
    search_fields = ['name', 'email_address']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['path', 'project', 'project']


class ImageInline(admin.TabularInline):
    model = Image
    min_num = 1
    max_num = 10
    extra = 0


@admin.register(QuoteRequest)
class ProjectQuoteRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_address', 'project_name', 'created_at']
    search_fields = ['name', 'email_address', 'project_name']
    inlines = [ImageInline]
