# Generated by Django 5.1.3 on 2024-12-04 11:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0041_rename_total_price_cartitem_sub_total'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cartitem',
            unique_together={('catalog_item', 'cart', 'quantity')},
        ),
    ]
