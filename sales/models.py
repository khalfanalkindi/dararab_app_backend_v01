from django.db import models
from django.db.models import Sum
from django.conf import settings
from inventory.models import Product, Warehouse
from common.models import ListItem
from decimal import Decimal


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
    global_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    
    # Composite ID for display and search
    composite_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    
    def save(self, *args, **kwargs):
        # First save to get the ID
        super().save(*args, **kwargs)

        # Generate composite ID if not set (after we have the ID)
        if not self.composite_id:
            if self.main_invoice:
                # ✅ Child invoice: parent_child (e.g., "160_161")
                self.composite_id = f"{self.main_invoice.id}_{self.id}"
            else:
                # ✅ Main invoice: just its own ID
                self.composite_id = str(self.id)
            super().save(update_fields=['composite_id'])

    @property
    def subtotal_amount(self) -> Decimal:
        return sum((item.total_price for item in self.invoiceitem_set.all()), Decimal('0.00'))
        

    @property
    def global_discount_amount(self) -> Decimal:
        return (self.subtotal_amount * (self.global_discount_percent or Decimal('0'))) / Decimal('100')

    @property
    def discounted_subtotal(self) -> Decimal:
        return self.subtotal_amount - self.global_discount_amount

    @property
    def tax_amount(self) -> Decimal:
        return (self.discounted_subtotal * (self.tax_percent or Decimal('0'))) / Decimal('100')

    @property
    def grand_total(self) -> Decimal:
        # Grand total = discounted subtotal + tax
        return (self.discounted_subtotal + self.tax_amount)

    @property
    def total_amount(self) -> Decimal:
        """Grand total after global discount and tax (backwards-compatible name)."""
        return (self.discounted_subtotal + self.tax_amount).quantize(Decimal('0.01'))

    @property
    def total_paid_amount(self) -> Decimal:
        """Sum of per-item paid amounts as stored on items."""
        return sum((item.paid_amount for item in self.invoiceitem_set.all()), Decimal('0.00')).quantize(Decimal('0.01'))

    @property
    def total_remaining_amount(self) -> Decimal:
        """Invoice-level remaining = grand total - sum of item paid."""
        rem = self.total_amount - self.total_paid_amount
        return rem if rem > 0 else Decimal('0.00')

    @property
    def payment_status(self) -> float:
        """Percent paid of the grand total."""
        if self.total_amount == 0:
            return 100.0
        return float((self.total_paid_amount / self.total_amount) * 100)

    @property
    def is_fully_paid(self) -> bool:
        """Treat as fully paid if within 0.001 OMR to tolerate rounding."""
        return (self.total_paid_amount + Decimal('0.001')) >= self.total_amount

    @property
    def has_partial_payments(self) -> bool:
        return self.total_paid_amount > 0 and not self.is_fully_paid

    @property
    def unpaid_items(self):
        return self.invoiceitem_set.filter(is_paid=False)

    @property
    def paid_items(self):
        return self.invoiceitem_set.filter(is_paid=True)
    
    def generate_child_invoice(self, paid_items_only=True):
        """Generate a child invoice from this invoice"""
        # Create new invoice
        child_invoice = Invoice.objects.create(
            customer=self.customer,
            warehouse=self.warehouse,
            invoice_type=self.invoice_type,
            payment_method=self.payment_method,
            is_returnable=self.is_returnable,
            main_invoice=self,  # Set this invoice as parent
            notes=f"Generated from Invoice #{self.id}",
            created_by=self.created_by,
            updated_by=self.updated_by
        )
        
        # Copy items based on selection
        if paid_items_only:
            # Copy only paid items
            items_to_copy = self.paid_items
        else:
            # Copy all items
            items_to_copy = self.invoiceitem_set.all()
        
        for item in items_to_copy:
            InvoiceItem.objects.create(
                invoice=child_invoice,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                total_price=item.total_price,
                paid_amount=item.paid_amount,
                remaining_amount=item.remaining_amount,
                is_paid=item.is_paid,
                created_by=self.created_by,
                updated_by=self.updated_by
            )
        
        return child_invoice

    def recalculate_payment_status(self):
        """Recalculate payment status for all items in this invoice"""
        for item in self.invoiceitem_set.all():
            item.remaining_amount = item.total_price - item.paid_amount
            item.is_paid = item.paid_amount >= item.total_price
            item.save(update_fields=['remaining_amount', 'is_paid'])
        
        # Update payment notes for this invoice
        self.update_payment_notes()
    
    def update_payment_notes(self):
        """Update notes for all payments of this invoice"""
        for payment in self.payment_set.all():
            payment.update_payment_notes()

    def __str__(self):
        composite_id = self.composite_id or str(self.id)
        customer_name = str(self.customer) if self.customer else "No Customer"
        return f"Invoice #{composite_id} - {customer_name}"

# 🧾 Invoice Items
class InvoiceItem(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment tracking fields
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)  # Default: not paid
    
    # Payment summary fields (for consistency with Payment model)
    item_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    item_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    item_remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        # Auto-calculate remaining amount and update paid status
        self.remaining_amount = self.total_price - self.paid_amount
        self.is_paid = self.paid_amount >= self.total_price
        
        # Update payment summary fields
        self.item_total_amount = self.total_price
        self.item_paid_amount = self.paid_amount
        self.item_remaining_amount = self.remaining_amount
        
        super().save(*args, **kwargs)
    
    @property
    def payment_status(self):
        """Get payment status as percentage"""
        if self.total_price == 0:
            return 100
        return (self.paid_amount / self.total_price) * 100
    
    @property
    def payment_status_display(self):
        """Get human-readable payment status"""
        if self.is_paid:
            return "Paid"
        elif self.paid_amount > 0:
            return f"Partially Paid ({self.payment_status:.1f}%)"
        else:
            return "Not Paid"

    def __str__(self):
        product_name = str(self.product) if self.product else "No Product"
        return f"{product_name} x {self.quantity}"

# 💵 Payments
class Payment(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)
    
    # Enhanced payment tracking
    payment_type = models.ForeignKey(ListItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_type')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Payment summary fields (stored as columns, not notes)
    invoice_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Recompute using our summary function
        self.calculate_payment_summary()

        def q2(x):
            if isinstance(x, Decimal):
                return x.quantize(Decimal("0.01"))
            if isinstance(x, (int, float)):
                return Decimal(str(x)).quantize(Decimal("0.01"))
            return Decimal("0.00")

        # IMPORTANT: write the values we just calculated (self.invoice_*_amount), not invoice.* props
        Payment.objects.filter(pk=self.pk).update(
            invoice_total_amount=q2(self.invoice_total_amount),
            invoice_paid_amount=q2(self.invoice_paid_amount),
            invoice_remaining_amount=q2(self.invoice_remaining_amount),
            notes=f"Payment of {float(self.amount):.3f} OMR received on {self.payment_date}"
        )
    # def save(self, *args, **kwargs):
    #     """
    #     Option A (ledger-only):
    #     - Do NOT mutate invoice items here.
    #     - Save the payment row.
    #     - Recompute and persist summary fields from the invoice items.
    #     """
    #     # 1) Save the payment record (ledger)
    #     super().save(*args, **kwargs)

    #     # 2) Recompute summary fields based on current invoice items
    #     self.calculate_payment_summary()

    #     # 3) Persist summary fields WITHOUT calling save() again
    #     def q2(x):
    #         if isinstance(x, Decimal):
    #             return x.quantize(Decimal("0.01"))
    #         if isinstance(x, (int, float)):
    #             return Decimal(str(x)).quantize(Decimal("0.01"))
    #         return Decimal("0.00")

    #     Payment.objects.filter(pk=self.pk).update(
    #         invoice_total_amount=q2(self.invoice_total_amount),
    #         invoice_paid_amount=q2(self.invoice_paid_amount),
    #         invoice_remaining_amount=q2(self.invoice_remaining_amount),
    #         notes=f"Payment of {float(self.amount):.3f} OMR received on {self.payment_date}"
    #     )
    
    def distribute_payment_to_items(self):
        """Distribute payment amount to unpaid items"""
        """
        DEPRECATED in Option A flow.
        Kept for legacy/manual use but NOT called from save().
        """
        return
        # # Get all items that still have remaining amounts to pay
        # invoice_items = self.invoice.invoiceitem_set.filter(remaining_amount__gt=0).order_by('id')
        # remaining_payment = self.amount
        
        # for item in invoice_items:
        #     if remaining_payment <= 0:
        #         break
                
        #     # Calculate how much to pay for this item
        #     payment_for_item = min(remaining_payment, item.remaining_amount)
        #     item.paid_amount += payment_for_item
        #     item.save()  # This will auto-update remaining_amount and is_paid
            
        #     remaining_payment -= payment_for_item
        
        # # Update payment summary fields
        # self.calculate_payment_summary()
    
    def calculate_payment_summary(self):
        """
        For the Payments *ledger*:
        - invoice_total_amount = original total (before global discount & tax) - the full amount owed
        - invoice_paid_amount  = sum of ALL payment amounts recorded for this invoice (actual money received)
        - invoice_remaining_amount = original total - money received
        """
        inv = self.invoice

        # Original total: before global discount and tax (the full amount owed)
        original_total = inv.subtotal_amount  # This is the gross total before discount

        # Money received: sum of all payments (ledger truth)
        paid = inv.payment_set.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        remaining = original_total - paid
        if remaining < 0:
            remaining = Decimal('0.00')

        # Store on the instance so save() can write them
        self.invoice_total_amount = original_total
        self.invoice_paid_amount = paid
        self.invoice_remaining_amount = remaining
    
    # def calculate_payment_summary(self):
    #     """Calculate and store payment summary as columns"""
    #     invoice = self.invoice
        
    #     # Get current invoice amounts
    #     self.invoice_total_amount = invoice.total_amount
    #     self.invoice_paid_amount = invoice.total_paid_amount
    #     self.invoice_remaining_amount = invoice.total_remaining_amount
        
    
    def update_payment_notes(self):
        """Update payment notes to reflect current payment status"""
        # Create a simple note without duplicating data that's now in columns
        self.notes = f"Payment of {self.amount:.3f} OMR received on {self.payment_date}"
    
    @property
    def payment_type_display(self):
        """Get payment type display name"""
        return self.payment_type.display_name_en if self.payment_type else "Cash"
    
    @property
    def is_partial_payment(self):
        """Check if this is a partial payment"""
        return self.amount < self.invoice.total_remaining_amount

    def __str__(self):
        invoice_id = self.invoice.composite_id if self.invoice and self.invoice.composite_id else "Unknown"
        return f"{self.amount} for Invoice #{invoice_id}"

# 🔄 Returns
class Return(AuditModel):
    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE)
    returned_quantity = models.IntegerField()
    return_date = models.DateField()

    def __str__(self):
        item_str = str(self.invoice_item) if self.invoice_item else "Unknown Item"
        return f"Returned {self.returned_quantity} of {item_str}"