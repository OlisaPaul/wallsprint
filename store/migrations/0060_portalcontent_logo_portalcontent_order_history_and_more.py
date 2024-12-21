# Generated by Django 5.1.4 on 2024-12-21 07:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0059_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='portalcontent',
            name='logo',
            field=models.ImageField(null=True, upload_to='logos/'),
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='order_history',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='payment_proof',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='portal',
            name='logo',
            field=models.ImageField(null=True, upload_to='logos/'),
        ),
    ]
