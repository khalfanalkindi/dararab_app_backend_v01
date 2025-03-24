# Generated by Django 5.0.6 on 2025-03-24 13:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ListType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='ListItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100)),
                ('display_name_ar', models.CharField(max_length=255)),
                ('display_name_en', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('list_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='common.listtype')),
            ],
        ),
    ]
