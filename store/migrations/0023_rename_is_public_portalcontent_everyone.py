# Generated by Django 5.1.3 on 2024-11-19 22:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_alter_htmlfile_link'),
    ]

    operations = [
        migrations.RenameField(
            model_name='portalcontent',
            old_name='is_public',
            new_name='everyone',
        ),
    ]
