from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name=_("Phone Number"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active Status"))
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Role"))
    last_login = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_groups",
        blank=True,
        help_text=_("The groups this user belongs to.")
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_permissions",
        blank=True,
        help_text=_("Specific permissions for this user.")
    )

    class Meta:
        db_table = "custom_user"
        verbose_name = _("User")

    def __str__(self):
        return self.username

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Role Name"))
    name_ar = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name=_("اسم الدور"))

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.name

class Page(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Page Name"))
    name_ar = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name=_("اسم الصفحة"))
    url = models.CharField(max_length=255, unique=True, verbose_name=_("Page URL"))

    class Meta:
        db_table = "page"

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))
    page = models.ForeignKey(Page, on_delete=models.CASCADE, verbose_name=_("Page"))
    can_view = models.BooleanField(default=False, verbose_name=_("View Permission"))
    can_add = models.BooleanField(default=False, verbose_name=_("Add Permission"))
    can_edit = models.BooleanField(default=False, verbose_name=_("Edit Permission"))
    can_delete = models.BooleanField(default=False, verbose_name=_("Delete Permission"))

    class Meta:
        unique_together = ('role', 'page')
        db_table = "role_permission"

    def __str__(self):
        return f"{self.role.name} - {self.page.name}"

class UserPermission(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("User"))
    page = models.ForeignKey(Page, on_delete=models.CASCADE, verbose_name=_("Page"))
    can_view = models.BooleanField(default=False, verbose_name=_("View Permission"))
    can_add = models.BooleanField(default=False, verbose_name=_("Add Permission"))
    can_edit = models.BooleanField(default=False, verbose_name=_("Edit Permission"))
    can_delete = models.BooleanField(default=False, verbose_name=_("Delete Permission"))

    class Meta:
        unique_together = ('user', 'page')
        db_table = "user_permission"

    def __str__(self):
        return f"{self.user.username} - {self.page.name}"
