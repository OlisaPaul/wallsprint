# Generated by Django 5.1.3 on 2024-11-10 23:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0008_extendedgroup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extendedgroup',
            name='group',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.group'),
        ),
    ]
