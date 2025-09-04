from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, F
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Customer, Invoice, InvoiceItem, Payment, Return


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'institution_name', 'type', 'contact_person', 'phone', 'email', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('institution_name', 'contact_person', 'phone', 'email')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'composite_id_link', 'customer', 'warehouse', 'invoice_type', 
        'payment_method', 'total_amount_display', 'payment_status_display',
        'is_fully_paid_display', 'created_at'
    )
    list_filter = (
        'invoice_type', 'payment_method', 'warehouse', 'is_returnable',
        'created_at', 'main_invoice'
    )
    search_fields = ('composite_id', 'customer__institution_name', 'customer__contact_person')
    readonly_fields = (
        'composite_id', 'total_amount', 'total_paid_amount', 'total_remaining_amount',
        'payment_status', 'is_fully_paid', 'has_partial_payments',
        'created_by', 'updated_by', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('composite_id', 'customer', 'warehouse', 'invoice_type', 'payment_method')
        }),
        ('Invoice Details', {
            'fields': ('is_returnable', 'main_invoice', 'notes')
        }),
        ('Payment Information', {
            'fields': ('total_amount', 'total_paid_amount', 'total_remaining_amount', 'payment_status'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_fully_paid', 'has_partial_payments'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['recalculate_payment_status', 'generate_child_invoice']

    def composite_id_link(self, obj):
        url = reverse('admin:sales_invoice_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.composite_id)
    composite_id_link.short_description = 'Composite ID'
    composite_id_link.admin_order_field = 'composite_id'
    
    # def get_form(self, request, obj=None, **kwargs):
    #     form = super().get_form(request, obj, **kwargs)
    #     form.base_fields['composite_id'].label = 'Composite ID (e.g., 161 or 223-161)'
    #     form.base_fields['composite_id'].help_text = 'Enter custom ID or leave blank for auto-generation. Format: bill_id-main_invoice for child invoices.'
    #     return form
    
    def total_amount_display(self, obj):
        return format_html("${:.2f}", obj.total_amount)
    total_amount_display.short_description = 'Total Amount'
    
    def payment_status_display(self, obj):
        if obj.payment_status == 100:
            color = 'green'
        elif obj.payment_status > 0:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, obj.payment_status
        )
    payment_status_display.short_description = 'Payment Status'
    
    def is_fully_paid_display(self, obj):
        if obj.is_fully_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        elif obj.total_paid_amount > 0:
            return format_html('<span style="color: orange;">Partial</span>')
        else:
            return format_html('<span style="color: red;">Unpaid</span>')
    is_fully_paid_display.short_description = 'Payment Status'
    
    def recalculate_payment_status(self, request, queryset):
        for invoice in queryset:
            invoice.recalculate_payment_status()
        self.message_user(request, f"Payment status recalculated for {queryset.count()} invoices.")
    recalculate_payment_status.short_description = "Recalculate payment status"
    
    def generate_child_invoice(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one invoice to generate a child invoice.", level='ERROR')
            return
        
        invoice = queryset.first()
        try:
            child_invoice = invoice.generate_child_invoice(paid_items_only=True)
            self.message_user(request, f"Child invoice #{child_invoice.composite_id} generated successfully.")
        except Exception as e:
            self.message_user(request, f"Error generating child invoice: {str(e)}", level='ERROR')
    generate_child_invoice.short_description = "Generate child invoice from selected invoice"
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        
        # If composite_id is manually provided, use it; otherwise let the model auto-generate
        if not obj.composite_id:
            # Let the model's save method handle auto-generation
            pass
        # If composite_id is provided, it will be saved as-is
        
        super().save_model(request, obj, form, change)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'invoice_link', 'product', 'quantity', 'unit_price', 
        'discount_percent', 'total_price', 'payment_status_display', 'is_paid_display'
    )
    list_filter = ('is_paid', 'invoice__invoice_type', 'invoice__warehouse')
    search_fields = ('invoice__composite_id', 'product__title_ar', 'product__title_en')
    readonly_fields = (
        'total_price', 'remaining_amount', 'payment_status', 'payment_status_display',
        'item_total_amount', 'item_paid_amount', 'item_remaining_amount',
        'created_by', 'updated_by', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice', 'product', 'quantity', 'unit_price', 'discount_percent')
        }),
        ('Payment Information', {
            'fields': ('total_price', 'paid_amount', 'remaining_amount', 'is_paid')
        }),
        ('Payment Summary', {
            'fields': ('item_total_amount', 'item_paid_amount', 'item_remaining_amount')
        }),
        ('Status', {
            'fields': ('payment_status', 'payment_status_display'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def invoice_link(self, obj):
        if obj.invoice:
            url = reverse('admin:sales_invoice_change', args=[obj.invoice.id])
            return format_html('<a href="{}">{}</a>', url, obj.invoice.composite_id)
        return '-'
    invoice_link.short_description = 'Invoice'
    
    def payment_status_display(self, obj):
        if obj.payment_status == 100:
            color = 'green'
        elif obj.payment_status > 0:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, obj.payment_status
        )
    payment_status_display.short_description = 'Payment Status'
    
    def is_paid_display(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        elif obj.paid_amount > 0:
            return format_html('<span style="color: orange;">Partial</span>')
        else:
            return format_html('<span style="color: red;">Unpaid</span>')
    is_paid_display.short_description = 'Paid'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'invoice_link', 'amount', 'payment_type_display', 
        'payment_date', 'is_partial_payment_display', 'payment_summary_display'
    )
    list_filter = ('payment_type', 'payment_date', 'invoice__invoice_type')
    search_fields = ('invoice__composite_id', 'reference_number', 'notes')
    readonly_fields = (
        'payment_type_display', 'is_partial_payment', 'payment_summary_display',
        'invoice_total_amount', 'invoice_paid_amount', 'invoice_remaining_amount',
        'created_by', 'updated_by', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Payment Information', {
            'fields': ('invoice', 'amount', 'payment_date', 'payment_type', 'reference_number')
        }),
        ('Payment Summary', {
            'fields': ('invoice_total_amount', 'invoice_paid_amount', 'invoice_remaining_amount')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Status', {
            'fields': ('payment_type_display', 'is_partial_payment', 'payment_summary_display'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['redistribute_payment']
    
    def invoice_link(self, obj):
        if obj.invoice:
            url = reverse('admin:sales_invoice_change', args=[obj.invoice.id])
            return format_html('<a href="{}">{}</a>', url, obj.invoice.composite_id)
        return '-'
    invoice_link.short_description = 'Invoice'
    
    def payment_type_display(self, obj):
        return obj.payment_type_display
    payment_type_display.short_description = 'Payment Type'
    
    def is_partial_payment_display(self, obj):
        if obj.is_partial_payment:
            return format_html('<span style="color: orange;">Partial</span>')
        else:
            return format_html('<span style="color: green;">Full</span>')
    is_partial_payment_display.short_description = 'Payment Type'
    
    def payment_summary_display(self, obj):
        """Display payment summary in a compact format"""
        return format_html(
            'Total: {:.2f} | Paid: {:.2f} | Due: {:.2f}',
            obj.invoice_total_amount,
            obj.invoice_paid_amount,
            obj.invoice_remaining_amount
        )
    payment_summary_display.short_description = 'Payment Summary'
    
    def redistribute_payment(self, request, queryset):
        for payment in queryset:
            payment.distribute_payment_to_items()
        self.message_user(request, f"Payment distribution updated for {queryset.count()} payments.")
    redistribute_payment.short_description = "Redistribute payment to invoice items"
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_item_link', 'returned_quantity', 'return_date', 'created_at')
    list_filter = ('return_date', 'created_at')
    search_fields = ('invoice_item__product__title_ar', 'invoice_item__product__title_en')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
    
    def invoice_item_link(self, obj):
        if obj.invoice_item:
            url = reverse('admin:sales_invoiceitem_change', args=[obj.invoice_item.id])
            return format_html('<a href="{}">Item {}</a>', url, obj.invoice_item.id)
        return '-'
    invoice_item_link.short_description = 'Invoice Item'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
