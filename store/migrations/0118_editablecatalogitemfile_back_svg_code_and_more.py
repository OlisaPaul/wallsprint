# Generated by Django 5.1.6 on 2025-03-24 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0117_editablecatalogitemfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='editablecatalogitemfile',
            name='back_svg_code',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='editablecatalogitemfile',
            name='front_svg_code',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='editablecatalogitemfile',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Confirming', 'Confirming')], default='Pending', max_length=20),
        ),
    ]
