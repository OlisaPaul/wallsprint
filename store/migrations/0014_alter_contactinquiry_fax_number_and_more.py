# Generated by Django 5.1.3 on 2024-11-06 10:01

import store.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0013_alter_contactinquiry_fax_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinquiry',
            name='fax_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_number]),
        ),
        migrations.AlterField(
            model_name='filetransfer',
            name='fax_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_number]),
        ),
        migrations.AlterField(
            model_name='quoterequest',
            name='fax_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_number]),
        ),
        migrations.AlterField(
            model_name='request',
            name='fax_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_number]),
        ),
    ]
