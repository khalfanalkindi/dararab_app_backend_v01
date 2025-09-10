from django.urls import path
from . import views

urlpatterns = [

    # Customers
    path("customers/", views.CustomerListCreateView.as_view(), name="customer-list-create"),
    path("customers/<int:pk>/", views.CustomerUpdateView.as_view(), name="customer-update"),
    path("customers/<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer-delete"),

    # Invoices
    path("invoices/", views.InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("invoices/<int:pk>/", views.InvoiceUpdateView.as_view(), name="invoice-update"),
    path("invoices/<int:pk>/delete/", views.InvoiceDeleteView.as_view(), name="invoice-delete"),

    # Invoice Items
    path("invoice-items/", views.InvoiceItemListCreateView.as_view(), name="invoice-item-list-create"),
    path("invoice-items/<int:pk>/", views.InvoiceItemUpdateView.as_view(), name="invoice-item-update"),
    path("invoice-items/<int:pk>/delete/", views.InvoiceItemDeleteView.as_view(), name="invoice-item-delete"),

    # Payments
    path("payments/", views.PaymentListCreateView.as_view(), name="payment-list-create"),
    path("payments/<int:pk>/", views.PaymentUpdateView.as_view(), name="payment-update"),
    path("payments/<int:pk>/delete/", views.PaymentDeleteView.as_view(), name="payment-delete"),

    # Returns
    path("returns/", views.ReturnListCreateView.as_view(), name="return-list-create"),
    path("returns/<int:pk>/", views.ReturnUpdateView.as_view(), name="return-update"),
    path("returns/<int:pk>/delete/", views.ReturnDeleteView.as_view(), name="return-delete"),

    path('invoices/<int:pk>/summary/', views.InvoiceSummaryView.as_view(), name='invoice-summary'),

    path('warehouse-dashboard/', views.WarehouseDashboardView.as_view(), name='warehouse-dashboard'),

    # New invoice filtering endpoints
    path("invoices/main/", views.MainInvoiceListView.as_view(), name="main-invoice-list"),
    path("invoices/sub/", views.SubInvoiceListView.as_view(), name="sub-invoice-list"),
    path("invoices/<int:main_invoice_id>/children/", views.InvoiceChildrenView.as_view(), name="invoice-children"),
    path("invoices/<int:invoice_id>/items/", views.InvoiceItemsView.as_view(), name="invoice-items"),
    
    # Partial payment endpoints
    path("invoices/partial-payments/", views.PartialPaymentInvoiceListView.as_view(), name="partial-payment-invoices"),
    path("invoices/outstanding-payments/", views.OutstandingPaymentInvoiceListView.as_view(), name="outstanding-payment-invoices"),
    path("invoices/<int:parent_invoice_id>/generate-child/", views.GenerateChildInvoiceView.as_view(), name="generate-child-invoice"),
    path("invoices/<int:pk>/payment-status/", views.InvoicePaymentStatusView.as_view(), name="invoice-payment-status"),
    
    # Debug endpoint
    path("invoices/debug/payments/", views.InvoicePaymentDebugView.as_view(), name="invoice-payment-debug"),
    path("invoices/debug/payment-distribution/", views.PaymentDistributionDebugView.as_view(), name="payment-distribution-debug"),
    path("invoices/debug/<int:invoice_id>/", views.InvoiceDetailDebugView.as_view(), name="invoice-detail-debug"),

]