# Generated by Django 5.0.6 on 2025-03-24 21:56

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Page Name')),
                ('name_ar', models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='اسم الصفحة')),
                ('url', models.CharField(max_length=255, unique=True, verbose_name='Page URL')),
            ],
            options={
                'db_table': 'page',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Role Name')),
                ('name_ar', models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='اسم الدور')),
            ],
            options={
                'db_table': 'role',
            },
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True, unique=True, verbose_name='Phone Number')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active Status')),
                ('last_login', models.DateTimeField(auto_now=True, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='customuser_groups', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='customuser_permissions', to='auth.permission')),
                ('role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.role', verbose_name='Role')),
            ],
            options={
                'verbose_name': 'User',
                'db_table': 'custom_user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_view', models.BooleanField(default=False, verbose_name='View Permission')),
                ('can_add', models.BooleanField(default=False, verbose_name='Add Permission')),
                ('can_edit', models.BooleanField(default=False, verbose_name='Edit Permission')),
                ('can_delete', models.BooleanField(default=False, verbose_name='Delete Permission')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='role_permissions_created', to=settings.AUTH_USER_MODEL)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.page', verbose_name='Page')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.role', verbose_name='Role')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='role_permissions_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'role_permission',
                'unique_together': {('role', 'page')},
            },
        ),
        migrations.CreateModel(
            name='UserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_view', models.BooleanField(default=False, verbose_name='View Permission')),
                ('can_add', models.BooleanField(default=False, verbose_name='Add Permission')),
                ('can_edit', models.BooleanField(default=False, verbose_name='Edit Permission')),
                ('can_delete', models.BooleanField(default=False, verbose_name='Delete Permission')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_permissions_created', to=settings.AUTH_USER_MODEL)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.page', verbose_name='Page')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_permissions_updated', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'db_table': 'user_permission',
                'unique_together': {('user', 'page')},
            },
        ),
    ]
