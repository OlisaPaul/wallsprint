# Generated by Django 5.1.8 on 2025-04-11 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0131_cartitem_back_pdf_name_cartitem_front_pdf_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='templatefield',
            name='prefix',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
