from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from common.models import ListItem, ListType
from inventory.models import Product, Warehouse
from sales.models import Customer, Invoice, InvoiceItem, Payment
from sales.services.settle_invoice import SettleInvoiceError, settle_invoice
from users.models import CustomUser


class SettleInvoiceServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="settler",
            email="settler@example.com",
            password="pass12345",
        )
        customer_type_list = ListType.objects.create(
            name_en="Customer Type", name_ar="نوع العميل", code="customer_type"
        )
        invoice_type_list = ListType.objects.create(
            name_en="Invoice Type", name_ar="نوع الفاتورة", code="invoice_type"
        )
        self.customer_type = ListItem.objects.create(
            list_type=customer_type_list,
            value="store",
            display_name_en="Store",
            display_name_ar="مكتبة",
        )
        self.invoice_type = ListItem.objects.create(
            list_type=invoice_type_list,
            value="mainstore",
            display_name_en="Main Store",
            display_name_ar="المستودع الرئيسي",
        )
        self.warehouse = Warehouse.objects.create(
            name_en="Muscat WH",
            name_ar="مسقط",
            location="Muscat",
        )
        self.customer = Customer.objects.create(
            institution_name="Bookshop A",
            customer_type=self.customer_type,
        )
        self.product = Product.objects.create(
            isbn="978-settle-1",
            title_ar="كتاب تسوية",
            title_en="Settle Book",
            price=Decimal("10.00"),
            is_direct_product=True,
        )
        self.product_b = Product.objects.create(
            isbn="978-settle-2",
            title_ar="كتاب آخر",
            title_en="Other Book",
            price=Decimal("5.00"),
            is_direct_product=True,
        )

    def _invoice(self, **kwargs):
        defaults = dict(
            customer=self.customer,
            warehouse=self.warehouse,
            invoice_type=self.invoice_type,
            created_by=self.user,
            updated_by=self.user,
        )
        defaults.update(kwargs)
        return Invoice.objects.create(**defaults)

    def _item(self, invoice, *, product=None, qty=2, unit=Decimal("10.00"), discount=Decimal("0"), paid=Decimal("0")):
        product = product or self.product
        gross = unit * qty
        line_total = (gross * (Decimal("100") - discount) / Decimal("100")).quantize(Decimal("0.01"))
        return InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=qty,
            unit_price=unit,
            discount_percent=discount,
            total_price=line_total,
            paid_amount=paid,
        )

    def test_settle_creates_paid_child_and_marks_parent_paid(self):
        parent = self._invoice()
        unpaid = self._item(parent, qty=2, unit=Decimal("10.00"), paid=Decimal("0"))
        discounted = self._item(
            parent,
            product=self.product_b,
            qty=1,
            unit=Decimal("5.00"),
            discount=Decimal("20"),
            paid=Decimal("0"),
        )
        # Already paid line must not move to child
        self._item(parent, qty=1, unit=Decimal("3.00"), paid=Decimal("3.00"))

        result = settle_invoice(invoice_id=parent.id, user=self.user)

        parent.refresh_from_db()
        unpaid.refresh_from_db()
        discounted.refresh_from_db()

        self.assertEqual(result["settled_item_count"], 2)
        self.assertEqual(Decimal(str(result["settled_amount"])), Decimal("24.00"))
        self.assertTrue(unpaid.is_paid)
        self.assertEqual(unpaid.paid_amount, unpaid.total_price)
        self.assertTrue(discounted.is_paid)

        child = Invoice.objects.get(pk=result["child_invoice_id"])
        self.assertEqual(child.main_invoice_id, parent.id)
        self.assertEqual(child.global_discount_percent, Decimal("0.00"))
        self.assertEqual(child.customer_id, parent.customer_id)
        self.assertEqual(child.warehouse_id, parent.warehouse_id)

        child_items = list(child.invoiceitem_set.order_by("id"))
        self.assertEqual(len(child_items), 2)
        self.assertTrue(all(item.is_paid for item in child_items))
        self.assertEqual(
            sum((item.total_price for item in child_items), Decimal("0")),
            Decimal("24.00"),
        )

        payment = Payment.objects.get(pk=result["payment_id"])
        self.assertEqual(payment.invoice_id, child.id)
        self.assertEqual(payment.amount, Decimal("24.00"))
        self.assertTrue(parent.is_fully_paid)

    def test_settle_rejects_fully_paid_invoice(self):
        parent = self._invoice()
        self._item(parent, qty=1, unit=Decimal("10.00"), paid=Decimal("10.00"))
        with self.assertRaises(SettleInvoiceError):
            settle_invoice(invoice_id=parent.id, user=self.user)

    def test_settle_rejects_missing_invoice(self):
        with self.assertRaises(SettleInvoiceError) as ctx:
            settle_invoice(invoice_id=999999, user=self.user)
        self.assertEqual(ctx.exception.status_code, 404)


class SettleInvoiceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username="settleapi",
            email="settleapi@example.com",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

        customer_type_list = ListType.objects.create(
            name_en="Customer Type", name_ar="نوع العميل", code="customer_type"
        )
        invoice_type_list = ListType.objects.create(
            name_en="Invoice Type", name_ar="نوع الفاتورة", code="invoice_type"
        )
        customer_type = ListItem.objects.create(
            list_type=customer_type_list,
            value="store",
            display_name_en="Store",
            display_name_ar="مكتبة",
        )
        invoice_type = ListItem.objects.create(
            list_type=invoice_type_list,
            value="mainstore",
            display_name_en="Main Store",
            display_name_ar="المستودع الرئيسي",
        )
        self.warehouse = Warehouse.objects.create(
            name_en="WH",
            name_ar="مستودع",
            location="Muscat",
        )
        self.customer = Customer.objects.create(
            institution_name="Shop",
            customer_type=customer_type,
        )
        self.product = Product.objects.create(
            isbn="978-api-settle",
            title_ar="كتاب",
            title_en="Book",
            price=Decimal("8.00"),
            is_direct_product=True,
        )
        self.parent = Invoice.objects.create(
            customer=self.customer,
            warehouse=self.warehouse,
            invoice_type=invoice_type,
            created_by=self.user,
            updated_by=self.user,
        )
        InvoiceItem.objects.create(
            invoice=self.parent,
            product=self.product,
            quantity=2,
            unit_price=Decimal("8.00"),
            discount_percent=Decimal("0"),
            total_price=Decimal("16.00"),
            paid_amount=Decimal("0"),
        )

    def test_settle_endpoint(self):
        url = f"/api/sales/invoices/{self.parent.id}/settle/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["settlement"]["settled_item_count"], 1)
        self.assertEqual(body["settlement"]["parent_invoice_id"], self.parent.id)
        self.assertIn("child_invoice", body)
        self.assertEqual(body["child_invoice"]["id"], body["settlement"]["child_invoice_id"])
