# Generated by Django 5.1.3 on 2024-12-09 11:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0045_portalcontentcatalogassignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalContentCatalog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=False)),
                ('order_approval', models.BooleanField(default=False)),
                ('catalog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_assignments', to='store.catalog')),
                ('portal_content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='catalog_assignments', to='store.portalcontent')),
            ],
        ),
        migrations.AddField(
            model_name='portalcontent',
            name='catalogs',
            field=models.ManyToManyField(related_name='portal_contents', through='store.PortalContentCatalog', to='store.catalog'),
        ),
        migrations.DeleteModel(
            name='PortalContentCatalogAssignment',
        ),
    ]
