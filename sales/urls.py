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

]
