from django.contrib import admin
from .models import Customer, Invoice, InvoiceItem, Payment, Return

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'institution_name', 'type', 'contact_person', 'phone')
    search_fields = ('institution_name', 'contact_person')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'warehouse', 'invoice_type', 'payment_method', 'created_at')
    list_filter = ('invoice_type', 'payment_method', 'warehouse')

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'product', 'quantity', 'unit_price', 'total_price')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'amount', 'payment_date')

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_item', 'returned_quantity', 'return_date')
