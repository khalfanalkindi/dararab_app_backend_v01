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
    queryset = Customer.objects.all().order_by('id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class CustomerUpdateView(generics.UpdateAPIView):
    queryset = Customer.objects.all().order_by('id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class CustomerDeleteView(BaseDeleteView):
    queryset = Customer.objects.all().order_by('id')
    serializer_class = CustomerSerializer

# ======== Invoices ========



class InvoiceListCreateView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-created_at', 'id')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['id', 'customer__institution_name', 'customer__contact_person']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Get display type from query params
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class MainInvoiceListView(generics.ListAPIView):
    """Get only main invoices (invoices without main_invoice)"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['composite_id', 'customer__institution_name', 'customer__contact_person']
    
    def get_queryset(self):
        return Invoice.objects.filter(main_invoice__isnull=True).select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).order_by('-created_at', 'id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class SubInvoiceListView(generics.ListAPIView):
    """Get only sub-invoices (invoices with main_invoice)"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['composite_id', 'customer__institution_name', 'customer__contact_person']
    
    def get_queryset(self):
        return Invoice.objects.filter(main_invoice__isnull=False).select_related(
            'main_invoice', 'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).order_by('-created_at', 'id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class InvoiceUpdateView(generics.UpdateAPIView):
    queryset = Invoice.objects.all().order_by('id')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InvoiceDeleteView(BaseDeleteView):
    queryset = Invoice.objects.all().order_by('id')
    serializer_class = InvoiceSerializer

# ======== Invoice Items ========
class InvoiceItemListCreateView(generics.ListCreateAPIView):
    queryset = InvoiceItem.objects.all().order_by('-created_at', 'id')
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class InvoiceItemUpdateView(generics.UpdateAPIView):
    queryset = InvoiceItem.objects.all().order_by('id')
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class InvoiceItemDeleteView(BaseDeleteView):
    queryset = InvoiceItem.objects.all().order_by('id')
    serializer_class = InvoiceItemSerializer

# ======== Payments ========
class PaymentListCreateView(generics.ListCreateAPIView):
    queryset = Payment.objects.all().order_by('-payment_date', 'id')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class PaymentUpdateView(generics.UpdateAPIView):
    queryset = Payment.objects.all().order_by('id')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class PaymentDeleteView(BaseDeleteView):
    queryset = Payment.objects.all().order_by('id')
    serializer_class = PaymentSerializer

# ======== Returns ========
class ReturnListCreateView(generics.ListCreateAPIView):
    queryset = Return.objects.all().order_by('-return_date', 'id')
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class ReturnUpdateView(generics.UpdateAPIView):
    queryset = Return.objects.all().order_by('id')
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ReturnDeleteView(BaseDeleteView):
    queryset = Return.objects.all().order_by('id')
    serializer_class = ReturnSerializer

class InvoiceSummaryView(generics.RetrieveAPIView):
    queryset = Invoice.objects.all().order_by('id')
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
        ).order_by('-created_at', 'id')

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

class InvoiceChildrenView(generics.ListAPIView):
    """Get all sub-invoices for a specific main invoice"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        main_invoice_id = self.kwargs.get('main_invoice_id')
        return Invoice.objects.filter(main_invoice_id=main_invoice_id).select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).order_by('-created_at', 'id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class InvoiceItemsView(generics.ListAPIView):
    """Get all items for a specific invoice"""
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        invoice_id = self.kwargs.get('invoice_id')
        return InvoiceItem.objects.filter(invoice_id=invoice_id).select_related(
            'invoice', 'product'
        ).order_by('id')

class PartialPaymentInvoiceListView(generics.ListAPIView):
    """Get invoices with partial payments"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['composite_id', 'customer__institution_name', 'customer__contact_person']
    
    def get_queryset(self):
        # Get all invoices and filter in Python to use the model properties
        all_invoices = Invoice.objects.select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related('invoiceitem_set').order_by('-created_at', 'id')
        
        # Filter invoices that have partial payments
        partial_payment_invoices = []
        for invoice in all_invoices:
            if invoice.has_partial_payments:
                partial_payment_invoices.append(invoice.id)
        
        # Return filtered queryset
        return Invoice.objects.filter(id__in=partial_payment_invoices).select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related('invoiceitem_set').order_by('-created_at', 'id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class OutstandingPaymentInvoiceListView(generics.ListAPIView):
    """Get invoices with outstanding payments (unpaid or partially paid)"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['composite_id', 'customer__institution_name', 'customer__contact_person']
    
    def get_queryset(self):
        # Get all invoices and filter in Python to use the model properties
        all_invoices = Invoice.objects.select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related('invoiceitem_set').order_by('-created_at', 'id')
        
        # Filter invoices that have outstanding payments (not fully paid)
        outstanding_invoices = []
        for invoice in all_invoices:
            if not invoice.is_fully_paid:
                outstanding_invoices.append(invoice.id)
        
        # Return filtered queryset
        return Invoice.objects.filter(id__in=outstanding_invoices).select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related('invoiceitem_set').order_by('-created_at', 'id')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        display_type = self.request.query_params.get('display_type', 'composite')
        context['display_type'] = display_type
        return context

class GenerateChildInvoiceView(generics.CreateAPIView):
    """Generate a child invoice from a parent invoice"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        parent_invoice_id = self.kwargs.get('parent_invoice_id')
        paid_items_only = request.data.get('paid_items_only', True)
        
        try:
            parent_invoice = Invoice.objects.get(id=parent_invoice_id)
            child_invoice = parent_invoice.generate_child_invoice(paid_items_only=paid_items_only)
            
            serializer = self.get_serializer(child_invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Invoice.DoesNotExist:
            return Response(
                {"error": "Parent invoice not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class InvoicePaymentStatusView(generics.RetrieveAPIView):
    """Get detailed payment status for an invoice"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Invoice.objects.select_related(
            'customer', 'warehouse', 'invoice_type', 'payment_method'
        ).prefetch_related(
            'invoiceitem_set',
            'invoiceitem_set__product',
            'payment_set'
        ).order_by('-created_at', 'id')

class InvoicePaymentDebugView(APIView):
    """Debug view to show payment status of all invoices"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        invoices = Invoice.objects.select_related('customer').prefetch_related('invoiceitem_set').all()
        
        debug_data = []
        for invoice in invoices:
            debug_data.append({
                'id': invoice.id,
                'composite_id': invoice.composite_id,
                'customer': invoice.customer.institution_name if invoice.customer else 'No Customer',
                'total_amount': float(invoice.total_amount),
                'total_paid_amount': float(invoice.total_paid_amount),
                'total_remaining_amount': float(invoice.total_remaining_amount),
                'is_fully_paid': invoice.is_fully_paid,
                'has_partial_payments': invoice.has_partial_payments,
                'payment_status_percentage': invoice.payment_status,
                'items_count': invoice.invoiceitem_set.count(),
                'items_detail': [
                    {
                        'id': item.id,
                        'product': item.product.title_ar if item.product else 'No Product',
                        'total_price': float(item.total_price),
                        'paid_amount': float(item.paid_amount),
                        'remaining_amount': float(item.remaining_amount),
                        'is_paid': item.is_paid
                    }
                    for item in invoice.invoiceitem_set.all()
                ]
            })
        
        return Response({
            'total_invoices': len(debug_data),
            'invoices': debug_data
        })

class PaymentDistributionDebugView(APIView):
    """Debug view to check payment distribution and fix any issues"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all payments
        payments = Payment.objects.select_related('invoice').all()
        
        # Get all invoice items
        invoice_items = InvoiceItem.objects.select_related('invoice', 'product').all()
        
        # Check for any inconsistencies
        issues = []
        fixed_count = 0
        
        for item in invoice_items:
            # Calculate what the values should be
            expected_remaining = item.total_price - item.paid_amount
            expected_is_paid = item.paid_amount >= item.total_price
            
            # Check if there are inconsistencies
            if item.remaining_amount != expected_remaining or item.is_paid != expected_is_paid:
                issues.append({
                    'item_id': item.id,
                    'invoice_id': item.invoice.id,
                    'product': item.product.title_ar if item.product else 'No Product',
                    'total_price': float(item.total_price),
                    'paid_amount': float(item.paid_amount),
                    'current_remaining': float(item.remaining_amount),
                    'expected_remaining': float(expected_remaining),
                    'current_is_paid': item.is_paid,
                    'expected_is_paid': expected_is_paid
                })
                
                # Fix the issue
                item.remaining_amount = expected_remaining
                item.is_paid = expected_is_paid
                item.save(update_fields=['remaining_amount', 'is_paid'])
                fixed_count += 1
        
        return Response({
            'total_payments': payments.count(),
            'total_invoice_items': invoice_items.count(),
            'issues_found': len(issues),
            'issues_fixed': fixed_count,
            'issues_detail': issues,
            'payments_summary': [
                {
                    'id': payment.id,
                    'invoice_id': payment.invoice.id,
                    'amount': float(payment.amount),
                    'payment_date': payment.payment_date,
                    'payment_type': payment.payment_type_display
                }
                for payment in payments
            ]
        })
    
    def post(self, request):
        """Manually redistribute all payments to fix any issues"""
        payments = Payment.objects.select_related('invoice').all()
        redistributed_count = 0
        
        for payment in payments:
            # Reset all invoice items for this invoice
            invoice_items = payment.invoice.invoiceitem_set.all()
            for item in invoice_items:
                item.paid_amount = 0
                item.remaining_amount = item.total_price
                item.is_paid = False
                item.save(update_fields=['paid_amount', 'remaining_amount', 'is_paid'])
            
            # Redistribute the payment
            payment.distribute_payment_to_items()
            redistributed_count += 1
        
        return Response({
            'message': f'Redistributed {redistributed_count} payments',
            'redistributed_count': redistributed_count
        })

class InvoiceDetailDebugView(APIView):
    """Debug view to check specific invoice details"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, invoice_id):
        try:
            invoice = Invoice.objects.select_related(
                'customer', 'warehouse', 'invoice_type', 'payment_method'
            ).prefetch_related(
                'invoiceitem_set',
                'invoiceitem_set__product',
                'payment_set'
            ).get(id=invoice_id)
            
            # Get all payments for this invoice
            payments = invoice.payment_set.all()
            
            # Get all items for this invoice
            items = invoice.invoiceitem_set.all()
            
            debug_data = {
                'invoice_id': invoice.id,
                'composite_id': invoice.composite_id,
                'customer': invoice.customer.institution_name if invoice.customer else 'No Customer',
                'payment_method': {
                    'id': invoice.payment_method.id if invoice.payment_method else None,
                    'name': invoice.payment_method.display_name_en if invoice.payment_method else None,
                    'value': invoice.payment_method.value if invoice.payment_method else None,
                },
                'total_amount': float(invoice.total_amount),
                'total_paid_amount': float(invoice.total_paid_amount),
                'total_remaining_amount': float(invoice.total_remaining_amount),
                'payment_status_percentage': invoice.payment_status,
                'is_fully_paid': invoice.is_fully_paid,
                'has_partial_payments': invoice.has_partial_payments,
                'payments': [
                    {
                        'id': payment.id,
                        'amount': float(payment.amount),
                        'payment_date': payment.payment_date,
                        'payment_type': payment.payment_type_display,
                        'reference_number': payment.reference_number,
                        'notes': payment.notes
                    }
                    for payment in payments
                ],
                'items': [
                    {
                        'id': item.id,
                        'product': item.product.title_ar if item.product else 'No Product',
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price),
                        'discount_percent': float(item.discount_percent),
                        'total_price': float(item.total_price),
                        'paid_amount': float(item.paid_amount),
                        'remaining_amount': float(item.remaining_amount),
                        'is_paid': item.is_paid,
                        'payment_status': item.payment_status
                    }
                    for item in items
                ]
            }
            
            return Response(debug_data)
            
        except Invoice.DoesNotExist:
            return Response(
                {"error": f"Invoice with ID {invoice_id} not found"}, 
                status=404
            )
