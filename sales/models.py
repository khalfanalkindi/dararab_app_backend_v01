from django.db import models
from django.conf import settings
from inventory.models import Product, Warehouse
from common.models import ListItem

# 🔁 Mixin for audit fields
class AuditModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="%(class)s_created_by"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="%(class)s_updated_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# 👤 Customer
class Customer(AuditModel):
    type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name="customer_type")
    institution_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.institution_name

# 🧾 Invoice
class Invoice(AuditModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    invoice_type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='invoice_type')
    payment_method = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, related_name='payment_method')
    is_returnable = models.BooleanField(default=True)
    main_invoice = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer}"

# 🧾 Invoice Items
class InvoiceItem(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product} x {self.quantity}"

# 💵 Payments
class Payment(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.amount} for Invoice #{self.invoice.id}"

# 🔄 Returns
class Return(AuditModel):
    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE)
    returned_quantity = models.IntegerField()
    return_date = models.DateField()

    def __str__(self):
        return f"Returned {self.returned_quantity} of {self.invoice_item}"
