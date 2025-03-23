from django.contrib import admin
from .models import CustomUser, Role, Page, RolePermission, UserPermission
from django.contrib import admin

# ✅ User Admin
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'phone_number', 'is_active', 'role')
    search_fields = ('username', 'email', 'phone_number')
    list_filter = ('is_active', 'role')

# ✅ Role Admin
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_ar')
    search_fields = ('name', 'name_ar')

# ✅ Page Admin
@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_ar', 'url')
    search_fields = ('name', 'name_ar', 'url')

# ✅ Role Permissions
@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'role', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete',
        'created_by', 'updated_by', 'created_at', 'updated_at'
    )
    list_filter = ('role', 'page')

# ✅ User Permissions
@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'page', 'can_view', 'can_add', 'can_edit', 'can_delete',
        'created_by', 'updated_by', 'created_at', 'updated_at'
    )
    list_filter = ('user', 'page')



admin.site.site_header = "DarArab Admin Panel"
admin.site.site_title = "DarArab Admin"
admin.site.index_title = "Welcome to DarArab Administration"