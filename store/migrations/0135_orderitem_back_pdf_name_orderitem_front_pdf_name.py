# Generated by Django 5.1.8 on 2025-04-23 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0134_alter_templatefield_field_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='back_pdf_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='front_pdf_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
