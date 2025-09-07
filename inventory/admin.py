from django.contrib import admin
from .models import (
    Author, PrintRun, PrintTask, Stakeholder, Translator, RightsOwner, Reviewer,
    Project, Contract, Product, Warehouse, Inventory, Transfer
)
from common.models import ListItem


# ========== Product & PrintRun ==========  
class PrintRunInline(admin.TabularInline):
    model = PrintRun
    extra = 1  # how many blank editions to show by default

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [PrintRunInline]

    list_display = (
        'id', 'isbn', 'title_ar', 'title_en',
        'project', 'author', 'translator', 'rights_owner', 'reviewer',
        'status', 'language', 'is_direct_product', 'created_by'
    )
    search_fields = ('isbn', 'title_ar', 'title_en')
    list_filter   = ('status', 'language', 'is_direct_product')

    fieldsets = (
        ('Basic Information', {
            'fields': ['isbn', 'title_ar', 'title_en', 'project'],
        }),
        ('Cover & Design', {
            'fields': ['cover_design'],
        }),
        ('People & Stakeholders', {
            'fields': ['author', 'translator', 'rights_owner', 'reviewer'],
        }),
        # removed published_at here
        ('General Details', {
            'fields': ['is_direct_product'],
        }),
        ('Classification', {
            'fields': ['genre', 'status', 'language'],
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="product_status")
        elif db_field.name == "genre":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="genre")
        elif db_field.name == "language":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="language")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(PrintRun)
class PrintRunAdmin(admin.ModelAdmin):
    list_display  = ('id', 'product', 'edition_number', 'print_cost', 'price', 'status')
    search_fields = ('product__title_en', 'product__isbn')
    list_filter   = ('status',)
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
    list_display = ('id', 'title_ar', 'approval_status', 'progress_status', 'language', 'author', 'translator')
    list_filter = ('approval_status', 'progress_status', 'language')
    search_fields = ('title_ar', 'title_original')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="projects_status")
        elif db_field.name == "progress_status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="progress_status")
        elif db_field.name == "type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="projects_type")
        elif db_field.name == "language":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="language")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ========== Contract ==========

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'contract_type', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'contract_type')
    search_fields = ('title', 'project__title_ar', 'project__title_original')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "contract_type":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="contract_type")
        elif db_field.name == "status":
            kwargs["queryset"] = ListItem.objects.filter(list_type__code="contract_status")
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

# ========== Stakeholder ==========
@admin.register(Stakeholder)
class StakeholderAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone')
    search_fields = ('name', 'contact_person', 'email')
    list_filter = ('created_at',)