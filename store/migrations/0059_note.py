# Generated by Django 5.1.3 on 2024-12-19 17:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('store', '0058_filetransfer_status_request_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('object_id', models.PositiveIntegerField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='notes', to=settings.AUTH_USER_MODEL)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
