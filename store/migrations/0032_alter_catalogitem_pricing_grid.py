# Generated by Django 5.1.3 on 2024-12-02 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0031_alter_catalogitem_pricing_grid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalogitem',
            name='pricing_grid',
            field=models.JSONField(default=list),
        ),
    ]
