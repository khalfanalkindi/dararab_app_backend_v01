from rest_framework import generics, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import ProtectedError
from rest_framework.views import APIView
from django.db.models import Sum, Count, Avg, F, Q
from inventory.models import Product
from datetime import datetime

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

class WarehouseDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get('warehouse_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        print("Received params:", warehouse_id, start_date, end_date)

        if not warehouse_id or not start_date or not end_date:
            return Response(
                {"detail": "warehouse_id, start_date, and end_date are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = start_date.strip()
        end_date = end_date.strip()

        try:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            print("Date parsing error:", e)
            return Response(
                {"detail": "start_date and end_date must be in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            warehouse_id=warehouse_id,
            created_at__date__gte=start_date_dt,
            created_at__date__lte=end_date_dt
        )

        total_income = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).aggregate(total=Sum('total_price'))['total'] or 0

        # Calculate total income without discount
        total_income_without_discount = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).aggregate(
            total=Sum(F('unit_price') * F('quantity'))
        )['total'] or 0

        total_books = InvoiceItem.objects.filter(
            invoice__in=invoices
        ).aggregate(total=Sum('quantity'))['total'] or 0

        bills_with_discount = invoices.filter(
            invoiceitem__discount_percent__gt=0
        ).distinct().count()
        total_bills = invoices.count()
        avg_discount = InvoiceItem.objects.filter(
            invoice__in=invoices,
            discount_percent__gt=0
        ).aggregate(avg=Avg('discount_percent'))['avg'] or 0

        popular_books = (
            InvoiceItem.objects.filter(invoice__in=invoices)
            .values('product__title_ar')
            .annotate(total=Sum('quantity'))
            .order_by('-total')[:4]
        )

        # If you have a category field on Product, adjust accordingly
        top_categories = (
            InvoiceItem.objects.filter(invoice__in=invoices)
            .values('product__genre__display_name_en')
            .annotate(total=Sum('quantity'))
            .order_by('-total')[:4]
        )

        daily_sales = (
            InvoiceItem.objects.filter(invoice__in=invoices)
            .values(date=F('invoice__created_at__date'))
            .annotate(
                sales=Sum('quantity'),
                revenue=Sum('total_price')
            )
            .order_by('date')
        )

        return Response({
            "total_income": total_income,
            "total_income_without_discount": total_income_without_discount,
            "total_books_sold": total_books,
            "bills_with_discount": bills_with_discount,
            "total_bills": total_bills,
            "average_discount": avg_discount,
            "popular_books": list(popular_books),
            "top_categories": list(top_categories),
            "daily_sales": list(daily_sales),
        })
