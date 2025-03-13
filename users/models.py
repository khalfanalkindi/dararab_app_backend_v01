from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_groups",
        blank=True,
        help_text="The groups this user belongs to."
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_permissions",
        blank=True,
        help_text="Specific permissions for this user."
    )

    class Meta:
        db_table = "custom_user"

    def __str__(self):
        return self.username

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.name

class Page(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "page"

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'page')
        db_table = "role_permission"

    def __str__(self):
        return f"{self.role.name} - {self.page.name}"

class UserPermission(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'page')
        db_table = "user_permission"

    def __str__(self):
        return f"{self.user.username} - {self.page.name}"
