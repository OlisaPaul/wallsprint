# Generated by Django 5.1.3 on 2024-12-10 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0050_rename_sender_email_fileexchange_email_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileexchange',
            name='file_size',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]