# Generated by Django 5.1.3 on 2024-12-10 07:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0047_onlinepayment_created_at_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='onlinepayment',
            old_name='email',
            new_name='email_address',
        ),
    ]