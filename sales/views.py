from rest_framework import generics, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import ProtectedError

from .models import Customer, Invoice, InvoiceItem, Payment, Return
from .serializers import (
    CustomerSerializer, InvoiceFilter, InvoiceSerializer, InvoiceItemSerializer, InvoiceSummarySerializer,
    PaymentSerializer, ReturnSerializer
)

# Shared delete view
class BaseDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response({"error": "Cannot delete due to related data."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ======== Customers ========
class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class CustomerUpdateView(generics.UpdateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class CustomerDeleteView(BaseDeleteView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

# ======== Invoices ========



class InvoiceListCreateView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['id', 'customer__institution_name', 'customer__contact_person']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class InvoiceUpdateView(generics.UpdateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InvoiceDeleteView(BaseDeleteView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

# ======== Invoice Items ========
class InvoiceItemListCreateView(generics.ListCreateAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class InvoiceItemUpdateView(generics.UpdateAPIView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InvoiceItemDeleteView(BaseDeleteView):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer

# ======== Payments ========
class PaymentListCreateView(generics.ListCreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class PaymentUpdateView(generics.UpdateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class PaymentDeleteView(BaseDeleteView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

# ======== Returns ========
class ReturnListCreateView(generics.ListCreateAPIView):
    queryset = Return.objects.all()
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ReturnUpdateView(generics.UpdateAPIView):
    queryset = Return.objects.all()
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ReturnDeleteView(BaseDeleteView):
    queryset = Return.objects.all()
    serializer_class = ReturnSerializer

class InvoiceSummaryView(generics.RetrieveAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().select_related(
            'customer',
            'customer__type',
            'warehouse',
            'invoice_type',
            'payment_method',
            'created_by',
            'updated_by'
        ).prefetch_related(
            'invoiceitem_set',
            'invoiceitem_set__product',
            'payment_set'
        )
