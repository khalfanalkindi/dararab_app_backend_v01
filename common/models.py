from django.db import models

class ListType(models.Model):
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    code = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"

class ListItem(models.Model):
    list_type = models.ForeignKey(ListType, on_delete=models.CASCADE, related_name='items')
    value = models.CharField(max_length=100)
    display_name_ar = models.CharField(max_length=255)
    display_name_en = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.display_name_ar} / {self.display_name_en}"
