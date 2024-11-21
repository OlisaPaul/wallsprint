# Generated by Django 5.1.3 on 2024-11-20 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0024_portal_copy_from_portal_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='portal',
            name='customer_groups',
            field=models.ManyToManyField(blank=True, related_name='portals', to='store.customergroup'),
        ),
        migrations.AddField(
            model_name='portal',
            name='customers',
            field=models.ManyToManyField(blank=True, related_name='portals', to='store.customer'),
        ),
    ]
