# Generated by Django 5.1.3 on 2024-12-10 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0048_rename_email_onlinepayment_email_address'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileExchange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_name', models.CharField(max_length=255)),
                ('recipient_email', models.EmailField(max_length=254)),
                ('sender_name', models.CharField(default='System Account', max_length=255)),
                ('sender_email', models.EmailField(max_length=254)),
                ('details', models.TextField(blank=True, null=True)),
                ('file', models.FileField(upload_to='uploads/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
