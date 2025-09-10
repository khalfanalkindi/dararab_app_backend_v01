from rest_framework import serializers
from django_filters import rest_framework as filters

from common.models import ListItem
from inventory.models import Warehouse
from .models import Customer, Invoice, InvoiceItem, Payment, Return
from django.db.models import Sum
from decimal import Decimal



class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class InvoiceSerializer(serializers.ModelSerializer):
    invoice_number = serializers.SerializerMethodField()
    composite_id = serializers.SerializerMethodField()
    display_id = serializers.SerializerMethodField()
    invoice_type_display = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    total_paid_amount = serializers.SerializerMethodField()
    total_remaining_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    is_fully_paid = serializers.SerializerMethodField()
    has_partial_payments = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source='customer', write_only=True, required=False
    )
    warehouse = serializers.SerializerMethodField()
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source='warehouse', write_only=True, required=False
    )
    invoice_type = serializers.SerializerMethodField()
    invoice_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='invoice_type', write_only=True, required=False
    )
    payment_method = serializers.SerializerMethodField()
    payment_method_id = serializers.PrimaryKeyRelatedField(
        queryset=ListItem.objects.all(), source='payment_method', write_only=True, required=False
    )
    main_invoice_id = serializers.PrimaryKeyRelatedField(
        source='main_invoice',
        queryset=Invoice.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Invoice
        fields = '__all__'
    
    def get_composite_id(self, obj):
        """Get composite ID (main_invoice-id or just id)"""
        return obj.composite_id
    
    def get_display_id(self, obj):
        """Get display ID based on context"""
        display_type = self.context.get('display_type', 'composite')
        
        if display_type == 'composite':
            return obj.composite_id
        elif display_type == 'simple':
            return str(obj.id)
        elif display_type == 'parent_child':
            if obj.main_invoice:
                return f"{obj.main_invoice.id}.{obj.id}"
            return str(obj.id)
        
        return obj.composite_id
    
    def get_invoice_number(self, obj):
        """Use composite_id for invoice number"""
        return obj.composite_id
    
    def get_total_amount(self, obj):
        return float(obj.total_amount)
    
    def get_total_paid_amount(self, obj):
        return float(obj.total_paid_amount)

    def get_total_remaining_amount(self, obj):
        return float(obj.total_remaining_amount)
    
    def get_payment_status(self, obj):
        return float(obj.payment_status)
    
    def get_is_fully_paid(self, obj):
        return bool(obj.is_fully_paid)
    
    def get_has_partial_payments(self, obj):
        return bool(obj.has_partial_payments)
    
    def get_invoice_type_display(self, obj):
        """Enhanced invoice type display with sub-invoice indicator"""
        base_type = obj.invoice_type.display_name_en if obj.invoice_type else "Unknown"
        if obj.main_invoice:
            return f"{base_type} (Sub-Invoice)"
        return f"{base_type} (Main Invoice)"

    def get_customer(self, obj):
        if obj.customer:
            return {
                'id': obj.customer.id,
                'institution_name': obj.customer.institution_name,
                'contact_person': obj.customer.contact_person,
            }
        return None

    def get_warehouse(self, obj):
        if obj.warehouse:
            return {
                'id': obj.warehouse.id,
                'name_en': obj.warehouse.name_en,
                'name_ar': obj.warehouse.name_ar,
            }
        return None

    def get_invoice_type(self, obj):
        if obj.invoice_type:
            return {
                'id': obj.invoice_type.id,
                'display_name_en': obj.invoice_type.display_name_en,
            }
        return None

    def get_payment_method(self, obj):
        if obj.payment_method:
            return {
                'id': obj.payment_method.id,
                'display_name_en': obj.payment_method.display_name_en,
            }
        return None

    
class InvoiceFilter(filters.FilterSet):
    created_at = filters.DateFilter(field_name="created_at", lookup_expr="date")
    start_date = filters.DateFilter(field_name="created_at", lookup_expr='gte')
    end_date = filters.DateFilter(field_name="created_at", lookup_expr='lte')
    warehouse_id = filters.NumberFilter(field_name="warehouse__id")
    
    # Payment status filters
    payment_status = filters.ChoiceFilter(
        choices=[
            ('fully_paid', 'Fully Paid'),
            ('partially_paid', 'Partially Paid'),
            ('unpaid', 'Unpaid'),
            ('has_partial_payments', 'Has Partial Payments')
        ],
        method='filter_payment_status'
    )
    
    # Invoice type filters
    invoice_type = filters.ChoiceFilter(
        choices=[
            ('main', 'Main Invoices'),
            ('sub', 'Sub Invoices'),
            ('all', 'All Invoices')
        ],
        method='filter_invoice_type'
    )
    
    # Search by composite ID
    composite_id = filters.CharFilter(field_name="composite_id", lookup_expr='icontains')
    
    main_invoice_id = filters.NumberFilter(field_name="main_invoice__id")
    customer_id = filters.NumberFilter(field_name="customer__id")
    payment_method_id = filters.NumberFilter(field_name="payment_method__id")

    class Meta:
        model = Invoice
        fields = [
            'created_at', 'start_date', 'end_date', 'warehouse_id',
            'invoice_type', 'payment_status', 'main_invoice_id', 
            'customer_id', 'payment_method_id', 'composite_id'
        ]
    
    def filter_payment_status(self, queryset, name, value):
        # Get all invoices and filter in Python to use the model properties
        all_invoices = queryset.select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related('invoiceitem_set')
        
        filtered_invoices = []
        for invoice in all_invoices:
            if value == 'fully_paid' and invoice.is_fully_paid:
                filtered_invoices.append(invoice.id)
            elif value == 'partially_paid' and invoice.has_partial_payments:
                filtered_invoices.append(invoice.id)
            elif value == 'unpaid' and invoice.total_paid_amount == 0:
                filtered_invoices.append(invoice.id)
            elif value == 'has_partial_payments' and invoice.has_partial_payments:
                filtered_invoices.append(invoice.id)
        
        return queryset.filter(id__in=filtered_invoices)
    
    def filter_invoice_type(self, queryset, name, value):
        if value == 'main':
            return queryset.filter(main_invoice__isnull=True)
        elif value == 'sub':
            return queryset.filter(main_invoice__isnull=False)
        elif value == 'all':
            return queryset
        return queryset

class InvoiceItemSerializer(serializers.ModelSerializer):
    payment_status = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    is_paid = serializers.ReadOnlyField()
    
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        read_only_fields = [
            'created_by', 'updated_by', 'created_at', 'updated_at',
            'item_total_amount', 'item_paid_amount', 'item_remaining_amount'
        ]
    
    def get_payment_status(self, obj):
        return obj.payment_status
    
    def get_payment_status_display(self, obj):
        return obj.payment_status_display
    
    def get_payment_summary(self, obj):
        """Get payment summary in a structured format"""
        return {
            'item_total': float(obj.item_total_amount),
            'item_paid': float(obj.item_paid_amount),
            'item_remaining': float(obj.item_remaining_amount)
        }

class PaymentSerializer(serializers.ModelSerializer):
    payment_type_display = serializers.SerializerMethodField()
    is_partial_payment = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = [
            'created_by', 'updated_by', 'created_at', 'updated_at',
            'invoice_total_amount', 'invoice_paid_amount', 'invoice_remaining_amount'
        ]
    
    def create(self, validated_data):
        # Apply discount if payment amount equals original amount
        invoice = validated_data['invoice']
        payment_amount = validated_data['amount']
        
        # If payment amount equals the original amount, apply the discount
        if payment_amount == invoice.subtotal_amount and invoice.global_discount_percent > 0:
            # Calculate discounted amount
            discount_amount = (invoice.subtotal_amount * invoice.global_discount_percent) / Decimal('100')
            discounted_amount = invoice.subtotal_amount - discount_amount
            validated_data['amount'] = discounted_amount
        
        return super().create(validated_data)
    
    def get_payment_type_display(self, obj):
        return obj.payment_type_display
    
    def get_is_partial_payment(self, obj):
        return obj.is_partial_payment
    
    def get_payment_summary(self, obj):
        """Get payment summary in a structured format"""
        return {
            'invoice_total': float(obj.invoice_total_amount),
            'invoice_paid': float(obj.invoice_paid_amount),
            'invoice_remaining': float(obj.invoice_remaining_amount),
            'payment_amount': float(obj.amount)
        }

class ReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Return
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']


class InvoiceSummarySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.institution_name', allow_null=True, default='No Customer')
    customer_type = serializers.CharField(source='customer.type', allow_null=True, default='N/A')
    warehouse_name = serializers.CharField(source='warehouse.name_ar', allow_null=True, default='No Warehouse')
    invoice_type_name = serializers.CharField(source='invoice_type.display_name_en', allow_null=True, default='No Type')
    payment_method_name = serializers.CharField(source='payment_method.display_name_en', allow_null=True, default='No Payment Method')
    customer_contact = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id',
            'composite_id',
            'customer_name',
            'customer_type',
            'customer_contact',
            'warehouse_name',
            'invoice_type_name',
            'payment_method_name',
            'is_returnable',
            'items',
            'total_amount',
            'total_paid',
            'remaining_amount',
            'global_discount_percent',
            'tax_percent',
            'notes',
            'created_at_formatted',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at'
        ]

    def get_customer_contact(self, obj):
        if not obj.customer:
            return 'No Contact Information'
            
        contact_info = []
        if obj.customer.contact_person:
            contact_info.append(f"Contact: {obj.customer.contact_person}")
        if obj.customer.phone:
            contact_info.append(f"Phone: {obj.customer.phone}")
        if obj.customer.email:
            contact_info.append(f"Email: {obj.customer.email}")
        return "\n".join(contact_info) if contact_info else 'No Contact Information'

    def get_items(self, obj):
        items = []
        for item in obj.invoiceitem_set.all():
            items.append({
                'product_name': getattr(item.product, 'title_ar', 'Unknown') if item.product else 'Unknown',
                'quantity': int(item.quantity),
                'unit_price': float(item.unit_price),
                'discount_percent': float(item.discount_percent),
                'total_price': float(item.total_price),
            })
        return items

    def get_total_amount(self, obj):
        # Original total (before global discount & tax) - the full amount owed
        return float(obj.subtotal_amount)

    def get_total_paid(self, obj):
        # Return the actual payment amount received (after discount)
        # This should be the sum of payment amounts, not the invoice total
        paid = obj.payment_set.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        return float(paid)

    def get_remaining_amount(self, obj):
        # Use the stored payment summary for consistency
        # Get the most recent payment's invoice_remaining_amount
        latest_payment = obj.payment_set.order_by('-created_at').first()
        if latest_payment and latest_payment.invoice_remaining_amount is not None:
            return float(latest_payment.invoice_remaining_amount)
        # Fallback to direct calculation if no payment records exist
        paid = obj.payment_set.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        rem = Decimal(str(obj.total_amount)) - paid
        if rem < 0:
            rem = Decimal('0.00')
        return float(rem)

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
