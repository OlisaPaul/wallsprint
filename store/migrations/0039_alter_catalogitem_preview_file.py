# Generated by Django 5.1.3 on 2024-12-03 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0038_rename_parent_catalog_catalogitem_catalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalogitem',
            name='preview_file',
            field=models.FileField(blank=True, null=True, upload_to='preview_files/'),
        ),
    ]
