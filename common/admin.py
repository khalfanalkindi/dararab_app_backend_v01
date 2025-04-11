from django.contrib import admin
from .models import ListType, ListItem

@admin.register(ListType)
class ListTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_en', 'name_ar', 'code')
    search_fields = ('name_en', 'code')
    readonly_fields = ('created_by', 'updated_by')  

@admin.register(ListItem)
class ListItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'value', 'display_name_en', 'display_name_ar', 'list_type', 'is_active')
    list_filter = ('list_type', 'is_active')
    search_fields = ('value', 'display_name_en', 'display_name_ar')
    readonly_fields = ('created_by', 'updated_by') 
