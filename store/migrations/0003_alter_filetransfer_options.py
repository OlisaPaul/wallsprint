# Generated by Django 5.1.2 on 2024-10-30 20:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_filetransfer_quoterequest_request_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='filetransfer',
            options={'permissions': [('transfer_files', 'Transfer Files')]},
        ),
    ]