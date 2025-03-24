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
