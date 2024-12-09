# Generated by Django 5.1.3 on 2024-12-06 14:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0044_order_date_needed'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalContentCatalogAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=False)),
                ('order_approval', models.BooleanField(default=False)),
                ('Catalog', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assigned_portals', to='store.portalcontent')),
                ('portal_content', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assigned_catalogs', to='store.portalcontent')),
            ],
        ),
    ]
