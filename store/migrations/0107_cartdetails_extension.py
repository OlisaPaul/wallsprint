# Generated by Django 5.1.6 on 2025-02-21 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0106_alter_cart_customer_alter_cart_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartdetails',
            name='extension',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
