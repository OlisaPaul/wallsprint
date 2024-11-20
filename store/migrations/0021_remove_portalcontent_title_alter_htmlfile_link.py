# Generated by Django 5.1.3 on 2024-11-19 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0020_htmlfile_portal_alter_customer_address_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='portalcontent',
            name='title',
        ),
        migrations.AlterField(
            model_name='htmlfile',
            name='link',
            field=models.FileField(null=True, upload_to='html_files/'),
        ),
    ]