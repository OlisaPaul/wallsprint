# Generated by Django 5.1.3 on 2024-11-06 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0014_alter_contactinquiry_fax_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filetransfer',
            name='additional_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='request',
            name='additional_details',
            field=models.TextField(blank=True, null=True),
        ),
    ]
