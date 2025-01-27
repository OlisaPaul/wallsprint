# Generated by Django 5.1.4 on 2025-01-27 09:36

import django.db.models.deletion
import django.utils.timezone
import store.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0090_alter_orderitem_sub_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='additional_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='billing_info',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.billinginfo'),
        ),
        migrations.AddField(
            model_name='order',
            name='country',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='fax_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_number]),
        ),
        migrations.AddField(
            model_name='order',
            name='portal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.portal'),
        ),
        migrations.AddField(
            model_name='order',
            name='preferred_mode_of_response',
            field=models.CharField(blank=True, choices=[('Email', 'Email'), ('Phone', 'Phone'), ('Fax', 'Fax')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('New', 'New'), ('Pending', 'Pending'), ('Processing', 'Processing'), ('Completed', 'Completed'), ('Shipped', 'Shipped')], default='New', max_length=50),
        ),
        migrations.AlterField(
            model_name='filetransfer',
            name='billing_info',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.billinginfo'),
        ),
        migrations.AlterField(
            model_name='order',
            name='city_state_zip',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[store.models.validate_phone_number]),
        ),
    ]
