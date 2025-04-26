from rest_framework import serializers
from .models import Customer, Invoice, InvoiceItem, Payment, Return

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

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
    customer_name = serializers.CharField(source='customer.institution_name')
    customer_type = serializers.CharField(source='customer.type')
    customer_contact = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(source='warehouse.name_ar')
    invoice_type_name = serializers.CharField(source='invoice_type.display_name_en')
    payment_method_name = serializers.CharField(source='payment_method.display_name_en')
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
        contact_info = []
        if obj.customer.contact_person:
            contact_info.append(f"Contact: {obj.customer.contact_person}")
        if obj.customer.phone:
            contact_info.append(f"Phone: {obj.customer.phone}")
        if obj.customer.email:
            contact_info.append(f"Email: {obj.customer.email}")
        return "\n".join(contact_info) if contact_info else None

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
