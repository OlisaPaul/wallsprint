# Generated by Django 5.1.4 on 2025-01-09 20:36

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0071_portalcontent_redirect_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portal',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
