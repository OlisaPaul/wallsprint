# Generated by Django 5.1.2 on 2024-10-21 12:35

import cloudinary.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContactInquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('fax_number', models.CharField(blank=True, max_length=20, null=True)),
                ('company', models.CharField(blank=True, max_length=255)),
                ('city_state_zip', models.CharField(max_length=255)),
                ('country', models.CharField(max_length=255)),
                ('questions', models.TextField()),
                ('comments', models.TextField(blank=True)),
                ('preferred_mode_of_response', models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProjectQuoteRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('fax_number', models.CharField(blank=True, max_length=20, null=True)),
                ('company', models.CharField(blank=True, max_length=255)),
                ('city_state_zip', models.CharField(max_length=255)),
                ('country', models.CharField(max_length=255)),
                ('preferred_mode_of_response', models.CharField(choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50)),
                ('artwork_provided', models.CharField(blank=True, choices=[('None', 'None'), ('Online file transfer', 'Online file transfer'), ('On disk', 'On disk'), ('Hard copy', 'Hard copy'), ('Film provided', 'Film provided'), ('Please estimate for design', 'Please estimate for design')], max_length=50)),
                ('project_name', models.CharField(max_length=255)),
                ('additional_details', models.TextField(blank=True)),
                ('uploaded_files', cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='image')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.URLField(max_length=500)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='contact_manager.projectquoterequest')),
            ],
        ),
    ]
