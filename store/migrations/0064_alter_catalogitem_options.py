# Generated by Django 5.1.4 on 2024-12-22 18:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0063_quoterequest_status'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='catalogitem',
            options={'permissions': [('catalog_items', 'Catalog Items')]},
        ),
    ]
