from django.db import models
from django.conf import settings

class ListType(models.Model):
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    code = models.CharField(max_length=100)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_list_types'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_list_types'
    )

    def __str__(self):
        name_ar = self.name_ar or "No Arabic Name"
        name_en = self.name_en or "No English Name"
        return f"{name_ar} / {name_en}"

class ListItem(models.Model):
    list_type = models.ForeignKey(ListType, on_delete=models.CASCADE, related_name='items')
    value = models.CharField(max_length=100)
    display_name_ar = models.CharField(max_length=255)
    display_name_en = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_list_items'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_list_items'
    )

    def __str__(self):
        name_ar = self.display_name_ar or "No Arabic Name"
        name_en = self.display_name_en or "No English Name"
        return f"{name_ar} / {name_en}"
