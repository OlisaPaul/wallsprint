# Generated by Django 5.1.4 on 2024-12-21 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0062_delete_staffnotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='quoterequest',
            name='status',
            field=models.CharField(choices=[('New', 'New'), ('Pending', 'Pending'), ('Processing', 'Processing'), ('Completed', 'Completed')], default='New', max_length=50),
        ),
    ]
