# Generated by Django 5.1.4 on 2025-01-17 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0084_alter_catalogitem_preview_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='sub_total',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=6),
            preserve_default=False,
        ),
    ]
