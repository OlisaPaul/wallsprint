import csv
import os
import re
import json
from uuid import uuid4
import requests
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.validators import ValidationError
from io import TextIOWrapper
from django.core.mail import send_mail, EmailMultiAlternatives
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import AttributeOption, Attribute, Cart, CartItem, Catalog, CatalogItem, ContactInquiry, FileExchange, Page, OnlinePayment, OnlineProof, OrderItem, Portal, QuoteRequest, File, Customer, Request, FileTransfer, CustomerGroup, PortalContent, Order, OrderItem, PortalContentCatalog, Note, BillingInfo, Shipment, Transaction, ItemDetails, TemplateField, EditableCatalogItemFile
from .utils import create_instance_with_files, validate_catalog, save_item
from .signals import file_transferred
from decimal import Decimal
from django.template.loader import render_to_string
import xml.etree.ElementTree as ET

User = get_user_model()

load_dotenv()


def send_email(user, context, subject, template):
    message = render_to_string(template, context)
    send_mail(
        subject,
        message,
        os.getenv('EMAIL_HOST_USER'),
        [user.email],
        fail_silently=False,
        html_message=message
    )

def send_html_email_with_attachments(subject, context, template_name, from_email, recipient_list, files=[]):
    # Render HTML and plain-text bodies
    html_content = render_to_string(template_name, context)
    # text_content = render_to_string(template_name, context)

    # Create email with HTML + plain text
    email = EmailMultiAlternatives(
        subject=subject,
        body='',
        from_email=from_email,
        to=recipient_list,
    )
    email.attach_alternative(html_content, "text/html")
    print(len(files))

    existing_filenames = set()

    for file in files:
        url = file.get("url")
        name = file.get("name")

        if not url:
            print("Skipping file with no URL.")
            continue

        try:
            response = requests.get(url)
            print(f"Fetching: {url} - Status: {response.status_code}")

            if response.status_code == 200:
                filename = name or os.path.basename(url.split('?')[0])
                
                # Ensure unique filename
                if filename in existing_filenames:
                    base, ext = os.path.splitext(filename)
                    count = 1
                    while f"{base}_{count}{ext}" in existing_filenames:
                        count += 1
                    filename = f"{base}_{count}{ext}"
                existing_filenames.add(filename)

                content_type = response.headers.get("Content-Type", "application/octet-stream")
                email.attach(filename, response.content, content_type)
                print(f"Attached: {filename} ({len(response.content)} bytes)")
            else:
                print(f"Failed to download: {url}")
        except Exception as e:
            print(f"Error attaching {url}: {e}")

    email.send()

SVG_TEMPLATE = """<svg width="336" height="192" viewBox="0 0 336 192" fill="none" xmlns="http://www.w3.org/2000/svg">
 <g clip-path="url(#clip0_407_397)">
 <path d="M326 0H10C4.47715 0 0 4.47715 0 10V182C0 187.523 4.47715 192 10 192H326C331.523 192 336 187.523 336 182V10C336 4.47715 331.523 0 326 0Z" fill="white"/>
 <path fill-rule="evenodd" clip-rule="evenodd" d="M189.5 78.5C174.928 55.3334 160.076 29.6536 159.344 0H185.248C189.718 16.7575 198.137 40.6042 213.001 73C233.451 117.572 232.678 160.712 226.056 192H201.331C214.436 164.7 222.101 130.327 189.5 78.5Z" fill="#2BBE9B"/>
 <path fill-rule="evenodd" clip-rule="evenodd" d="M195.185 79C180.531 55.7033 165.594 29.8651 165.018 0H190.8C195.236 16.782 203.673 40.7807 218.685 73.5C239.027 117.835 238.37 160.753 231.846 192H207.255C220.213 164.781 227.587 130.511 195.185 79Z" fill="#287B67"/>
 <path fill-rule="evenodd" clip-rule="evenodd" d="M336.001 0H172.777C171.281 27.4658 180.852 49.7127 195.186 72.5C227.841 124.413 217.831 162.309 203.151 192H336.001V0Z" fill="#141717"/>
 <path d="M287 132H252V167H287V132Z" fill="white"/>
 <path d="M255.135 133.929H253.93V135.134H255.135V133.929Z" fill="black"/>
 <path d="M256.34 133.929H255.135V135.134H256.34V133.929Z" fill="black"/>
 <path d="M257.546 133.929H256.34V135.134H257.546V133.929Z" fill="black"/>
 <path d="M258.753 133.929H257.547V135.134H258.753V133.929Z" fill="black"/>
 <path d="M259.958 133.929H258.752V135.134H259.958V133.929Z" fill="black"/>
 <path d="M261.163 133.929H259.957V135.134H261.163V133.929Z" fill="black"/>
 <path d="M262.368 133.929H261.162V135.134H262.368V133.929Z" fill="black"/>
 <path d="M264.78 133.929H263.574V135.134H264.78V133.929Z" fill="black"/>
 <path d="M268.397 133.929H267.191V135.134H268.397V133.929Z" fill="black"/>
 <path d="M269.602 133.929H268.396V135.134H269.602V133.929Z" fill="black"/>
 <path d="M274.426 133.929H273.221V135.134H274.426V133.929Z" fill="black"/>
 <path d="M276.837 133.929H275.631V135.134H276.837V133.929Z" fill="black"/>
 <path d="M278.044 133.929H276.838V135.134H278.044V133.929Z" fill="black"/>
 <path d="M279.249 133.929H278.043V135.134H279.249V133.929Z" fill="black"/>
 <path d="M280.454 133.929H279.248V135.134H280.454V133.929Z" fill="black"/>
 <path d="M281.659 133.929H280.453V135.134H281.659V133.929Z" fill="black"/>
 <path d="M282.864 133.929H281.658V135.134H282.864V133.929Z" fill="black"/>
 <path d="M284.071 133.929H282.865V135.134H284.071V133.929Z" fill="black"/>
 <path d="M255.135 135.135H253.93V136.34H255.135V135.135Z" fill="black"/>
 <path d="M262.368 135.135H261.162V136.34H262.368V135.135Z" fill="black"/>
 <path d="M265.985 135.135H264.779V136.34H265.985V135.135Z" fill="black"/>
 <path d="M267.19 135.135H265.984V136.34H267.19V135.135Z" fill="black"/>
 <path d="M268.397 135.135H267.191V136.34H268.397V135.135Z" fill="black"/>
 <path d="M269.602 135.135H268.396V136.34H269.602V135.135Z" fill="black"/>
 <path d="M276.837 135.135H275.631V136.34H276.837V135.135Z" fill="black"/>
 <path d="M284.071 135.135H282.865V136.34H284.071V135.135Z" fill="black"/>
 <path d="M255.135 136.34H253.93V137.546H255.135V136.34Z" fill="black"/>
 <path d="M257.546 136.34H256.34V137.546H257.546V136.34Z" fill="black"/>
 <path d="M258.753 136.34H257.547V137.546H258.753V136.34Z" fill="black"/>
 <path d="M259.958 136.34H258.752V137.546H259.958V136.34Z" fill="black"/>
 <path d="M262.368 136.34H261.162V137.546H262.368V136.34Z" fill="black"/>
 <path d="M264.78 136.34H263.574V137.546H264.78V136.34Z" fill="black"/>
 <path d="M269.602 136.34H268.396V137.546H269.602V136.34Z" fill="black"/>
 <path d="M270.809 136.34H269.604V137.546H270.809V136.34Z" fill="black"/>
 <path d="M272.014 136.34H270.809V137.546H272.014V136.34Z" fill="black"/>
 <path d="M276.837 136.34H275.631V137.546H276.837V136.34Z" fill="black"/>
 <path d="M279.249 136.34H278.043V137.546H279.249V136.34Z" fill="black"/>
 <path d="M280.454 136.34H279.248V137.546H280.454V136.34Z" fill="black"/>
 <path d="M281.659 136.34H280.453V137.546H281.659V136.34Z" fill="black"/>
 <path d="M284.071 136.34H282.865V137.546H284.071V136.34Z" fill="black"/>
 <path d="M255.135 137.546H253.93V138.752H255.135V137.546Z" fill="black"/>
 <path d="M257.546 137.546H256.34V138.752H257.546V137.546Z" fill="black"/>
 <path d="M258.753 137.546H257.547V138.752H258.753V137.546Z" fill="black"/>
 <path d="M259.958 137.546H258.752V138.752H259.958V137.546Z" fill="black"/>
 <path d="M262.368 137.546H261.162V138.752H262.368V137.546Z" fill="black"/>
 <path d="M264.78 137.546H263.574V138.752H264.78V137.546Z" fill="black"/>
 <path d="M265.985 137.546H264.779V138.752H265.985V137.546Z" fill="black"/>
 <path d="M268.397 137.546H267.191V138.752H268.397V137.546Z" fill="black"/>
 <path d="M269.602 137.546H268.396V138.752H269.602V137.546Z" fill="black"/>
 <path d="M270.809 137.546H269.604V138.752H270.809V137.546Z" fill="black"/>
 <path d="M273.219 137.546H272.014V138.752H273.219V137.546Z" fill="black"/>
 <path d="M276.837 137.546H275.631V138.752H276.837V137.546Z" fill="black"/>
 <path d="M279.249 137.546H278.043V138.752H279.249V137.546Z" fill="black"/>
 <path d="M280.454 137.546H279.248V138.752H280.454V137.546Z" fill="black"/>
 <path d="M281.659 137.546H280.453V138.752H281.659V137.546Z" fill="black"/>
 <path d="M284.071 137.546H282.865V138.752H284.071V137.546Z" fill="black"/>
 <path d="M255.135 138.752H253.93V139.958H255.135V138.752Z" fill="black"/>
 <path d="M257.546 138.752H256.34V139.958H257.546V138.752Z" fill="black"/>
 <path d="M258.753 138.752H257.547V139.958H258.753V138.752Z" fill="black"/>
 <path d="M259.958 138.752H258.752V139.958H259.958V138.752Z" fill="black"/>
 <path d="M262.368 138.752H261.162V139.958H262.368V138.752Z" fill="black"/>
 <path d="M264.78 138.752H263.574V139.958H264.78V138.752Z" fill="black"/>
 <path d="M265.985 138.752H264.779V139.958H265.985V138.752Z" fill="black"/>
 <path d="M269.602 138.752H268.396V139.958H269.602V138.752Z" fill="black"/>
 <path d="M270.809 138.752H269.604V139.958H270.809V138.752Z" fill="black"/>
 <path d="M272.014 138.752H270.809V139.958H272.014V138.752Z" fill="black"/>
 <path d="M273.219 138.752H272.014V139.958H273.219V138.752Z" fill="black"/>
 <path d="M274.426 138.752H273.221V139.958H274.426V138.752Z" fill="black"/>
 <path d="M276.837 138.752H275.631V139.958H276.837V138.752Z" fill="black"/>
 <path d="M279.249 138.752H278.043V139.958H279.249V138.752Z" fill="black"/>
 <path d="M280.454 138.752H279.248V139.958H280.454V138.752Z" fill="black"/>
 <path d="M281.659 138.752H280.453V139.958H281.659V138.752Z" fill="black"/>
 <path d="M284.071 138.752H282.865V139.958H284.071V138.752Z" fill="black"/>
 <path d="M255.135 139.958H253.93V141.164H255.135V139.958Z" fill="black"/>
 <path d="M262.368 139.958H261.162V141.164H262.368V139.958Z" fill="black"/>
 <path d="M265.985 139.958H264.779V141.164H265.985V139.958Z" fill="black"/>
 <path d="M269.602 139.958H268.396V141.164H269.602V139.958Z" fill="black"/>
 <path d="M270.809 139.958H269.604V141.164H270.809V139.958Z" fill="black"/>
 <path d="M272.014 139.958H270.809V141.164H272.014V139.958Z" fill="black"/>
 <path d="M276.837 139.958H275.631V141.164H276.837V139.958Z" fill="black"/>
 <path d="M284.071 139.958H282.865V141.164H284.071V139.958Z" fill="black"/>
 <path d="M255.135 141.163H253.93V142.369H255.135V141.163Z" fill="black"/>
 <path d="M256.34 141.163H255.135V142.369H256.34V141.163Z" fill="black"/>
 <path d="M257.546 141.163H256.34V142.369H257.546V141.163Z" fill="black"/>
 <path d="M258.753 141.163H257.547V142.369H258.753V141.163Z" fill="black"/>
 <path d="M259.958 141.163H258.752V142.369H259.958V141.163Z" fill="black"/>
 <path d="M261.163 141.163H259.957V142.369H261.163V141.163Z" fill="black"/>
 <path d="M262.368 141.163H261.162V142.369H262.368V141.163Z" fill="black"/>
 <path d="M264.78 141.163H263.574V142.369H264.78V141.163Z" fill="black"/>
 <path d="M267.19 141.163H265.984V142.369H267.19V141.163Z" fill="black"/>
 <path d="M269.602 141.163H268.396V142.369H269.602V141.163Z" fill="black"/>
 <path d="M272.014 141.163H270.809V142.369H272.014V141.163Z" fill="black"/>
 <path d="M274.426 141.163H273.221V142.369H274.426V141.163Z" fill="black"/>
 <path d="M276.837 141.163H275.631V142.369H276.837V141.163Z" fill="black"/>
 <path d="M278.044 141.163H276.838V142.369H278.044V141.163Z" fill="black"/>
 <path d="M279.249 141.163H278.043V142.369H279.249V141.163Z" fill="black"/>
 <path d="M280.454 141.163H279.248V142.369H280.454V141.163Z" fill="black"/>
 <path d="M281.659 141.163H280.453V142.369H281.659V141.163Z" fill="black"/>
 <path d="M282.864 141.163H281.658V142.369H282.864V141.163Z" fill="black"/>
 <path d="M284.071 141.163H282.865V142.369H284.071V141.163Z" fill="black"/>
 <path d="M265.985 142.369H264.779V143.575H265.985V142.369Z" fill="black"/>
 <path d="M269.602 142.369H268.396V143.575H269.602V142.369Z" fill="black"/>
 <path d="M273.219 142.369H272.014V143.575H273.219V142.369Z" fill="black"/>
 <path d="M274.426 142.369H273.221V143.575H274.426V142.369Z" fill="black"/>
 <path d="M255.135 143.574H253.93V144.78H255.135V143.574Z" fill="black"/>
 <path d="M256.34 143.574H255.135V144.78H256.34V143.574Z" fill="black"/>
 <path d="M257.546 143.574H256.34V144.78H257.546V143.574Z" fill="black"/>
 <path d="M258.753 143.574H257.547V144.78H258.753V143.574Z" fill="black"/>
 <path d="M262.368 143.574H261.162V144.78H262.368V143.574Z" fill="black"/>
 <path d="M264.78 143.574H263.574V144.78H264.78V143.574Z" fill="black"/>
 <path d="M268.397 143.574H267.191V144.78H268.397V143.574Z" fill="black"/>
 <path d="M272.014 143.574H270.809V144.78H272.014V143.574Z" fill="black"/>
 <path d="M273.219 143.574H272.014V144.78H273.219V143.574Z" fill="black"/>
 <path d="M274.426 143.574H273.221V144.78H274.426V143.574Z" fill="black"/>
 <path d="M275.631 143.574H274.426V144.78H275.631V143.574Z" fill="black"/>
 <path d="M279.249 143.574H278.043V144.78H279.249V143.574Z" fill="black"/>
 <path d="M280.454 143.574H279.248V144.78H280.454V143.574Z" fill="black"/>
 <path d="M281.659 143.574H280.453V144.78H281.659V143.574Z" fill="black"/>
 <path d="M284.071 143.574H282.865V144.78H284.071V143.574Z" fill="black"/>
 <path d="M257.546 144.78H256.34V145.986H257.546V144.78Z" fill="black"/>
 <path d="M258.753 144.78H257.547V145.986H258.753V144.78Z" fill="black"/>
 <path d="M259.958 144.78H258.752V145.986H259.958V144.78Z" fill="black"/>
 <path d="M263.573 144.78H262.367V145.986H263.573V144.78Z" fill="black"/>
 <path d="M264.78 144.78H263.574V145.986H264.78V144.78Z" fill="black"/>
 <path d="M265.985 144.78H264.779V145.986H265.985V144.78Z" fill="black"/>
 <path d="M268.397 144.78H267.191V145.986H268.397V144.78Z" fill="black"/>
 <path d="M270.809 144.78H269.604V145.986H270.809V144.78Z" fill="black"/>
 <path d="M274.426 144.78H273.221V145.986H274.426V144.78Z" fill="black"/>
 <path d="M275.631 144.78H274.426V145.986H275.631V144.78Z" fill="black"/>
 <path d="M278.044 144.78H276.838V145.986H278.044V144.78Z" fill="black"/>
 <path d="M282.864 144.78H281.658V145.986H282.864V144.78Z" fill="black"/>
 <path d="M255.135 145.986H253.93V147.192H255.135V145.986Z" fill="black"/>
 <path d="M256.34 145.986H255.135V147.192H256.34V145.986Z" fill="black"/>
 <path d="M261.163 145.986H259.957V147.192H261.163V145.986Z" fill="black"/>
 <path d="M262.368 145.986H261.162V147.192H262.368V145.986Z" fill="black"/>
 <path d="M264.78 145.986H263.574V147.192H264.78V145.986Z" fill="black"/>
 <path d="M268.397 145.986H267.191V147.192H268.397V145.986Z" fill="black"/>
 <path d="M269.602 145.986H268.396V147.192H269.602V145.986Z" fill="black"/>
 <path d="M274.426 145.986H273.221V147.192H274.426V145.986Z" fill="black"/>
 <path d="M278.044 145.986H276.838V147.192H278.044V145.986Z" fill="black"/>
 <path d="M255.135 147.191H253.93V148.397H255.135V147.191Z" fill="black"/>
 <path d="M256.34 147.191H255.135V148.397H256.34V147.191Z" fill="black"/>
 <path d="M261.163 147.191H259.957V148.397H261.163V147.191Z" fill="black"/>
 <path d="M268.397 147.191H267.191V148.397H268.397V147.191Z" fill="black"/>
 <path d="M270.809 147.191H269.604V148.397H270.809V147.191Z" fill="black"/>
 <path d="M272.014 147.191H270.809V148.397H272.014V147.191Z" fill="black"/>
 <path d="M273.219 147.191H272.014V148.397H273.219V147.191Z" fill="black"/>
 <path d="M274.426 147.191H273.221V148.397H274.426V147.191Z" fill="black"/>
 <path d="M275.631 147.191H274.426V148.397H275.631V147.191Z" fill="black"/>
 <path d="M276.837 147.191H275.631V148.397H276.837V147.191Z" fill="black"/>
 <path d="M280.454 147.191H279.248V148.397H280.454V147.191Z" fill="black"/>
 <path d="M281.659 147.191H280.453V148.397H281.659V147.191Z" fill="black"/>
 <path d="M256.34 148.397H255.135V149.603H256.34V148.397Z" fill="black"/>
 <path d="M257.546 148.397H256.34V149.603H257.546V148.397Z" fill="black"/>
 <path d="M258.753 148.397H257.547V149.603H258.753V148.397Z" fill="black"/>
 <path d="M259.958 148.397H258.752V149.603H259.958V148.397Z" fill="black"/>
 <path d="M261.163 148.397H259.957V149.603H261.163V148.397Z" fill="black"/>
 <path d="M262.368 148.397H261.162V149.603H262.368V148.397Z" fill="black"/>
 <path d="M263.573 148.397H262.367V149.603H263.573V148.397Z" fill="black"/>
 <path d="M264.78 148.397H263.574V149.603H264.78V148.397Z" fill="black"/>
 <path d="M265.985 148.397H264.779V149.603H265.985V148.397Z" fill="black"/>
 <path d="M269.602 148.397H268.396V149.603H269.602V148.397Z" fill="black"/>
 <path d="M270.809 148.397H269.604V149.603H270.809V148.397Z" fill="black"/>
 <path d="M272.014 148.397H270.809V149.603H272.014V148.397Z" fill="black"/>
 <path d="M273.219 148.397H272.014V149.603H273.219V148.397Z" fill="black"/>
 <path d="M275.631 148.397H274.426V149.603H275.631V148.397Z" fill="black"/>
 <path d="M276.837 148.397H275.631V149.603H276.837V148.397Z" fill="black"/>
 <path d="M278.044 148.397H276.838V149.603H278.044V148.397Z" fill="black"/>
 <path d="M279.249 148.397H278.043V149.603H279.249V148.397Z" fill="black"/>
 <path d="M281.659 148.397H280.453V149.603H281.659V148.397Z" fill="black"/>
 <path d="M282.864 148.397H281.658V149.603H282.864V148.397Z" fill="black"/>
 <path d="M284.071 148.397H282.865V149.603H284.071V148.397Z" fill="black"/>
 <path d="M257.546 149.603H256.34V150.808H257.546V149.603Z" fill="black"/>
 <path d="M258.753 149.603H257.547V150.808H258.753V149.603Z" fill="black"/>
 <path d="M261.163 149.603H259.957V150.808H261.163V149.603Z" fill="black"/>
 <path d="M267.19 149.603H265.984V150.808H267.19V149.603Z" fill="black"/>
 <path d="M269.602 149.603H268.396V150.808H269.602V149.603Z" fill="black"/>
 <path d="M270.809 149.603H269.604V150.808H270.809V149.603Z" fill="black"/>
 <path d="M272.014 149.603H270.809V150.808H272.014V149.603Z" fill="black"/>
 <path d="M273.219 149.603H272.014V150.808H273.219V149.603Z" fill="black"/>
 <path d="M274.426 149.603H273.221V150.808H274.426V149.603Z" fill="black"/>
 <path d="M276.837 149.603H275.631V150.808H276.837V149.603Z" fill="black"/>
 <path d="M278.044 149.603H276.838V150.808H278.044V149.603Z" fill="black"/>
 <path d="M279.249 149.603H278.043V150.808H279.249V149.603Z" fill="black"/>
 <path d="M284.071 149.603H282.865V150.808H284.071V149.603Z" fill="black"/>
 <path d="M256.34 150.809H255.135V152.014H256.34V150.809Z" fill="black"/>
 <path d="M257.546 150.809H256.34V152.014H257.546V150.809Z" fill="black"/>
 <path d="M259.958 150.809H258.752V152.014H259.958V150.809Z" fill="black"/>
 <path d="M261.163 150.809H259.957V152.014H261.163V150.809Z" fill="black"/>
 <path d="M262.368 150.809H261.162V152.014H262.368V150.809Z" fill="black"/>
 <path d="M265.985 150.809H264.779V152.014H265.985V150.809Z" fill="black"/>
 <path d="M272.014 150.809H270.809V152.014H272.014V150.809Z" fill="black"/>
 <path d="M274.426 150.809H273.221V152.014H274.426V150.809Z" fill="black"/>
 <path d="M275.631 150.809H274.426V152.014H275.631V150.809Z" fill="black"/>
 <path d="M279.249 150.809H278.043V152.014H279.249V150.809Z" fill="black"/>
 <path d="M281.659 150.809H280.453V152.014H281.659V150.809Z" fill="black"/>
 <path d="M282.864 150.809H281.658V152.014H282.864V150.809Z" fill="black"/>
 <path d="M255.135 152.014H253.93V153.219H255.135V152.014Z" fill="black"/>
 <path d="M257.546 152.014H256.34V153.219H257.546V152.014Z" fill="black"/>
 <path d="M258.753 152.014H257.547V153.219H258.753V152.014Z" fill="black"/>
 <path d="M259.958 152.014H258.752V153.219H259.958V152.014Z" fill="black"/>
 <path d="M261.163 152.014H259.957V153.219H261.163V152.014Z" fill="black"/>
 <path d="M263.573 152.014H262.367V153.219H263.573V152.014Z" fill="black"/>
 <path d="M264.78 152.014H263.574V153.219H264.78V152.014Z" fill="black"/>
 <path d="M265.985 152.014H264.779V153.219H265.985V152.014Z" fill="black"/>
 <path d="M267.19 152.014H265.984V153.219H267.19V152.014Z" fill="black"/>
 <path d="M268.397 152.014H267.191V153.219H268.397V152.014Z" fill="black"/>
 <path d="M272.014 152.014H270.809V153.219H272.014V152.014Z" fill="black"/>
 <path d="M275.631 152.014H274.426V153.219H275.631V152.014Z" fill="black"/>
 <path d="M278.044 152.014H276.838V153.219H278.044V152.014Z" fill="black"/>
 <path d="M279.249 152.014H278.043V153.219H279.249V152.014Z" fill="black"/>
 <path d="M284.071 152.014H282.865V153.219H284.071V152.014Z" fill="black"/>
 <path d="M257.546 153.22H256.34V154.425H257.546V153.22Z" fill="black"/>
 <path d="M261.163 153.22H259.957V154.425H261.163V153.22Z" fill="black"/>
 <path d="M262.368 153.22H261.162V154.425H262.368V153.22Z" fill="black"/>
 <path d="M264.78 153.22H263.574V154.425H264.78V153.22Z" fill="black"/>
 <path d="M270.809 153.22H269.604V154.425H270.809V153.22Z" fill="black"/>
 <path d="M274.426 153.22H273.221V154.425H274.426V153.22Z" fill="black"/>
 <path d="M275.631 153.22H274.426V154.425H275.631V153.22Z" fill="black"/>
 <path d="M276.837 153.22H275.631V154.425H276.837V153.22Z" fill="black"/>
 <path d="M278.044 153.22H276.838V154.425H278.044V153.22Z" fill="black"/>
 <path d="M279.249 153.22H278.043V154.425H279.249V153.22Z" fill="black"/>
 <path d="M280.454 153.22H279.248V154.425H280.454V153.22Z" fill="black"/>
 <path d="M281.659 153.22H280.453V154.425H281.659V153.22Z" fill="black"/>
 <path d="M282.864 153.22H281.658V154.425H282.864V153.22Z" fill="black"/>
 <path d="M284.071 153.22H282.865V154.425H284.071V153.22Z" fill="black"/>
 <path d="M264.78 154.426H263.574V155.631H264.78V154.426Z" fill="black"/>
 <path d="M265.985 154.426H264.779V155.631H265.985V154.426Z" fill="black"/>
 <path d="M267.19 154.426H265.984V155.631H267.19V154.426Z" fill="black"/>
 <path d="M268.397 154.426H267.191V155.631H268.397V154.426Z" fill="black"/>
 <path d="M273.219 154.426H272.014V155.631H273.219V154.426Z" fill="black"/>
 <path d="M274.426 154.426H273.221V155.631H274.426V154.426Z" fill="black"/>
 <path d="M279.249 154.426H278.043V155.631H279.249V154.426Z" fill="black"/>
 <path d="M281.659 154.426H280.453V155.631H281.659V154.426Z" fill="black"/>
 <path d="M284.071 154.426H282.865V155.631H284.071V154.426Z" fill="black"/>
 <path d="M255.135 155.631H253.93V156.837H255.135V155.631Z" fill="black"/>
 <path d="M256.34 155.631H255.135V156.837H256.34V155.631Z" fill="black"/>
 <path d="M257.546 155.631H256.34V156.837H257.546V155.631Z" fill="black"/>
 <path d="M258.753 155.631H257.547V156.837H258.753V155.631Z" fill="black"/>
 <path d="M259.958 155.631H258.752V156.837H259.958V155.631Z" fill="black"/>
 <path d="M261.163 155.631H259.957V156.837H261.163V155.631Z" fill="black"/>
 <path d="M262.368 155.631H261.162V156.837H262.368V155.631Z" fill="black"/>
 <path d="M265.985 155.631H264.779V156.837H265.985V155.631Z" fill="black"/>
 <path d="M270.809 155.631H269.604V156.837H270.809V155.631Z" fill="black"/>
 <path d="M272.014 155.631H270.809V156.837H272.014V155.631Z" fill="black"/>
 <path d="M274.426 155.631H273.221V156.837H274.426V155.631Z" fill="black"/>
 <path d="M276.837 155.631H275.631V156.837H276.837V155.631Z" fill="black"/>
 <path d="M279.249 155.631H278.043V156.837H279.249V155.631Z" fill="black"/>
 <path d="M281.659 155.631H280.453V156.837H281.659V155.631Z" fill="black"/>
 <path d="M282.864 155.631H281.658V156.837H282.864V155.631Z" fill="black"/>
 <path d="M284.071 155.631H282.865V156.837H284.071V155.631Z" fill="black"/>
 <path d="M255.135 156.837H253.93V158.043H255.135V156.837Z" fill="black"/>
 <path d="M262.368 156.837H261.162V158.043H262.368V156.837Z" fill="black"/>
 <path d="M265.985 156.837H264.779V158.043H265.985V156.837Z" fill="black"/>
 <path d="M268.397 156.837H267.191V158.043H268.397V156.837Z" fill="black"/>
 <path d="M272.014 156.837H270.809V158.043H272.014V156.837Z" fill="black"/>
 <path d="M273.219 156.837H272.014V158.043H273.219V156.837Z" fill="black"/>
 <path d="M274.426 156.837H273.221V158.043H274.426V156.837Z" fill="black"/>
 <path d="M279.249 156.837H278.043V158.043H279.249V156.837Z" fill="black"/>
 <path d="M282.864 156.837H281.658V158.043H282.864V156.837Z" fill="black"/>
 <path d="M284.071 156.837H282.865V158.043H284.071V156.837Z" fill="black"/>
 <path d="M255.135 158.042H253.93V159.248H255.135V158.042Z" fill="black"/>
 <path d="M257.546 158.042H256.34V159.248H257.546V158.042Z" fill="black"/>
 <path d="M258.753 158.042H257.547V159.248H258.753V158.042Z" fill="black"/>
 <path d="M259.958 158.042H258.752V159.248H259.958V158.042Z" fill="black"/>
 <path d="M262.368 158.042H261.162V159.248H262.368V158.042Z" fill="black"/>
 <path d="M265.985 158.042H264.779V159.248H265.985V158.042Z" fill="black"/>
 <path d="M268.397 158.042H267.191V159.248H268.397V158.042Z" fill="black"/>
 <path d="M269.602 158.042H268.396V159.248H269.602V158.042Z" fill="black"/>
 <path d="M272.014 158.042H270.809V159.248H272.014V158.042Z" fill="black"/>
 <path d="M274.426 158.042H273.221V159.248H274.426V158.042Z" fill="black"/>
 <path d="M275.631 158.042H274.426V159.248H275.631V158.042Z" fill="black"/>
 <path d="M276.837 158.042H275.631V159.248H276.837V158.042Z" fill="black"/>
 <path d="M278.044 158.042H276.838V159.248H278.044V158.042Z" fill="black"/>
 <path d="M279.249 158.042H278.043V159.248H279.249V158.042Z" fill="black"/>
 <path d="M280.454 158.042H279.248V159.248H280.454V158.042Z" fill="black"/>
 <path d="M282.864 158.042H281.658V159.248H282.864V158.042Z" fill="black"/>
 <path d="M284.071 158.042H282.865V159.248H284.071V158.042Z" fill="black"/>
 <path d="M255.135 159.249H253.93V160.455H255.135V159.249Z" fill="black"/>
 <path d="M257.546 159.249H256.34V160.455H257.546V159.249Z" fill="black"/>
 <path d="M258.753 159.249H257.547V160.455H258.753V159.249Z" fill="black"/>
 <path d="M259.958 159.249H258.752V160.455H259.958V159.249Z" fill="black"/>
 <path d="M262.368 159.249H261.162V160.455H262.368V159.249Z" fill="black"/>
 <path d="M264.78 159.249H263.574V160.455H264.78V159.249Z" fill="black"/>
 <path d="M268.397 159.249H267.191V160.455H268.397V159.249Z" fill="black"/>
 <path d="M270.809 159.249H269.604V160.455H270.809V159.249Z" fill="black"/>
 <path d="M276.837 159.249H275.631V160.455H276.837V159.249Z" fill="black"/>
 <path d="M279.249 159.249H278.043V160.455H279.249V159.249Z" fill="black"/>
 <path d="M280.454 159.249H279.248V160.455H280.454V159.249Z" fill="black"/>
 <path d="M281.659 159.249H280.453V160.455H281.659V159.249Z" fill="black"/>
 <path d="M282.864 159.249H281.658V160.455H282.864V159.249Z" fill="black"/>
 <path d="M284.071 159.249H282.865V160.455H284.071V159.249Z" fill="black"/>
 <path d="M255.135 160.454H253.93V161.66H255.135V160.454Z" fill="black"/>
 <path d="M257.546 160.454H256.34V161.66H257.546V160.454Z" fill="black"/>
 <path d="M258.753 160.454H257.547V161.66H258.753V160.454Z" fill="black"/>
 <path d="M259.958 160.454H258.752V161.66H259.958V160.454Z" fill="black"/>
 <path d="M262.368 160.454H261.162V161.66H262.368V160.454Z" fill="black"/>
 <path d="M264.78 160.454H263.574V161.66H264.78V160.454Z" fill="black"/>
 <path d="M265.985 160.454H264.779V161.66H265.985V160.454Z" fill="black"/>
 <path d="M267.19 160.454H265.984V161.66H267.19V160.454Z" fill="black"/>
 <path d="M268.397 160.454H267.191V161.66H268.397V160.454Z" fill="black"/>
 <path d="M269.602 160.454H268.396V161.66H269.602V160.454Z" fill="black"/>
 <path d="M270.809 160.454H269.604V161.66H270.809V160.454Z" fill="black"/>
 <path d="M272.014 160.454H270.809V161.66H272.014V160.454Z" fill="black"/>
 <path d="M275.631 160.454H274.426V161.66H275.631V160.454Z" fill="black"/>
 <path d="M276.837 160.454H275.631V161.66H276.837V160.454Z" fill="black"/>
 <path d="M279.249 160.454H278.043V161.66H279.249V160.454Z" fill="black"/>
 <path d="M281.659 160.454H280.453V161.66H281.659V160.454Z" fill="black"/>
 <path d="M282.864 160.454H281.658V161.66H282.864V160.454Z" fill="black"/>
 <path d="M255.135 161.66H253.93V162.866H255.135V161.66Z" fill="black"/>
 <path d="M262.368 161.66H261.162V162.866H262.368V161.66Z" fill="black"/>
 <path d="M264.78 161.66H263.574V162.866H264.78V161.66Z" fill="black"/>
 <path d="M267.19 161.66H265.984V162.866H267.19V161.66Z" fill="black"/>
 <path d="M269.602 161.66H268.396V162.866H269.602V161.66Z" fill="black"/>
 <path d="M270.809 161.66H269.604V162.866H270.809V161.66Z" fill="black"/>
 <path d="M272.014 161.66H270.809V162.866H272.014V161.66Z" fill="black"/>
 <path d="M273.219 161.66H272.014V162.866H273.219V161.66Z" fill="black"/>
 <path d="M275.631 161.66H274.426V162.866H275.631V161.66Z" fill="black"/>
 <path d="M276.837 161.66H275.631V162.866H276.837V161.66Z" fill="black"/>
 <path d="M279.249 161.66H278.043V162.866H279.249V161.66Z" fill="black"/>
 <path d="M281.659 161.66H280.453V162.866H281.659V161.66Z" fill="black"/>
 <path d="M255.135 162.865H253.93V164.071H255.135V162.865Z" fill="black"/>
 <path d="M256.34 162.865H255.135V164.071H256.34V162.865Z" fill="black"/>
 <path d="M257.546 162.865H256.34V164.071H257.546V162.865Z" fill="black"/>
 <path d="M258.753 162.865H257.547V164.071H258.753V162.865Z" fill="black"/>
 <path d="M259.958 162.865H258.752V164.071H259.958V162.865Z" fill="black"/>
 <path d="M261.163 162.865H259.957V164.071H261.163V162.865Z" fill="black"/>
 <path d="M262.368 162.865H261.162V164.071H262.368V162.865Z" fill="black"/>
 <path d="M264.78 162.865H263.574V164.071H264.78V162.865Z" fill="black"/>
 <path d="M269.602 162.865H268.396V164.071H269.602V162.865Z" fill="black"/>
 <path d="M270.809 162.865H269.604V164.071H270.809V162.865Z" fill="black"/>
 <path d="M272.014 162.865H270.809V164.071H272.014V162.865Z" fill="black"/>
 <path d="M278.044 162.865H276.838V164.071H278.044V162.865Z" fill="black"/>
 <path d="M279.249 162.865H278.043V164.071H279.249V162.865Z" fill="black"/>
 <path d="M280.454 162.865H279.248V164.071H280.454V162.865Z" fill="black"/>
 <path d="M281.659 162.865H280.453V164.071H281.659V162.865Z" fill="black"/>
 <path d="M282.864 162.865H281.658V164.071H282.864V162.865Z" fill="black"/>
 <path d="M284.071 162.865H282.865V164.071H284.071V162.865Z" fill="black"/>
 <mask id="mask0_407_397" style="mask-type:luminance" maskUnits="userSpaceOnUse" x="190" y="25" width="22" height="22">
 <path d="M212 25H190V47H212V25Z" fill="white"/>
 </mask>
 <g mask="url(#mask0_407_397)">
 <path d="M196.416 46.4339C185.119 45.2116 189.578 22.6003 203.254 30.2395C199.092 28.406 187.2 38.4894 196.416 46.4339Z" fill="#0071BC"/>
 <path d="M206.314 37.2227H211.368C210.476 41.1949 207.522 43.3016 206.314 43.9449C197.134 48.8338 195.053 39.3615 195.611 38.1393C196.242 45.1671 206.053 40.5838 206.314 37.2227Z" fill="#2BBE9B"/>
 <path d="M211.702 34.4722C210.751 22.0056 200.801 24.5926 195.945 27.4445C204.507 25.4889 206.648 31.3148 206.648 34.4722C208.432 34.5741 211.94 34.7167 211.702 34.4722Z" fill="#F7931E"/>
 </g>
 <text fill="white" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="6" letter-spacing="0em"><tspan x="224" y="44.6818">{{tagline}}</tspan></text>
 <text fill="white" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="12" font-weight="bold" letter-spacing="0em"><tspan x="224" y="34.8636">{{company_name}}</tspan></text>
 <text fill="black" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="8" letter-spacing="0em"><tspan x="25" y="51.8183">{{position}}</tspan></text>
 <text fill="#2BBE9B" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="14" font-weight="bold" letter-spacing="0em"><tspan x="62.2559" y="38.1817">{{name}}</tspan></text>
 <text fill="black" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="8" letter-spacing="0em"><tspan x="40" y="154.818">{{address_2}}</tspan></text>
 <text fill="black" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="8" letter-spacing="0em"><tspan x="40" y="164.818">{{address_1}}</tspan></text>
 <path d="M33.75 147H26.25C25.5596 147 25 147.56 25 148.25V155.75C25 156.44 25.5596 157 26.25 157H33.75C34.4404 157 35 156.44 35 155.75V148.25C35 147.56 34.4404 147 33.75 147Z" fill="#2BBE9B"/>
 <path fill-rule="evenodd" clip-rule="evenodd" d="M29.9997 155.829L30.3002 155.49C30.6411 155.099 30.9478 154.729 31.2207 154.377L31.4459 154.079C32.3864 152.812 32.8569 151.807 32.8569 151.063C32.8569 149.477 31.5778 148.19 29.9997 148.19C28.4216 148.19 27.1426 149.477 27.1426 151.063C27.1426 151.807 27.6131 152.812 28.5535 154.079L28.7788 154.377C29.168 154.875 29.5753 155.36 29.9997 155.829Z" stroke="white" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M30.0009 152.238C30.6584 152.238 31.1914 151.705 31.1914 151.047C31.1914 150.39 30.6584 149.857 30.0009 149.857C29.3435 149.857 28.8105 150.39 28.8105 151.047C28.8105 151.705 29.3435 152.238 30.0009 152.238Z" stroke="white" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round"/>
 <text fill="black" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="8" letter-spacing="0em"><tspan x="40" y="138.818">{{email}}</tspan></text>
 <path d="M33.75 131H26.25C25.5596 131 25 131.56 25 132.25V139.75C25 140.44 25.5596 141 26.25 141H33.75C34.4404 141 35 140.44 35 139.75V132.25C35 131.56 34.4404 131 33.75 131Z" fill="#2BBE9B"/>
 <path d="M33.3333 133.083H26.6667C26.4365 133.083 26.25 133.27 26.25 133.5V138.5C26.25 138.73 26.4365 138.917 26.6667 138.917H33.3333C33.5635 138.917 33.75 138.73 33.75 138.5V133.5C33.75 133.27 33.5635 133.083 33.3333 133.083Z" stroke="white" stroke-width="0.5" stroke-linecap="round"/>
 <path d="M26.25 133.708L30 136L33.75 133.708" stroke="white" stroke-width="0.5" stroke-linecap="round"/>
 <mask id="mask1_407_397" style="mask-type:luminance" maskUnits="userSpaceOnUse" x="25" y="115" width="10" height="10">
 <path d="M33.75 115H26.25C25.5596 115 25 115.56 25 116.25V123.75C25 124.44 25.5596 125 26.25 125H33.75C34.4404 125 35 124.44 35 123.75V116.25C35 115.56 34.4404 115 33.75 115Z" fill="white"/>
 </mask>
 <g mask="url(#mask1_407_397)">
 <path d="M33.75 115H26.25C25.5596 115 25 115.56 25 116.25V123.75C25 124.44 25.5596 125 26.25 125H33.75C34.4404 125 35 124.44 35 123.75V116.25C35 115.56 34.4404 115 33.75 115Z" fill="#2BBE9B"/>
 <path d="M29.3983 117.6L27.9887 115.973C27.8262 115.786 27.5283 115.786 27.3395 115.976L26.1804 117.137C25.8354 117.482 25.7366 117.995 25.9362 118.406C27.1285 120.875 29.1195 122.869 31.5866 124.065C31.9974 124.264 32.5099 124.166 32.8549 123.82L34.0249 122.648C34.2145 122.458 34.2149 122.159 34.0258 121.996L32.3924 120.594C32.2216 120.448 31.9562 120.467 31.7849 120.638L31.2166 121.208C31.1875 121.238 31.1492 121.258 31.1076 121.265C31.066 121.271 31.0233 121.264 30.9862 121.244C30.0572 120.709 29.2866 119.938 28.7529 119.008C28.7329 118.971 28.7256 118.928 28.7323 118.886C28.7389 118.845 28.759 118.806 28.7895 118.777L29.3562 118.21C29.5279 118.038 29.5466 117.771 29.3983 117.6Z" stroke="white" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round"/>
 </g>
 <text fill="black" xml:space="preserve" style="white-space: pre" font-family="Inter" font-size="8" letter-spacing="0em"><tspan x="40" y="122.818">{{phone}}</tspan></text>
 </g>
 <defs>
 <clipPath id="clip0_407_397">
 <rect width="336" height="192" fill="white"/>
 </clipPath>
 </defs>
 </svg>"""

TEMPLATE_FIELDS = [
    {
        "id": 40,
        "label": "name",
        "field_type": "text",
        "placeholder": "Olisa Paul"
    },
    {
        "id": 41,
        "label": "position",
        "field_type": "text",
        "placeholder": "Designer"
    },
    {
        "id": 42,
        "label": "phone",
        "field_type": "text",
        "placeholder": "01236735409"
    },
    {
        "id": 43,
        "label": "email",
        "field_type": "text",
        "placeholder": "test@example.com"
    },
    {
        "id": 44,
        "label": "address_2",
        "field_type": "text",
        "placeholder": "123, Test Avenue"
    },
    {
        "id": 45,
        "label": "address_1",
        "field_type": "text",
        "placeholder": "Stupid Lane, US"
    },
    {
        "id": 46,
        "label": "company_name",
        "field_type": "text",
        "placeholder": "Big Boys LTD"
    },
    {
        "id": 47,
        "label": "tagline",
        "field_type": "text",
        "placeholder": "Example Tag Line"
    }
]

catalog_item_fields = [
    'id', 'title', 'item_sku', 'description', 'short_description',
    'default_quantity', 'pricing_grid', 'thumbnail', 'preview_image', 'preview_file',
    'available_inventory', 'minimum_inventory', 'track_inventory_automatically',
    'restrict_orders_to_inventory', 'weight_per_piece_lb', 'weight_per_piece_oz',
    'exempt_from_shipping_charges', 'is_this_item_taxable', 'can_item_be_ordered',
    'details_page_per_layout', 'is_favorite', 'attributes', 'item_type'
]

online_proof_fields = [
    "name",
    "email_address",
    "created_at",
    "tracking_number",
    "proof_status",
    "recipient_name",
    "recipient_email",
    "project_title",
    "project_details",
    "proof_due_date",
    "additional_info",
    "files",
    "created_at"
]

general_fields = [
    'id', 'name', 'email_address', 'phone_number', 'address', 'fax_number',
    'company', 'city_state_zip', 'country', 'additional_details', 'portal',
    'files'
]

image_fields = general_fields + \
    ['preferred_mode_of_response', 'artwork_provided',
        'project_name', 'project_due_date']

customer_fields = ['id', 'company', 'address', 'city_state_zip',
                   'phone_number', 'fax_number', 'pay_tax',
                   'third_party_identifier', 'credit_balance', 'user_id']


def create_file_fields(num_files, allowed_extensions):
    return {
        f'file{i+1}': serializers.FileField(
            validators=[FileExtensionValidator(
                allowed_extensions=allowed_extensions)],
            required=False
        )
        for i in range(num_files)
    }


def _notify_customer_permission_change(customers):
    """Helper function to send permission updates for users"""
    channel_layer = get_channel_layer()
    permissions_updates = [
        {
            "user_id": customer.id,
        }
        for customer in customers
    ]

    async_to_sync(channel_layer.group_send)(
        "customer_permissions",
        {
            "type": "bulk_customer_permissions_update",
            "updates": permissions_updates
        }
    )


def _implement_permission_change(validated_data, instance, old_customers):
    if 'customers' in validated_data or 'customer_groups' in validated_data:
        affected_customers = set()
        affected_customers.update(instance.customers.all())
        affected_customers.update(old_customers)
        for group in instance.customer_groups.all():
            affected_customers.update(group.customers.all())

        if affected_customers:
            _notify_customer_permission_change(list(affected_customers))


def get_old_customers(instance):
    old_customers = set()
    old_customers.update(instance.customers.only('id'))
    for group in instance.customer_groups.all():
        old_customers.update(group.customers.only('id'))

    return old_customers


class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'


class FileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(method_name='get_url')

    class Meta:
        model = File
        fields = ['path', 'url', 'file_size', 'file_name']

    def get_url(self, image: File):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        path = image.path
        return f"https://res.cloudinary.com/{cloud_name}/{path}"


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )
    has_header = serializers.BooleanField()

    def validate_file(self, file):
        if file.content_type != 'text/csv':
            raise serializers.ValidationError(
                "Invalid file type. Please upload a CSV file.")

        file_data = file.read().decode('utf-8')

        try:
            csv_reader = csv.DictReader(file_data.splitlines())
            list(csv_reader)
        except csv.Error:
            raise serializers.ValidationError(
                "CSV parsing error. Ensure the file is a valid CSV with UTF-8 encoding.")

        return file_data


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'first_name', 'last_name', 'email_address', 'phone_number',
            'fax_number', 'company', 'address', 'address_line_2',
            'state', 'city', 'zip_code', 'status', 'send_notifications',
            'tracking_number', 'shipment_cost', 'created_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'type', 'description', 'created_at']

    def validate(self, data):
        if data['type'] == 'refund':
            content_type = self.context['content_type']
            object_id = self.context['object_id']
            if not Transaction.objects.filter(content_type=content_type, object_id=object_id, type='payment').exists():
                raise serializers.ValidationError(
                    {"type": "Refund cannot be made without an existing payment."})
        return data


class BillingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingInfo
        fields = [
            'first_name', 'last_name', 'email_address', 'phone_number',
            'fax_number', 'company', 'address', 'address_line_2',
            'state', 'city', 'zip_code', 'created_at'
        ]


class TitlePortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['title']


class QuoteRequestSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']


class CreateQuoteRequestSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = QuoteRequest
        fields = image_fields
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(QuoteRequest, validated_data)


class NoteAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class NoteSerializer(serializers.ModelSerializer):
    author = NoteAuthorSerializer(read_only=True)

    class Meta:
        model = Note
        fields = ['id', 'content', 'created_at', 'author']
        read_only_fields = ['created_at', 'author']


class CreateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'content']


class RequestSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()
    notes = NoteSerializer(many=True, read_only=True)
    billing_info = BillingInfoSerializer()

    class Meta:
        model = Request
        fields = image_fields + ['this_is_an', 'status',
                                 'notes', 'billing_info', 'shipments', 'transactions']
        read_only_fields = ['created_at']


class CreateRequestSerializer(serializers.ModelSerializer):
    allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
    files = serializers.ListField(
        child=serializers.FileField(
            validators=[FileExtensionValidator(
                allowed_extensions=allowed_extensions)]
        ),
        write_only=True,
        required=False
    )

    class Meta:
        model = Request
        fields = image_fields + ["this_is_an"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(Request, validated_data)


class OnlineProofSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = OnlineProof
        fields = online_proof_fields
        read_only_fields = ['created_at']


class CreateOnlineProofSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = OnlineProof
        fields = online_proof_fields
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(OnlineProof, validated_data)


class FileTransferSerializer(serializers.ModelSerializer):
    shipments = ShipmentSerializer(many=True, read_only=True)
    billing_info = BillingInfoSerializer()
    transactions = TransactionSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    portal = TitlePortalSerializer()

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type", "status", "notes", "billing_info", "shipments", "transactions"]
        read_only_fields = ['created_at']


class CreateFileTransferSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=True
    )

    class Meta:
        model = FileTransfer
        fields = general_fields + ["file_type",
                                   "application_type", "other_application_type"]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        return create_instance_with_files(FileTransfer, validated_data)


def validate_status_transition(instance, new_status):
    # Define the allowed status progression
    allowed_transitions = {
        'New': ['Pending'],
        'Pending': ['New', 'Processing'],
        'Processing': ['New', 'Pending', 'Completed'],
        'Completed': ['New', 'Pending', 'Processing', 'Shipped'],
        'Shipped': ['New', 'Pending', 'Processing', 'Completed']
    }

    # Get the current instance's status
    if instance:
        current_status = instance.status

        # Check if the transition is valid
        if current_status in allowed_transitions and new_status not in allowed_transitions[current_status]:
            raise serializers.ValidationError(
                f"Invalid status transition from \
                    {current_status} to {new_status}."
                f"You can only change it to one of \
                    {allowed_transitions[current_status]}."
            )

    return new_status


class UpdateFileTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileTransfer
        fields = ['status']

    def validate_status(self, value):
        return validate_status_transition(self.instance, value)


class UpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['status']

    def validate_status(self, value):
        return validate_status_transition(self.instance, value)


class SimpleCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title']


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    groups = SimpleCustomerGroupSerializer(many=True, read_only=True)
    groups_count = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [*customer_fields, 'groups', 'groups_count',
                  'name', 'email', 'username', 'is_active']

    def get_email(self, customer: Customer):
        return customer.user.email

    def get_groups_count(self, customer: Customer):
        return customer.groups.count()

    def get_is_active(self, customer: Customer):
        return customer.user.is_active

    def get_username(self, customer: Customer):
        return customer.user.username

    def get_name(self, customer: Customer):
        return customer.user.name


class SimpleCustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'company', 'fax_number',
                  'city_state_zip', 'address', 'phone_number']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email


class PortalCustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'username']

    def get_name(self, customer: Customer):
        return customer.user.name

    def get_email(self, customer: Customer):
        return customer.user.email

    def get_username(self, customer: Customer):
        return customer.user.username


class UpdateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(write_only=True)

    class Meta:
        model = Customer
        fields = [*customer_fields, 'groups', 'is_active', 'name']

    @transaction.atomic()
    def update(self, instance, validated_data):
        name = validated_data.pop('name')
        is_active = validated_data.pop('is_active')
        groups = validated_data.pop('groups')

        customer = super().update(instance, validated_data)

        if type(groups) is list:
            _notify_customer_permission_change([customer])

        if groups:
            customer.groups.set(groups)

        if name is not None or isinstance(is_active, bool):
            user = instance.user

            if name:
                user.name = name
            if isinstance(is_active, bool):
                user.is_active = is_active
            user.save()

        return customer


class CreateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(write_only=True)
    is_active = serializers.BooleanField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})
    username = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = [*customer_fields, 'groups', 'email',
                  'password', 'username', 'name', 'is_active']

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(username=value).exists():
            raise ValidationError("A user with this username already exists.")
        return value

    def get_name(self, customer: Customer):
        return customer.user.name

    @transaction.atomic()
    def create(self, validated_data):
        email = validated_data.pop('email')
        is_active = validated_data.pop('is_active')
        name = validated_data.pop('name')
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        groups = validated_data.pop('groups', [])

        user = User.objects.create_user(
            email=email, password=password, name=name, username=username, is_active=is_active)
        customer = Customer.objects.create(user=user, **validated_data)

        subject = "Welcome to Walls Printing!"
        template = "email/welcome_email.html"
        context = {
            "user": user,
            "temporary_password": password,
            "login_url": os.getenv('CUSTOMER_LOGIN_URL')
        }

        send_email(user=user, context=context,
                   subject=subject, template=template)

        if groups:
            customer.groups.set(groups)

        return customer


class CustomerGroupSerializer(serializers.ModelSerializer):
    customers = SimpleCustomerSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()

    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers', "date_created", "members"]

    def get_members(self, customer_group: CustomerGroup):
        return customer_group.customers.count()


class PortalCustomerGroupSerializer(serializers.ModelSerializer):
    customers = PortalCustomerSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers',]


class CreateCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers']

    def validate_title(self, attrs):
        title = attrs.lower()
        if CustomerGroup.objects.filter(title__iexact=title).exists():
            raise serializers.ValidationError("Group name already exists")
        return attrs


class UpdateCustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ['id', 'title', 'customers']

    def update(self, instance, validated_data):
        old_customers = [*instance.customers.only('id')]
        customer_group = super().update(instance, validated_data)
        customers = set([*customer_group.customers.only("id"), *old_customers])

        _notify_customer_permission_change(customers)

        return customer_group


class BulkCreateCustomerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = [*customer_fields, 'name', 'email', 'password']

    def validate_email(self, value):
        """Ensure email is unique across users"""
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'title', 'content']


class UpdatePortalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContent
        fields = ['id', 'customer_groups', 'customers', 'everyone', 'content',
                  'display_in_site_navigation', 'catalogs', 'logo'
                  #   'logo', 'payment_proof', 'order_history', 'page_redirect',
                  #   'redirect_page', 'redirect_file', 'redirect_url', 'redirect_code'
                  #   'include_in_site_map', 'location',
                  ]
        logo = serializers.ImageField(required=False)

    def validate(self, data):
        customer_groups_data = data.get('customer_groups', [])
        customer_data = data.get('customers', [])
        catalogs = data.get('catalogs', [])
        everyone = data.get('everyone', None)
        # page_redirect = data.get('page_redirect', None)
        # redirect_page = data.get('redirect_page', None)
        # redirect_file = data.get('redirect_file', None)
        # redirect_url = data.get('redirect_url', None)

        # Validate customer group and everyone selection
        if (customer_groups_data or customer_data) and everyone:
            raise ValidationError(
                "You cannot select 'everyone' and also specify 'customer_groups' or 'customers'. Choose one option only."
            )

        portal_id = self.context['portal_id']
        portal = Portal.objects.prefetch_related(
            'customers', 'customer_groups').get(id=portal_id)
        portal_customers = set(portal.customers.values_list('id', flat=True))
        portal_customer_ids = set()
        for group in portal.customer_groups.all():
            portal_customer_ids.update(
                group.customers.values_list('id', flat=True))

        customer_ids = set(customer.id if hasattr(
            customer, 'id') else customer for customer in customer_data)
        if not customer_ids.issubset(portal_customers.union(portal_customer_ids)):
            raise ValidationError(
                "All selected customers must be part of the parent portal."
            )

        # Restrict customer groups to those in the parent portal
        portal_customer_groups = set(
            portal.customer_groups.values_list(flat=True))
        customer_group_ids = set(customer_group.id if hasattr(
            customer_group, 'id') else customer_group for customer_group in customer_groups_data)

        if not customer_group_ids.issubset(portal_customer_groups):
            raise ValidationError(
                "All selected customer groups must be part of the parent portal."
            )

        if self.instance.title != CreatePortalSerializer.ONLINE_ORDERS and catalogs:
            raise ValidationError(
                {"catalogs": "You can't assign catalogs for this page."})

        # # Validate redirect fields based on page_redirect value
        # if page_redirect == 'no_redirect':
        #     if redirect_page or redirect_file or redirect_url or not data.get('redirect_code') in ['default', None]:
        #         raise ValidationError(
        #             "For 'no_redirect', 'redirect_page', 'redirect_file', 'redirect_url', and 'redirect_code' must be null."
        #         )
        # elif page_redirect == 'external':
        #     if not redirect_url:
        #         raise ValidationError(
        #             "For 'external', 'redirect_url' is required."
        #         )
        #     if redirect_page or redirect_file:
        #         raise ValidationError(
        #             "For 'external', 'redirect_page' and 'redirect_file' must be null."
        #         )
        # elif page_redirect == 'internal':
        #     if not redirect_page:
        #         raise ValidationError(
        #             "For 'internal', 'redirect_page' is required."
        #         )
        #     if redirect_file or redirect_url:
        #         raise ValidationError(
        #             "For 'internal', 'redirect_file' and 'redirect_url' must be null."
        #         )
        # elif page_redirect == 'file':
        #     if not redirect_file:
        #         raise ValidationError(
        #             "For 'file', 'redirect_file' is required."
        #         )
        #     if redirect_page or redirect_url:
        #         raise ValidationError(
        #             "For 'file', 'redirect_page' and 'redirect_url' must be null."
        #         )

        return data

    @transaction.atomic()
    def create(self, validated_data):
        portal_id = self.context['portal_id']
        customer_group_data = []
        customer_data = []
        customer_group_data = validated_data.pop('customer_groups', None)
        customer_data = validated_data.pop('customers', None)

        portal_content = PortalContent.objects.create(
            portal_id=portal_id, **validated_data)

        if customer_group_data:
            portal_content.customer_groups.set(customer_group_data)
        if customer_data:
            portal_content.customers.set(customer_data)

        return portal_content

    def update(self, instance, validated_data):
        customers = get_old_customers(instance)
        content = super().update(instance, validated_data)

        _implement_permission_change(validated_data, content.portal, customers)

        return content


class CreatePortalSerializer(serializers.ModelSerializer):
    # content = CreatePortalContentSerializer(many=True, required=False)
    WELCOME = 'Welcome'
    ONLINE_PAYMENTS = 'Online payments'
    ORDER_APPROVAL = 'Order approval'
    ONLINE_ORDERS = 'Online orders'
    logo = serializers.ImageField(
        required=True, allow_null=True, write_only=True)
    copy_an_existing_portal = serializers.BooleanField(default=False)
    copy_from_portal_id = serializers.IntegerField(
        required=False, allow_null=True)
    copy_the_logo = serializers.BooleanField(default=False)
    same_permissions = serializers.BooleanField(required=False)
    same_catalogs = serializers.BooleanField(required=False)
    same_proofing_categories = serializers.BooleanField(required=False)
    catalog = serializers.CharField(required=False)
    customer_groups = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    customers = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Portal
        fields = ['id', 'title', 'logo', 'copy_an_existing_portal', 'copy_from_portal_id',
                  'same_permissions', 'copy_the_logo', 'same_catalogs', 'same_proofing_categories',
                  'customers', 'customer_groups', 'catalog',
                  ]

    def validate_title(self, value):
        if Portal.objects.filter(title__iexact=value).exists():
            if self.instance is None:
                raise serializers.ValidationError(
                    "A Portal with this title already exists.")
            else:
                if Portal.objects.get(title__iexact=value).id != self.instance.id:
                    raise serializers.ValidationError(
                        "A Portal with this title already exists.")
        return value

    def validate_catalog(self, value):
        if Catalog.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "Catalog already exists with title.")
        return value

    def validate(self, data):
        copy_an_existing_portal = data.get('copy_an_existing_portal', False)
        copy_the_logo = data.get('copy_the_logo', False)
        same_permissions = data.get('same_permissions', False)
        customers = data.get('customers', False)
        customer_groups = data.get('customer_groups', False)
        logo = data.get('logo', None)

        if not copy_an_existing_portal:
            invalid_fields = {
                field: data.get(field)
                for field in ['copy_from_portal_id', 'same_permissions', 'same_catalogs', 'same_proofing_categories', 'copy_the_logo']
                if data.get(field) is True
            }
            if invalid_fields:
                raise serializers.ValidationError(
                    {
                        field: f"Must be false when 'copy_an_existing_portal' is False."
                        for field in invalid_fields
                    }
                )
        else:
            if logo and copy_the_logo:
                raise serializers.ValidationError(
                    {
                        field: f"No need to specify the logo when you are copying a logo from a another portal"
                        for field in ['logo', 'copy_the_logo']
                    }
                )

            if same_permissions and (customers or customer_groups):
                raise serializers.ValidationError(
                    {
                        field: f"No need to specify the logo when you are copying a logo from a another portal"
                        for field in ['customer', 'copy_the_logo']
                    }
                )

        return data

    @transaction.atomic()
    def create(self, validated_data):
        allowed_titles = [self.WELCOME,
                          self.ONLINE_PAYMENTS, self.ORDER_APPROVAL]
        catalog = validated_data.pop('catalog', None)
        copy_an_existing_portal = validated_data.pop(
            'copy_an_existing_portal', False)
        validated_data.pop('copy_the_logo', False)
        customers = validated_data.pop('customers', [])
        customer_groups = validated_data.pop('customer_groups', [])
        copy_from_portal_id = validated_data.pop('copy_from_portal_id', False)
        same_permissions = validated_data.pop('same_permissions', None)
        same_catalogs = validated_data.pop('same_catalogs', None)
        same_proofing_categories = validated_data.pop(
            'same_proofing_categories', None)
        portal = Portal.objects.create(**validated_data)

        if customer_groups and copy_from_portal_id:
            raise ValidationError(
                "You cannot specify both 'customer_groups' and 'copy_from_portal_id'. Choose one option."
            )

        if catalog:
            catalog = Catalog.objects.create(title=catalog)

        if copy_an_existing_portal:
            try:
                if None in [same_permissions, same_catalogs, same_proofing_categories]:
                    return ValueError('Neither same_permissions, same_catalogs nor same_proofing_categories is allowed to be null')
                source_portal = Portal.objects.prefetch_related(
                    'contents__customer_groups', 'contents__customers'
                ).get(id=copy_from_portal_id)

                customers = source_portal.customers.all()
                customer_groups = source_portal.customer_groups.all()
            except Portal.DoesNotExist:
                raise ValidationError(
                    {"copy_from_portal_id": "The portal to copy from does not exist."})

            portal_contents = []

            for source_content in source_portal.contents.all():
                portal_contents.append(PortalContent(
                    portal=portal,
                    everyone=source_content.everyone,
                    page=source_content.page,
                    title=source_content.title,
                    can_have_catalogs=source_content.can_have_catalogs,
                ))

            PortalContent.objects.bulk_create(portal_contents)
            created_portal_contents = PortalContent.objects.filter(
                portal=portal, title__in=[content.title for content in portal_contents])

            for portal_content, source_content in zip(created_portal_contents, source_portal.contents.all()):
                portal_content.customer_groups.set(
                    source_content.customer_groups.all())
                portal_content.customers.set(source_content.customers.all())

                if portal_content.can_have_catalogs and same_catalogs:
                    portal_content.catalogs.set(source_content.catalogs.all())
                elif portal_content.can_have_catalogs and catalog:
                    portal_content.catalogs.set([catalog])
        else:
            allowed_titles = ['Welcome', 'Online payments', 'Order approval',]
            existing_titles = PortalContent.objects.filter(
                portal=portal).values_list('title', flat=True)

            online_orders_content = [
                PortalContent(portal=portal, title=self.ONLINE_ORDERS,
                              url='online-orders.html', can_have_catalogs=True)
            ]
            order_history_content = [
                PortalContent(portal=portal, title='Order history',
                              url='order-history.html', order_history=True)
            ]

            portal_contents = online_orders_content + order_history_content + [
                PortalContent(portal=portal, title=title,
                              url=f'{title.lower().replace(" ", "-")}.html')
                for title in allowed_titles
                if title not in existing_titles
            ]

            if portal_contents:
                PortalContent.objects.bulk_create(portal_contents)

            if catalog:
                created_portal_contents = PortalContent.objects.get(
                    portal=portal, can_have_catalogs=True)
                created_portal_contents.catalogs.set([catalog])

        portal.customers.set(customers)
        portal.customer_groups.set(customer_groups)
        return portal


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = [
            'id',
            'title',
            'parent_catalog',
            'specify_low_inventory_message',
            'recipient_emails',
            'subject',
            'message_text',
            'description',
            'display_items_on_same_page',
            'created_at',
        ]

    def validate_title(self, value):
        request = self.context['request']
        if Catalog.objects.filter(title__iexact=value).exists():
            if request.method == 'POST':
                raise serializers.ValidationError(
                    "A catalog with this title already exists.")
            elif request.method in ['PATCH', 'PUT']:
                if Catalog.objects.get(title__iexact=value).id != self.instance.id:
                    raise serializers.ValidationError(
                        "A catalog with this title already exists.")
        return value

    def validate_recipient_emails(self, value):
        """
        Validate the recipient_emails field.
        """
        if not value:
            return value

        emails = [email.strip() for email in value.split(',')]
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise serializers.ValidationError(
                    f"'{email}' is not a valid email address.")

        return value

    def validate(self, data):
        """
        Validate the fields related to 'specify_low_inventory_message'.
        """
        if data.get('specify_low_inventory_message'):
            if not data.get('recipient_emails'):
                raise serializers.ValidationError(
                    {"recipient_emails": "This field is required when specifying a low inventory message."})
            if not data.get('subject'):
                raise serializers.ValidationError(
                    {"subject": "This field is required when specifying a low inventory message."})
            if not data.get('message_text'):
                raise serializers.ValidationError(
                    {"message_text": "This field is required when specifying a low inventory message."})
        else:
            if data.get('recipient_emails') or data.get('subject') or data.get('message_text'):
                raise serializers.ValidationError(
                    "Low inventory message fields should not be filled if 'specify_low_inventory_message' is disabled.")
        return data


class SimpleCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = [
            'id',
            'title',
            'parent_catalog',
            'description',
            'display_items_on_same_page',
        ]


class ViewPortalContentCatalogSerializer(serializers.ModelSerializer):
    catalog = CatalogSerializer()

    class Meta:
        model = PortalContentCatalog
        fields = ['catalog', 'is_active', 'order_approval']


class PortalContentSerializer(serializers.ModelSerializer):
    customer_groups = PortalCustomerGroupSerializer(many=True, read_only=True)
    customers = serializers.SerializerMethodField()
    can_user_access = serializers.SerializerMethodField()
    groups_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    catalogs = CatalogSerializer(many=True, read_only=True)
    logo = serializers.ImageField(required=False)
    # page = PageSerializer()
    # catalog_assignments = ViewPortalContentCatalogSerializer(many=True)

    class Meta:
        model = PortalContent
        fields = ['id', 'title',
                  'customer_groups', 'everyone', 'can_user_access', 'can_have_catalogs',
                  'customers', 'groups_count', 'user_count', 'catalogs', 'content', 'logo', 'payment_proof', 'order_history']

    def get_can_user_access(self, obj):
        return True

    def get_groups_count(self, portal_content: PortalContent):
        return portal_content.customer_groups.count()

    def get_user_count(self, portal_content: PortalContent):
        return portal_content.customers.count()

    def get_customers(self, portal_content: PortalContent):
        customers = portal_content.customers.all()
        portal = Portal.objects.get(contents=portal_content)
        portal_customers = portal.customers.all()
        portal_group_customers = Customer.objects.filter(
            groups__in=portal.customer_groups.all())

        filtered_customers = customers.intersection(portal_customers).union(
            customers.intersection(portal_group_customers))
        return PortalCustomerSerializer(filtered_customers, many=True).data

    def get_can_have_catalogs(self, obj):
        return obj.title == CreatePortalSerializer.ONLINE_ORDERS


class PortalSerializer(serializers.ModelSerializer):
    contents = serializers.SerializerMethodField()
    can_user_access = serializers.SerializerMethodField()
    customer_groups = PortalCustomerGroupSerializer(many=True, read_only=True)
    customers = PortalCustomerSerializer(many=True, read_only=True)
    logo = serializers.ImageField(required=False)
    number_of_cart_items = serializers.SerializerMethodField()

    class Meta:
        model = Portal
        fields = ['id', 'title', 'contents', 'can_user_access',
                  'customers', 'customer_groups', 'created_at', 'logo', 'number_of_cart_items']

    def get_contents(self, obj: Portal):
        customer_id = self.context.get('customer_id')

        if not customer_id:
            return PortalContentSerializer(obj.contents.all(), many=True, context={'request': self.context['request']}).data

        filtered_content = [
            content for content in obj.contents.all()
            if content.everyone or customer_id in content.customers.values_list('id', flat=True) or
            any(customer_id in group.customers.values_list('id', flat=True)
                for group in content.customer_groups.all()) or content.title == CreatePortalSerializer.WELCOME
        ]
        return PortalContentSerializer(filtered_content, many=True, context={'request': self.context['request']}).data

    def get_can_user_access(self, obj):
        return True

    def get_number_of_cart_items(self, obj: Portal):
        customer_id = self.context.get('customer_id')

        carts = obj.cart_set.all().prefetch_related('items')
        if customer_id:
            carts = carts.filter(customer_id=customer_id)

        return sum([cart.items.count() for cart in carts])

    def delete(self, instance):
        _implement_permission_change(instance, instance, instance.customers)
        instance.delete()


class PatchPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['title', 'customers', 'customer_groups', 'logo']

    def update(self, instance, validated_data):
        customers = get_old_customers(instance)
        portal = super().update(instance, validated_data)
        _implement_permission_change(validated_data, portal, customers)

        return portal


class BulkPortalContentCatalogSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        content_id = self.context['content_id']
        for item in validated_data:
            item['portal_content_id'] = content_id

        return PortalContentCatalog.objects.bulk_create([
            PortalContentCatalog(**item) for item in validated_data
        ])

    def validate(self, data):
        # Validate for duplicates in the incoming data
        seen_pairs = set()
        for item in data:
            pair = (self.context['content_id'], item['catalog'].id)
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    f"Duplicate portal_content-catalog pair found: {pair}."
                )
            seen_pairs.add(pair)

        # Validate for duplicates in the database
        existing_pairs = PortalContentCatalog.objects.filter(
            portal_content_id=self.context['content_id'],
            catalog__in=[item['catalog'] for item in data]
        ).values_list('portal_content_id', 'catalog_id')

        for pair in existing_pairs:
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    f"Duplicate pair found in the database: {pair}."
                )

        return data


class PortalContentCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalContentCatalog
        fields = ['catalog', 'is_active', 'order_approval']
        list_serializer_class = BulkPortalContentCatalogSerializer

    def create(self, validated_data):
        portal_content_id = self.context['content_id']

        return PortalContentCatalog.objects.create(portal_content_id=portal_content_id, **validated_data)

    def validate(self, data):
        if PortalContentCatalog.objects.filter(
            portal_content_id=self.context['content_id'], catalog=data['catalog']
        ).exists():
            raise serializers.ValidationError(
                "This portal_content-catalog combination already exists."
            )
        return data


class MessageCenterSerializer(serializers.ModelSerializer):
    title_and_tracking = serializers.SerializerMethodField()

    class Meta:
        model = None  # This is a composite serializer, not tied to a single model
        fields = ['created_at', 'title_and_tracking', 'your_name', 'files']

    def get_title_and_tracking(self, obj):
        if isinstance(obj, FileTransfer):
            return 'Online File Transfer'
        elif isinstance(obj, Request):
            if obj.this_is_an == 'Estimate Request':
                return 'Estimate Request'
            else:
                return 'Online Order'
        # elif isinstance(obj, EcommerceOrder):
        #     return 'Ecommerce Order'
        elif isinstance(obj, ContactInquiry):
            return 'General Contact'
        else:
            return ''


class AttributeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeOption
        fields = [
            'id', 'option', 'alternate_display_text',
            'price_modifier_type', 'pricing_tiers',
        ]

    def create(self, validated_data):
        attribute_id = self.context['attribute_id']
        validated_data['item_attribute_id'] = attribute_id

        return super().create(validated_data)


class AttributeSerializer(serializers.ModelSerializer):
    options_data = serializers.JSONField(write_only=True, required=False)
    options = AttributeOptionSerializer(read_only=True, many=True)

    class Meta:
        model = Attribute
        fields = [
            'id', 'label', 'is_required', 'attribute_type',
            'max_length', 'pricing_tiers', 'price_modifier_scope',
            'price_modifier_type', 'options', 'options_data'
        ]

    def validate_options_data(self, options_data):
        options_data = options_data or []
        if options_data and not self.instance:
            for option_data in options_data:
                serializer = AttributeOptionSerializer(data=option_data)
                serializer.is_valid(raise_exception=True)

        return options_data

    def validate(self, attrs):
        attribute_type = attrs.get('attribute_type', 'text_field')
        max_length = attrs.get('max_length')
        options = attrs.get('options_data')
        pricing_tiers = attrs.get('pricing_tiers')
        price_modifier_type = attrs.get('price_modifier_type')

        if self.instance and options:
            raise serializers.ValidationError(
                {"options_data": "Options can only be set during creation"})

        select_list = ['checkboxes', 'radio_buttons', 'select_menu']

        if attribute_type == 'text_field' and not max_length:
            raise serializers.ValidationError(
                {"max_length": "Max length is required for text fields"})

        if attribute_type != 'text_field' and max_length:
            raise serializers.ValidationError(
                {"max_length": "Max length can only be set for text fields"})

        if attribute_type in select_list:
            if pricing_tiers:
                raise serializers.ValidationError(
                    {"pricing_tiers": "Pricing tiers can only be set for text fields, file upload and text areas types"})
            if price_modifier_type:
                raise serializers.ValidationError(
                    {"price_modifier_type": "Price modifier type can only be set for text fields, file upload and text areas types"})
        else:
            if options:
                raise serializers.ValidationError(
                    {"options": "Options can only be set for checkboxes, radio buttons, and select menus"})

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        options_data = validated_data.pop('options_data', [])
        self.validate_options_data(options_data)

        catalog_item_id = self.context['catalog_item_id']
        validated_data['catalog_item_id'] = catalog_item_id
        attribute = super().create(validated_data)

        options = [
            AttributeOption(item_attribute=attribute, **option_data)
            for option_data in options_data
        ]
        AttributeOption.objects.bulk_create(options)

        return attribute


class ItemDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDetails
        fields = ['id', 'title', 'name', 'email_address',
                  'phone_number', 'office_number', 'extension',
                  'description', 'created_at'
                  ]

    def validate(self, attrs):
        is_new = self.context.get('is_new', False)
        id = self.context['id']
        model = self.context['model']
        title = attrs.get('title')
        name = attrs.get('name')
        description = attrs.get('description')
        email_address = attrs.get('email_address')

        item = model.objects.filter(
            id=id,
            catalog_item__can_be_edited=True
        ).first()

        if not is_new:
            if not item:
                if not model.objects.filter(id=id).exists():
                    raise serializers.ValidationError(
                        "No item with the given ID was found")
                else:
                    raise serializers.ValidationError(
                        "This item cannot be edited")
            else:
                if item.catalog_item.item_type == CatalogItem.NON_EDITABLE:
                    raise serializers.ValidationError(
                        "This item cannot be edited")

                elif item.catalog_item.item_type == CatalogItem.BUSINESS_CARD:
                    items_to_check = (("name", name), ("title", title),
                                      ("email_address", email_address))
                    for key, value in items_to_check:
                        if not value:
                            raise serializers.ValidationError(
                                {key: "This field is required"})
                elif item.catalog_item.item_type == CatalogItem.OTHERS:
                    if not description:
                        raise serializers.ValidationError(
                            {"description": "Description is required"})

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        id = self.context['id']
        model = self.context['model']

        instance = get_object_or_404(model, id=id)
        details = super().create(validated_data)

        instance.details = details
        instance.save()

        return details


# class CartDetailsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ItemDetails
#         fields = ['id', 'title', 'name', 'email_address',
#                   'phone_number', 'office_number', 'extension',
#                     'description', 'created_at'
#                   ]

#     def create(self, validated_data):
#         cart_item_id = self.context['cart_item_id']

#         cart_item = CartItem.objects.filter(
#             id=cart_item_id,
#             catalog_item__can_be_edited=True
#         ).first()

#         if not cart_item:
#             if not CartItem.objects.filter(id=cart_item_id).exists():
#                 raise serializers.ValidationError(
#                     "No cart item with the given ID was found")
#             else:
#                 raise serializers.ValidationError(
#                     "This item in the cart cannot be edited")

#         cart_details = CartDetails.objects.create(
#             cart_item=cart_item, **validated_data)
#         return cart_details

class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = ['id', 'label', 'field_type', 'placeholder',
                  'position_x', 'position_y', 'font_size', 'font_color',
                  'font_family', 'bold', 'italic', 'width', 'height',
                  'max_length', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        # Get the catalog item from context
        catalog_item_id = self.context.get('catalog_item_id')
        if catalog_item_id:
            try:
                catalog_item = CatalogItem.objects.get(id=catalog_item_id)
                if catalog_item.item_type != CatalogItem.BUSINESS_CARD:
                    raise serializers.ValidationError(
                        "Template fields can only be associated with Business Card catalog items."
                    )
            except CatalogItem.DoesNotExist:
                raise serializers.ValidationError(
                    "Catalog item does not exist.")

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        catalog_item_id = self.context.get('catalog_item_id')
        if catalog_item_id:
            validated_data['catalog_item_id'] = catalog_item_id

        return super().create(validated_data)


class CatalogItemSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)
    # template_fields = TemplateFieldSerializer(many=True, read_only=True)
    preview_image = serializers.SerializerMethodField()
    preview_file = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    catalog = SimpleCatalogSerializer()
    template_fields = serializers.SerializerMethodField()
    front_svg_code = serializers.SerializerMethodField()
    back_svg_code = serializers.SerializerMethodField()
    can_be_edited = serializers.SerializerMethodField()

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + \
            ['created_at', 'can_be_edited', 'catalog', 'template_fields',
                'front_svg_code', 'back_svg_code', 'sides']

    def get_url(self, field):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not field:
            return None

        url = field.url
        if not field.url:
            return url

        if 'http' in url:
            return url

        return f"https://res.cloudinary.com/{cloud_name}/{url}"

    def get_preview_image(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_image)

    def get_preview_file(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_file)

    def get_thumbnail(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.thumbnail)

    def get_front_svg_code(self, obj: CatalogItem):
        if obj.file_name:
            return obj.front_svg_code or SVG_TEMPLATE
        return None

    def get_back_svg_code(self, obj: CatalogItem):
        if obj.file_name:
            return obj.back_svg_code or SVG_TEMPLATE
        return None

    def get_template_fields(self, obj: CatalogItem):
        if obj.file_name: 
            return TemplateFieldSerializer(
                obj.template_fields.all(), many=True).data or TEMPLATE_FIELDS
        return None
    
    def get_can_be_edited(self, obj: CatalogItem):
        return obj.item_type in [CatalogItem.BUSINESS_CARD, CatalogItem.OTHERS]

class CreateTemplateFieldSerializer(serializers.ModelSerializer):
    position = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = TemplateField
        fields = ['id', 'label', 'field_type', 'placeholder', 'prefix', 
                  'position', 'font_size', 'font_color',
                  'font_family', 'bold', 'italic', 'width', 'height',
                  'max_length']

    def validate(self, attrs):
        # Get the catalog item from context
        catalog_item_id = self.context.get('catalog_item_id')
        editable_item_id = self.context.get('editable_item_id')
        if editable_item_id and not CatalogItem.objects.filter(id=editable_item_id).exists():
            raise serializers.ValidationError(
                "Editable item does not exist.")

        if catalog_item_id:
            try:
                catalog_item = CatalogItem.objects.get(id=catalog_item_id)
                if catalog_item.item_type != CatalogItem.BUSINESS_CARD:
                    raise serializers.ValidationError(
                        "Template fields can only be associated with Business Card catalog items."
                    )
            except CatalogItem.DoesNotExist:
                raise serializers.ValidationError(
                    "Catalog item does not exist.")

        # Handle position JSON field
        position = attrs.pop('position', None)
        if position:
            if not isinstance(position, dict):
                raise serializers.ValidationError(
                    {"position": "Position must be a dictionary with x and y coordinates."})

            attrs['position_x'] = position.get('x', 0)
            attrs['position_y'] = position.get('y', 0)

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        catalog_item_id = self.context.get('catalog_item_id')
        editable_item_id = self.context.get('editable_item_id')
        if catalog_item_id:
            validated_data['catalog_item_id'] = catalog_item_id
        if editable_item_id:
            editable_item = CatalogItem.objects.get(
                id=editable_item_id)
            if editable_item.status != CatalogItem.APPROVING:
                editable_item.status = CatalogItem.APPROVING
                editable_item.save()

            validated_data['catalog_item_id'] = editable_item_id

        return super().create(validated_data)


class CreateOrUpdateCatalogItemSerializer(serializers.ModelSerializer):
    preview_image = serializers.ImageField()
    thumbnail = serializers.ImageField()
    preview_file = serializers.FileField()
    attributes = AttributeSerializer(many=True, read_only=True)
    attribute_data = serializers.JSONField(write_only=True, required=False)
    # template_fields = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = CatalogItem
        fields = catalog_item_fields + \
            ['attribute_data', 'can_be_edited', 'item_type']

    # def validate_template_fields(self, template_fields):
    #     if template_fields:
    #         for template_field in template_fields:
    #             serializer = CreateTemplateFieldSerializer(data=template_field)
    #             serializer.is_valid(raise_exception=True)
    #         return template_fields

    def validate_attribute_data(self, attributes_data):
        if attributes_data and self.instance:
            for attribute_data in attributes_data:
                serializer = AttributeSerializer(data=attribute_data)
                serializer.is_valid(raise_exception=True)
            return attributes_data

    def validate(self, attrs):
        attributes_data = attrs.pop('attribute_data', [])
        if self.instance and attributes_data:
            raise serializers.ValidationError(
                {"attribute_data": "Attribute data not allowed during updates"})

        catalog_id = self.context['catalog_id']
        if not Catalog.objects.filter(pk=catalog_id).exists():
            raise serializers.ValidationError(
                "No catalog with the given catalog_id was found")

        item_type = attrs.get('item_type', getattr(
            self.instance, 'item_type', None))

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        attributes_data = validated_data.pop('attribute_data', [])
        # template_fields = validated_data.pop('template_fields', [])
        self.validate_attribute_data(attributes_data)
        catalog_id = self.context['catalog_id']
        catalog_item = CatalogItem.objects.create(
            catalog_id=catalog_id, **validated_data)

        options_to_bulk_create = []

        # if template_fields:
        #     template_fields = CreateTemplateFieldSerializer(
        #         data=template_fields,
        #         context={
        #             'catalog_item_id': catalog_item.id,
        #         },
        #         many=True
        #     )
        #     template_fields.is_valid(raise_exception=True)
        #     template_fields.save()

        for attribute_data in attributes_data:
            options_data = attribute_data.pop('options', [])
            attribute = Attribute.objects.create(
                catalog_item=catalog_item, **attribute_data)

            attribute_options = [
                AttributeOption(item_attribute_id=attribute.id, **option_data)
                for option_data in options_data
            ]

            options_to_bulk_create += attribute_options

        AttributeOption.objects.bulk_create(options_to_bulk_create)

        return catalog_item

    @transaction.atomic()
    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attribute_data', [])
        # Validate attribute_data
        self.validate_attribute_data(attributes_data)

        for attribute_data in attributes_data:
            options_data = attribute_data.pop('options', [])
            attribute_id = attribute_data.get('id')
            if attribute_id:
                attribute = Attribute.objects.get(
                    id=attribute_id, catalog_item=instance)
                for key, value in attribute_data.items():
                    setattr(attribute, key, value)
                attribute.save()
                for option_data in options_data:
                    option_id = option_data.get('id')
                    if option_id:
                        option = AttributeOption.objects.get(
                            id=option_id, item_attribute=attribute)
                        for key, value in option_data.items():
                            setattr(option, key, value)
                        option.save()
                    else:
                        AttributeOption.objects.create(
                            item_attribute=attribute, **option_data)
            else:
                attribute = Attribute.objects.create(
                    catalog_item=instance, **attribute_data)
                for option_data in options_data:
                    AttributeOption.objects.create(
                        item_attribute=attribute, **option_data)

        return super().update(instance, validated_data)


class SimpleCatalogItemSerializer(serializers.ModelSerializer):
    catalog = SimpleCatalogSerializer()
    preview_image = serializers.SerializerMethodField()
    preview_file = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = CatalogItem
        fields = [
            'id', 'title', 'item_sku',
            'description', 'short_description', 'default_quantity',
            'thumbnail', 'preview_image', 'catalog',
            'preview_file', 'pricing_grid', 'item_type'
        ]

    def get_url(self, field):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not field:
            return None

        url = field.url
        if not field.url:
            return url

        if 'http' in url:
            return url

        return f"https://res.cloudinary.com/{cloud_name}/{url}"

    def get_preview_image(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_image)

    def get_preview_file(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.preview_file)

    def get_thumbnail(self, catalog_item: CatalogItem):
        return self.get_url(catalog_item.thumbnail)


class CartItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()
    sub_total = serializers.SerializerMethodField()
    details = ItemDetailsSerializer()
    front_pdf = serializers.SerializerMethodField()
    back_pdf = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'catalog_item', 'quantity',
                  'sub_total', 'unit_price', 'details', 'front_pdf', 'back_pdf', 'created_at']

    def get_sub_total(self, cart_item: CartItem):
        pricing_grid = cart_item.catalog_item.pricing_grid
        quantity = cart_item.quantity
        item = next(
            (entry for entry in pricing_grid if entry["minimum_quantity"] == quantity), None)
        total_price = (quantity * item['unit_price']
                       ) if item else cart_item.sub_total
        return total_price
    
    def get_url(self, field: CartItem):
        return field.url if field else None
    
    def get_front_pdf(self, cart_item: CartItem):
        return self.get_url(cart_item.front_pdf)
    def get_back_pdf(self, cart_item: CartItem):
        return self.get_url(cart_item.back_pdf)
    

class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    customer = SimpleCustomerSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    customer_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price",
                  "customer_id", 'customer', 'portal']

    def validate_customer_id(self, value):
        if not Customer.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "No customer with the given customer_id")
        customer_id = self.context['customer_id']
        if customer_id and customer_id != value:
            raise serializers.ValidationError(
                "You can only create your own cart")
        return value

    def validate(self, attrs):
        customer_id = attrs.get('customer_id', None)
        portal = attrs.get('portal', None)

        customer = attrs.get('customer_id', None)
        user = User.objects.get(id=self.context['user_id'])

        if user.is_staff and not customer:
            raise serializers.ValidationError(
                {"customer_id": "A valid integer field is required"})

        if Cart.objects.filter(customer_id=customer_id, portal=portal).exists():
            raise serializers.ValidationError(
                "The customer already has an active cart for this portal")

        return attrs

    def get_total_price(self, cart: Cart):
        return sum(
            Decimal(
                cart_item.quantity * next(
                    (entry['unit_price'] for entry in cart_item.catalog_item.pricing_grid
                     if entry['minimum_quantity'] == cart_item.quantity),
                    0
                ) or cart_item.sub_total
            )
            for cart_item in cart.items.all()
        )


class AddCartItemSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    back_image = serializers.ImageField(required=False)
    front_pdf = serializers.FileField(required=False)
    back_pdf = serializers.FileField(required=False)

    def validate(self, attrs):
        catalog_item = attrs.get('catalog_item')
        image = attrs.get('image')
        back_image = attrs.get('back_image')
        front_pdf = attrs.get('front_pdf')
        back_pdf = attrs.get('back_pdf')
        if catalog_item.item_type != CatalogItem.BUSINESS_CARD:
            if image or back_image:
                raise serializers.ValidationError(
                    {"image": "Image is not allowed for this item type"})
            if front_pdf or back_pdf:
                raise serializers.ValidationError(
                    {"front_pdf": "PDF is not allowed for this item type"})
        # else:
        #     if not image:
        #         raise serializers.ValidationError(
        #             {"image": "Image is required for this item type"})

        return validate_catalog(self.context, attrs, Cart, 'cart', self.instance)

    @transaction.atomic()
    def create(self, validated_data):
        front_pdf = validated_data.get('front_pdf', None)
        back_pdf = validated_data.get('back_pdf', None)
        if front_pdf:
            validated_data['front_pdf_name'] = front_pdf.name
        if back_pdf:
            validated_data['back_pdf_name'] = back_pdf.name
        return save_item(self.context, validated_data, CartItem, 'cart_id', self.instance)

    class Meta:
        model = CartItem
        fields = ["id", "catalog_item", "quantity", 'image', 'back_image', 'front_pdf', 'back_pdf']


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]


class OrderItemSerializer(serializers.ModelSerializer):
    catalog_item = SimpleCatalogItemSerializer()
    details = ItemDetailsSerializer()
    front_pdf = serializers.SerializerMethodField()
    back_pdf = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'catalog_item', 'unit_price',
                  'quantity', 'sub_total', 'tax', 'status',
                  'details', 'front_pdf', 'back_pdf', 'created_at'
                  ]
        
    def get_url(self, field: OrderItem):
        return field.url if field else None
    def get_front_pdf(self, order_item: OrderItem):
        return self.get_url(order_item.front_pdf)
    def get_back_pdf(self, order_item: OrderItem):
        return self.get_url(order_item.back_pdf)


class CreateOrderItemSerializer(serializers.ModelSerializer):
    details = ItemDetailsSerializer(required=False)

    class Meta:
        model = OrderItem
        fields = ['id', 'catalog_item', 'quantity', 'details']

    def validate(self, attrs):
        validated_data = validate_catalog(
            self.context, attrs, Order, 'order', self.instance)

        # If details are provided, validate them
        # if 'details' in attrs:
        #     details_serializer = ItemDetailsSerializer(
        #         data=attrs['details'],
        #         context={
        #             'id': self.context.get('order_id'),
        #             'model': OrderItem
        #         }
        #     )
        #     details_serializer.is_valid(raise_exception=True)

        return validated_data

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop('details', None)
        validated_data['order_id'] = self.context['order_id']

        order_item = super().create(validated_data)

        # Create ItemDetails if provided
        if details_data:
            details_serializer = ItemDetailsSerializer(
                data=details_data,
                context={
                    'id': order_item.id,
                    'model': OrderItem,
                    'is_new': False
                }
            )
            details_serializer.is_valid(raise_exception=True)
            details = details_serializer.save()
            order_item.details = details
            order_item.save()

        return order_item


class UpdateOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'tax', 'status']

    def validate(self, attrs):
        return validate_catalog(self.context, attrs, Order, 'order', self.instance)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer = SimpleCustomerSerializer()
    transactions = TransactionSerializer(many=True, read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    tax = serializers.SerializerMethodField()
    shipment_cost = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'payment_status',
            'placed_at', 'items', 'name',
            'email_address', 'address', 'shipping_address',
            'phone_number', 'company', 'city_state_zip',
            'po_number', 'project_due_date', 'notes',
            'shipments', 'transactions', 'status',
            'tracking_number', 'tax', 'shipment_cost',
            'sub_total', 'total_paid', 'balance',
            "total_price"
        ]

    def get_sub_total(self, obj: Order):
        total_price = sum([item.sub_total for item in obj.items.all()])
        return total_price

    def get_tax(self, obj: Order):
        return sum([item.sub_total * (item.tax / 100) for item in obj.items.all()])

    def get_shipment_cost(self, obj: Order):
        return sum([shipment.shipment_cost for shipment in obj.shipments.all()])

    def get_total_paid(self, obj: Order):
        total_paid = sum([
            transaction.amount if transaction.type == 'payment' else (
                -1 * transaction.amount)
            for transaction in obj.transactions.all()
        ])
        return total_paid

    def get_total_price(self, obj: Order):
        return self.get_sub_total(obj) + self.get_tax(obj) + self.get_shipment_cost(obj)

    def get_balance(self, obj: Order):
        return self.get_total_price(obj) - self.get_total_paid(obj)


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status', 'status']


class CreateOrderSerializer(serializers.ModelSerializer):
    cart_id = serializers.UUIDField(write_only=True)
    auto_send_proof = serializers.BooleanField(default=False)

    class Meta:
        model = Order
        fields = [
            'cart_id', 'name', 'email_address',
            'address', 'shipping_address', 'phone_number',
            'company', 'city_state_zip', 'po_number',
            'project_due_date', 'auto_send_proof',
        ]

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError(
                {'cart_id': 'No cart with the given cart ID was found'})
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('The cart is empty')

        if self.context['customer'] and not Cart.objects.filter(customer=self.context['customer'], pk=cart_id).exists():
            raise serializers.ValidationError(
                'The cart does not belong to the customer')

        return cart_id

    def validate_po_number(self, value):
        if not value:
            return value
        if not re.match(r'^[a-zA-Z0-9]*$', value):
            raise serializers.ValidationError(
                "PO number can only contain letters and numbers.")
        if Order.objects.filter(po_number=value).exists():
            raise serializers.ValidationError(
                "An order with the given PO number already exists.")
        return value

    def validate(self, attrs):
        cart_id = attrs.get('cart_id')
        cart_items = CartItem.objects.select_related(
            "catalog_item").filter(cart_id=cart_id)

        for item in cart_items:
            catalog_item = item.catalog_item
            quantity = item.quantity

            if not catalog_item.can_item_be_ordered:
                raise serializers.ValidationError(
                    f"{catalog_item.title} cannot be ordered.")
            if quantity > catalog_item.available_inventory:
                raise serializers.ValidationError(f"The quantity of\
                            {catalog_item.title} in the cart is more than the available inventory.")

        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        auto_send_proof = validated_data.pop('auto_send_proof')
        cart_id = validated_data.pop('cart_id')
        cart_items = CartItem.objects.select_related(
            "catalog_item").filter(cart_id=cart_id)
        cart = Cart.objects.get(id=cart_id)

        order = Order.objects.create(customer=cart.customer, **validated_data)

        order_items = []
        catalog_items = []
        contains_business_card = False
        attached_files = []

        for item in cart_items:
            catalog_item = item.catalog_item
            quantity = item.quantity

            if catalog_item.item_type == CatalogItem.BUSINESS_CARD:
                contains_business_card = True

            if catalog_item.restrict_orders_to_inventory:
                catalog_item.available_inventory -= quantity
                catalog_items.append(catalog_item)

            if catalog_item.track_inventory_automatically and catalog_item.available_inventory < catalog_item.minimum_inventory:
                catalog = catalog_item.catalog
                if catalog.specify_low_inventory_message:
                    send_mail(
                        subject=catalog.subject,
                        message=catalog.message_text,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[
                            email.strip() for email in catalog.recipient_emails.split(",")],
                        fail_silently=False,
                    )

            unit_price = next(
                (entry['unit_price'] for entry in item.catalog_item.pricing_grid if entry['minimum_quantity'] == item.quantity), item.unit_price)
            sub_total = item.quantity * unit_price

            if item.front_pdf:
                attached_files.append({'url':item.front_pdf.url, 'name': item.front_pdf_name})
            if item.back_pdf:
                attached_files.append({'url':item.back_pdf.url, 'name': item.back_pdf_name})

            order_items.append(OrderItem(
                order=order,
                catalog_item=item.catalog_item,
                sub_total=sub_total,
                unit_price=unit_price,
                quantity=item.quantity,
                details=item.details,
                image=item.image,
                back_image=item.back_image,
                front_pdf=item.front_pdf,
                back_pdf=item.back_pdf,
            ))
        
        if catalog_items:
            CatalogItem.objects.bulk_update(
                catalog_items, ['available_inventory'])
        if order_items:
            OrderItem.objects.bulk_create(order_items)

        Cart.objects.filter(pk=cart_id).delete()

        if auto_send_proof:
            context = {
                'order_number': order.po_number,
                'customer_name': order.name,
                'response_days': 2,
                'wallsprinting_phone': os.getenv('WALLSPRINTING_PHONE'),
                'wallsprinting_website': os.getenv('WALLSPRINTING_WEBSITE'),
                'invoice_number': order.po_number,
                'po_number': order.po_number,
                'payment_submission_link': 'your_payment_submission_link_here'
            }
            template = 'email/order_confirmation_editable.html' if contains_business_card else 'email/order_confirmation.html'
            subject = f"Your Walls Printing Order Confirmation - {order.po_number}"
            message = render_to_string(template, context=context)
            # send_mail(
            #     subject=subject,
            #     message='',
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=[order.email_address],
            #     html_message=message,
            #     fail_silently=False,
            #     attachments=[
            #         (file.name, file.read(), file.content_type) for file in attached_files if file
            #     ]
            # )

            send_html_email_with_attachments(
                subject=subject,
                context=context,
                template_name=template,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[order.email_address],
                files=attached_files,
            )

        return order


class OnlinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlinePayment
        fields = [
            'id',
            'name',
            'email_address',
            'payment_method',
            'invoice_number',
            'po_number',
            'amount',
            'additional_instructions',
        ]

    def validate_po_number(self, value):
        customer = self.context['customer']

        if not value:
            return value
        if not re.match(r'^[a-zA-Z0-9]*$', value):
            raise serializers.ValidationError(
                "PO number can only contain letters and numbers.")
        order = Order.objects.filter(
            customer=customer, po_number=value).first()

        if not order:
            raise serializers.ValidationError("The PO# submitted is invalid")

        if order.status not in [Order.COMPLETED, Order.SHIPPED]:
            raise serializers.ValidationError(
                "The order with the given PO# is not yet completed or shipped.")

        return value

    def validate_payment_method(self, value):
        """
        Ensure the selected payment method is valid.
        """
        if value not in dict(OnlinePayment.PAYMENT_METHOD_CHOICES).keys():
            raise serializers.ValidationError("Invalid payment method.")
        return value

    def create(self, validated_data):
        payment = super().create(validated_data)

        # Send email to the customer
        subject = f"Payment Proof Submitted Successfully - Order {payment.po_number}"
        message = render_to_string('email/payment_confirmation.html', {
            'customer_name': payment.name,
            'po_number': payment.po_number,
            'amount': payment.amount,
        })
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[payment.email_address],
            html_message=message,
            fail_silently=False,
        )

        return payment


class FileExchangeSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = FileExchange
        fields = [
            "name",
            "email_address",
            "recipient_name",
            "recipient_email",
            "details",
            "file",
            "file_size",
            "created_at"
        ]

    def save(self, **kwargs):
        file_transfer = super().save(**kwargs)
        file_transferred.send_robust(
            self.__class__, request=self.context['request'], file_transfer=file_transfer)
        return file_transfer


class CopyCatalogSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    copy_items = serializers.BooleanField(default=False)

    def validate_title(self, value):
        if Catalog.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A catalog with this title already exists.")
        return value


class CopyCatalogItemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    catalog = serializers.PrimaryKeyRelatedField(
        queryset=Catalog.objects.all())

    def validate_title(self, value):
        if CatalogItem.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A catalog item with this title already exists.")
        return value


class CopyPortalSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    copy_the_logo = serializers.BooleanField(default=False)
    same_permissions = serializers.BooleanField(default=False)
    same_catalogs = serializers.BooleanField(default=False)
    same_proofing_categories = serializers.BooleanField(default=False)
    logo = serializers.ImageField(required=False, allow_null=True)
    catalog = serializers.CharField(max_length=255, required=False)
    new_proofing_category = serializers.CharField(
        max_length=255, required=False)
    customers = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), many=True, required=False)
    customer_groups = serializers.PrimaryKeyRelatedField(
        queryset=CustomerGroup.objects.all(), many=True, required=False)

    def validate_title(self, value):
        if Portal.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError(
                "A portal with this title already exists.")
        return value

    def validate(self, data):
        if data['copy_the_logo'] and data.get('logo'):
            raise serializers.ValidationError(
                "You cannot select both 'copy_the_logo' and provide a 'logo'.")

        if data['same_catalogs'] and data.get('catalog'):
            raise serializers.ValidationError(
                "You cannot select both 'same_catalogs' and provide a 'catalog'.")
        if not data['same_catalogs'] and not data.get('catalog'):
            raise serializers.ValidationError(
                "You must provide a 'catalog' if 'same_catalogs' is false.")
        if data.get('catalog') and Catalog.objects.filter(title__iexact=data['catalog']).exists():
            raise serializers.ValidationError(
                "A catalog with this title already exists.")

        if data['same_proofing_categories'] and data.get('new_proofing_category'):
            raise serializers.ValidationError(
                "You cannot select both 'same_proofing_categories' and provide a 'new_proofing_category'.")
        if not data['same_proofing_categories'] and not data.get('new_proofing_category'):
            raise serializers.ValidationError(
                "You must provide a 'new_proofing_category' if 'same_proofing_categories' is false.")

        if data['same_permissions'] and (data.get('customers') or data.get('customer_groups')):
            raise serializers.ValidationError(
                "You cannot provide 'customers' or 'customer_groups' when 'same_permissions' is true.")

        return data


class BusinessCardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, default="John Doe")
    phone = serializers.CharField(max_length=20, default="+123-456-7890")
    email = serializers.EmailField(default="john@example.com")
    business_name = serializers.CharField(
        max_length=150, default="GreenTech Solutions")
    format = serializers.ChoiceField(choices=["svg", "png"], default="svg")


class CreateEditableCatalogItemFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['cdr', 'psd', 'pdf'])]
    )
    file_name = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    file_size = serializers.SerializerMethodField()
    catalog_item_name = serializers.CharField(source='title', write_only=True)

    class Meta:
        model = CatalogItem
        fields = ['id', 'file', 'description', 'sides', 'catalog', 'catalog_item_name',
                  'file_name', 'file_size', 'created_at']

    def validate_file(self, value):
        if value.size > 10 * 1024 * 1024:  # 10MB in bytes
            raise serializers.ValidationError("File size cannot exceed 10MB")
        return value

    def validate(self, attrs):
        catalog_item_name = attrs.get('catalog_item_name')
        catalog = attrs.get('catalog')

        if CatalogItem.objects.filter(title__iexact=catalog_item_name, catalog_id=catalog).exists():
            raise serializers.ValidationError(
                {"catalog_item_name": "A catalog item with this title already exists."})
        return attrs

    @transaction.atomic()
    def create(self, validated_data):
        file = validated_data.get('file')
        file_name = file.name
        file_size = file.size
        validated_data['file_name'] = file_name
        validated_data['file_size'] = file_size
        validated_data['status'] = CatalogItem.PENDING
        validated_data['item_type'] = CatalogItem.BUSINESS_CARD
        validated_data['can_be_edited'] = True
        return super().create(validated_data)

    def get_file_size(self, obj: EditableCatalogItemFile):
        file_size_in_bytes = obj.file_size
        if not file_size_in_bytes:
            return '0KB'
        if file_size_in_bytes >= 1024 * 1024:
            return f"{file_size_in_bytes / (1024 * 1024):.2f} MB"
        return f"{file_size_in_bytes / 1024:.2f} KB"


class UpdateEditableCatalogItemFileSerializer(serializers.ModelSerializer):
    catalog = serializers.PrimaryKeyRelatedField(
        queryset=Catalog.objects.all(), required=False)
    file = serializers.FileField(required=False)
    front_svg_code = serializers.CharField(required=False)
    catalog_item_name = serializers.CharField(write_only=True)

    class Meta:
        model = CatalogItem
        fields = ['id', 'back_svg_code', 'front_svg_code', 'catalog_item_name',
                  'description', 'sides', 'catalog', 'status', 'file']

    def validate_svg_code(self, value):
        if value:
            # Check if string starts with SVG tag
            if not value.strip().startswith('<svg'):
                raise serializers.ValidationError(
                    "Invalid SVG code - must start with <svg> tag")

            # Check if string ends with closing SVG tag
            if not value.strip().endswith('</svg>'):
                raise serializers.ValidationError(
                    "Invalid SVG code - must end with </svg> tag")

            # # Basic XML validation
            # try:
            #     ET.fromstring(value)
            # except ET.ParseError:
            #     raise serializers.ValidationError(
            #         "Invalid SVG code - malformed XML")

        return value

    def validate_front_svg_code(self, value):
        return self.validate_svg_code(value)

    def validate_back_svg_code(self, value):
        return self.validate_svg_code(value)

    def validate(self, attrs):
        back_svg_code = attrs.get('back_svg_code')
        front_svg_code = attrs.get('front_svg_code')
        status = attrs.get('status', None)

        # if self.instance:
        #     if status == CatalogItem.APPROVED and self.instance.status not in [CatalogItem.APPROVING, CatalogItem.UPDATED]:
        #         raise serializers.ValidationError(
        #             {"status": "You can't update status to approved"})

        if back_svg_code and not front_svg_code:
            raise serializers.ValidationError(
                {"front_svg_code": "Front SVG code is required"})

        if front_svg_code:
            fields_to_check = {
                "sides": "You can't update sides now",
                "catalog_item_name": "You can't update catalog item name now",
                "catalog": "You can't update catalog now",
                'file': "You can't update file now"
            }
            for field, error_message in fields_to_check.items():
                if attrs.get(field):
                    raise serializers.ValidationError({field: error_message})

        return attrs

    def update(self, instance, validated_data):
        file = validated_data.get('file', None)
        catalog_item_name = validated_data.pop('catalog_item_name', None)
        front_svg_code = validated_data.get('front_svg_code', None)
        catalog = validated_data.get('catalog', None)
        status = validated_data.get('status', None)
        if catalog_item_name:
            validated_data['title'] = catalog_item_name

        if file or (catalog and status != CatalogItem.PROCESSING):
            validated_data['status'] = CatalogItem.UPDATED
        elif front_svg_code:
            validated_data['status'] = CatalogItem.CONFIRMING

        return super().update(instance, validated_data)


class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = ['id', 'label', 'field_type', 'placeholder', 'prefix']
        read_only_fields = ['created_at', 'updated_at']


class EditableCatalogItemFileSerializer(serializers.ModelSerializer):
    # template_fields = TemplateFieldSerializer(many=True, read_only=True)
    catalog = SimpleCatalogSerializer()
    file_size = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    catalog_item_name = serializers.SerializerMethodField()
    front_svg_code = serializers.SerializerMethodField()
    back_svg_code = serializers.SerializerMethodField()
    template_fields = serializers.SerializerMethodField()

    class Meta:
        model = CatalogItem
        fields = ['id', 'file', 'description', 'sides', 'catalog', 'file_size',
                  'catalog_item_name', 'file_name', 'created_at', "template_fields",
                  'status', 'front_svg_code', 'back_svg_code']

    def get_file_size(self, obj: CatalogItem):
        return CreateEditableCatalogItemFileSerializer.get_file_size(self, obj)

    def get_file(self, obj: CatalogItem):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        return obj.file.url if obj.file else None

    def get_catalog_item_name(self, obj: CatalogItem):
        return obj.title

    
    def get_front_svg_code(self, obj: CatalogItem):
        if obj.file_name:
            return obj.front_svg_code or SVG_TEMPLATE
        return None

    def get_back_svg_code(self, obj: CatalogItem):
        if obj.file_name:
            return obj.back_svg_code or SVG_TEMPLATE
        return None

    def get_template_fields(self, obj: CatalogItem):
        if obj.file_name: 
            return TemplateFieldSerializer(
                obj.template_fields.all(), many=True).data or TEMPLATE_FIELDS
        return None