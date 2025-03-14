# Generated by Django 5.1.3 on 2024-11-06 17:46

import store.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_alter_contactinquiry_phone_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinquiry',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_phone_number]),
        ),
        migrations.AlterField(
            model_name='filetransfer',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_phone_number]),
        ),
        migrations.AlterField(
            model_name='quoterequest',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_phone_number]),
        ),
        migrations.AlterField(
            model_name='request',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_phone_number]),
        ),
    ]
