from rest_framework import serializers
from django_filters import rest_framework as filters

from common.models import ListItem
from inventory.models import Warehouse
from .models import Customer, Invoice, InvoiceItem, Payment, Return

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class InvoiceSerializer(serializers.ModelSerializer):
    invoice_number = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
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

    class Meta:
        model = Invoice
        fields = '__all__'
    
    def get_invoice_number(self, obj):
        return obj.id

    def get_total_amount(self, obj):
        return sum(item.total_price for item in obj.invoiceitem_set.all())

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

    class Meta:
        model = Invoice
        fields = ['created_at', 'start_date', 'end_date', 'warehouse_id']

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

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
                'product_name': item.product.title_ar,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'discount_percent': item.discount_percent,
                'total_price': item.total_price
            })
        return items

    def get_total_amount(self, obj):
        return sum(item.total_price for item in obj.invoiceitem_set.all())

    def get_total_paid(self, obj):
        return sum(payment.amount for payment in obj.payment_set.all())

    def get_remaining_amount(self, obj):
        return self.get_total_amount(obj) - self.get_total_paid(obj)

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
