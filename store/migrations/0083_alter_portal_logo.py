# Generated by Django 5.1.4 on 2025-01-16 13:12

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0082_alter_portal_logo_alter_portalcontent_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portal',
            name='logo',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='auto'),
        ),
    ]
