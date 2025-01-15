# Generated by Django 5.1.4 on 2025-01-14 13:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0076_portalcontent_can_have_catalogs'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='portalcontent',
            name='catalogs',
        ),
        migrations.AlterField(
            model_name='portalcontent',
            name='customer_groups',
            field=models.ManyToManyField(blank=True, related_name='accessible_contents', to='store.customergroup'),
        ),
        migrations.AlterField(
            model_name='portalcontent',
            name='customers',
            field=models.ManyToManyField(blank=True, related_name='portal_contents', to='store.customer'),
        ),
        migrations.AlterField(
            model_name='portalcontent',
            name='portal',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to='store.portal'),
        ),
    ]