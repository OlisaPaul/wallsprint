# Generated by Django 5.1.4 on 2025-01-28 10:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0095_alter_catalogitem_item_type'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cartitem',
            unique_together=set(),
        ),
    ]
