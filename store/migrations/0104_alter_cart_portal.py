# Generated by Django 5.1.6 on 2025-02-20 09:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0103_cart_portal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='portal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='carts', to='store.portal'),
        ),
    ]
