# Generated by Django 5.1.6 on 2025-03-24 13:53

import cloudinary.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0116_catalogitem_empty_image_catalogitem_height_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EditableCatalogItemFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sides', models.CharField(choices=[('Front Only', 'Front Only'), ('Front and Back', 'Front and Back')], default='Front Only', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('file', cloudinary.models.CloudinaryField(max_length=255, verbose_name='business_card')),
                ('catalog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='editable_files', to='store.catalog')),
            ],
            options={
                'permissions': [('editable_files', 'Editable Files')],
            },
        ),
    ]
