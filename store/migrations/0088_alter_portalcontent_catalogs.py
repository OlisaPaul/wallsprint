# Generated by Django 5.1.4 on 2025-01-23 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0087_catalogitem_can_be_edited_alter_portalcontent_logo_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portalcontent',
            name='catalogs',
            field=models.ManyToManyField(blank=True, related_name='portal_contents', to='store.catalog'),
        ),
    ]
