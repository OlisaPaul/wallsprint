# Generated by Django 5.1.3 on 2024-11-19 21:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0021_remove_portalcontent_title_alter_htmlfile_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='htmlfile',
            name='link',
            field=models.FileField(upload_to='html_files/'),
        ),
    ]
