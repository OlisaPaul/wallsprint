# Generated by Django 5.1.4 on 2025-01-02 12:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0070_alter_filetransfer_status_alter_quoterequest_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portalcontent',
            name='redirect_code',
            field=models.CharField(choices=[('default', 'Default'), ('301', '301'), ('302', '302')], default='default', max_length=50),
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='redirect_file',
            field=models.FileField(blank=True, null=True, upload_to='redirect_files/'),
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='redirect_page',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='redirect_content', to='store.portalcontent'),
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='redirect_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
