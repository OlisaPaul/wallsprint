# Generated by Django 5.1.4 on 2025-01-14 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0077_remove_portalcontent_catalogs_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portalcontent',
            name='catalogs',
            field=models.ManyToManyField(related_name='portal_contents', to='store.catalog'),
        ),
    ]
