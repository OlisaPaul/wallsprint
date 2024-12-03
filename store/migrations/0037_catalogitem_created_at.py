# Generated by Django 5.1.3 on 2024-12-03 10:08

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0036_catalogitem_preview_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalogitem',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]