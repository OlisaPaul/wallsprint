# Generated by Django 5.1.4 on 2025-01-16 12:42

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0081_alter_cartitem_unit_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portal',
            name='logo',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='image'),
        ),
        migrations.AlterField(
            model_name='portalcontent',
            name='logo',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='image'),
        ),
    ]
