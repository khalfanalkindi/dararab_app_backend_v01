from django.contrib import admin
from .models import (
    Author, PrintTask, Translator, RightsOwner, Reviewer,
    Project, Contract, Product, Warehouse, Inventory, Transfer
)
from common.models import ListItem

# ========== Product ==========
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'isbn', 'price', 'published_at', 'status', 'created_by')
    search_fields = ('isbn',)
    list_filter = ('status', 'is_direct_product')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="product_status")
        elif db_field.name == "genre":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="genre")  # لو عندك genre
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ========== Warehouse ==========
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_en','name_ar', 'type', 'location', 'created_by')
    search_fields = ('name', 'location')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="warehouse_type")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ========== Inventory ==========
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'warehouse', 'quantity', 'created_by')
    list_filter = ('warehouse',)

# ========== Transfer ==========
@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'from_warehouse', 'to_warehouse', 'quantity', 'transfer_date')
    list_filter = ('from_warehouse', 'to_warehouse')

# ========== People ==========
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Translator)
class TranslatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(RightsOwner)
class RightsOwnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Reviewer)
class ReviewerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# ========== Project ==========
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_ar', 'approval_status', 'progress_status', 'author', 'translator')
    list_filter = ('approval_status', 'progress_status')
    search_fields = ('title_ar', 'title_original')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="project_status")
        elif db_field.name == "progress_status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="project_progress")
        elif db_field.name == "type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="project_type")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ========== Contract ==========
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'contract_type', 'author', 'translator', 'rights_owner', 'reviewer', 'commission_percent', 'fixed_amount')
    list_filter = ('contract_type',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "contract_type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="contract_type")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ========== PrintTask ==========
@admin.register(PrintTask)
class PrintTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'task_type', 'status', 'due_date')
    list_filter = ('task_type', 'status')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "task_type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="print_task_type")
        elif db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="print_task_status")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
