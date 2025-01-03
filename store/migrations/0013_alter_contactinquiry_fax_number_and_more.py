# Generated by Django 5.1.3 on 2024-11-06 09:43

import phonenumber_field.modelfields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_alter_contactinquiry_fax_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinquiry',
            name='fax_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, error_messages={'invalid': 'Please enter a valid fax number.'}, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='contactinquiry',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='filetransfer',
            name='fax_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, error_messages={'invalid': 'Please enter a valid fax number.'}, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='filetransfer',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='quoterequest',
            name='fax_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, error_messages={'invalid': 'Please enter a valid fax number.'}, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='quoterequest',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='request',
            name='fax_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, error_messages={'invalid': 'Please enter a valid fax number.'}, max_length=128, null=True, region='US'),
        ),
        migrations.AlterField(
            model_name='request',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region='US'),
        ),
    ]
