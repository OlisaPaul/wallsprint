# Generated by Django 5.1.2 on 2024-10-30 18:28

import cloudinary.models
import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('store', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('fax_number', models.CharField(blank=True, max_length=20, null=True)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('city_state_zip', models.CharField(max_length=255, null=True)),
                ('country', models.CharField(max_length=255, null=True)),
                ('preferred_mode_of_response', models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('additional_details', models.TextField(blank=True)),
                ('file_type', models.CharField(choices=[('PC', 'PC'), ('MACINTOSH', 'MACINTOSH')], max_length=50)),
                ('application_type', models.CharField(choices=[('MULTIPLE', 'MULTIPLE (COMPRESSED)'), ('ACROBAT', 'ACROBAT (PDF)'), ('CORELDRAW', 'CORELDRAW'), ('EXCEL', 'EXCEL'), ('FONTS', 'FONTS'), ('FREEHAND', 'FREEHAND'), ('ILLUSTRATOR', 'ILLUSTRATOR'), ('INDESIGN', 'INDESIGN'), ('PAGEMAKER', 'PAGEMAKER'), ('PHOTOSHOP', 'PHOTOSHOP'), ('POWERPOINT', 'POWERPOINT'), ('PUBLISHER', 'PUBLISHER'), ('WORD', 'WORD'), ('QUARKXPRESS', 'QUARKXPRESS'), ('OTHER', 'OTHER')], max_length=255)),
                ('other_application_type', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='QuoteRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('fax_number', models.CharField(blank=True, max_length=20, null=True)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('city_state_zip', models.CharField(max_length=255, null=True)),
                ('country', models.CharField(max_length=255, null=True)),
                ('preferred_mode_of_response', models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('artwork_provided', models.CharField(blank=True, choices=[('None', 'None'), ('Online file transfer', 'Online file transfer'), ('On disk', 'On disk'), ('Hard copy', 'Hard copy'), ('Film provided', 'Film provided'), ('Please estimate for design', 'Please estimate for design')], max_length=50, null=True)),
                ('project_name', models.CharField(max_length=255, null=True)),
                ('project_due_date', models.DateField(default=datetime.date.today)),
                ('additional_details', models.TextField(blank=True, null=True)),
                ('this_is_an', models.CharField(blank=True, choices=[('Order Request', 'Order Request'), ('Quote Request', 'Quote Request')], max_length=50, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email_address', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=20)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('fax_number', models.CharField(blank=True, max_length=20, null=True)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('city_state_zip', models.CharField(max_length=255, null=True)),
                ('country', models.CharField(max_length=255, null=True)),
                ('preferred_mode_of_response', models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('artwork_provided', models.CharField(blank=True, choices=[('None', 'None'), ('Online file transfer', 'Online file transfer'), ('On disk', 'On disk'), ('Hard copy', 'Hard copy'), ('Film provided', 'Film provided'), ('Please estimate for design', 'Please estimate for design')], max_length=50)),
                ('project_name', models.CharField(max_length=255)),
                ('project_due_date', models.DateField(default=datetime.date.today)),
                ('additional_details', models.TextField(blank=True)),
                ('you_are_a', models.CharField(choices=[('New Customer', 'New Customer'), ('Current Customer', 'Current Customer')], max_length=50)),
                ('this_is_an', models.CharField(choices=[('Order Request', 'Order Request'), ('Estimate Request', 'Estimate Request')], max_length=50)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='city_state_zip',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='company',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='country',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='preferred_mode_of_response',
            field=models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50, null=True),
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company', models.CharField(max_length=255)),
                ('address', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=255)),
                ('state', models.CharField(max_length=255)),
                ('zip', models.CharField(max_length=255)),
                ('phone_number', models.CharField(max_length=255)),
                ('fax_number', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('pay_tax', models.BooleanField()),
                ('third_party_identifier', models.CharField(max_length=255)),
                ('credit_balance', models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='auto')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='ProjectQuoteRequest',
        ),
    ]
