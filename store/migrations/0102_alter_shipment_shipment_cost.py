# Generated by Django 5.1.5 on 2025-02-10 14:00

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0101_alter_orderitem_tax'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shipment',
            name='shipment_cost',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
    ]
