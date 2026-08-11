from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import ListItem, ListType
from inventory.models import Inventory, Product, Transfer, Warehouse
from sales.models import Customer, Invoice, InvoiceItem, Return
from sales.services.book_analytics import BookAnalyticsFilters, BookAnalyticsService
from users.models import CustomUser


class BookAnalyticsServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="analyst",
            email="analyst@example.com",
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
        self.other_warehouse = Warehouse.objects.create(
            name_en="Dubai WH",
            name_ar="دبي",
            location="Dubai",
        )
        self.customer = Customer.objects.create(
            institution_name="Bookshop A",
            customer_type=self.customer_type,
        )
        self.product = Product.objects.create(
            isbn="978-1",
            title_ar="كتاب",
            title_en="Book One",
            price=Decimal("10.00"),
            is_direct_product=True,
        )
        Inventory.objects.create(product=self.product, warehouse=self.warehouse, quantity=40)

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

    def _item(self, invoice, *, qty=2, unit=Decimal("10.00"), discount=Decimal("0"), paid=None, total=None):
        gross = unit * qty
        line_total = total if total is not None else (gross * (Decimal("100") - discount) / Decimal("100"))
        paid_amount = paid if paid is not None else line_total
        return InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=qty,
            unit_price=unit,
            discount_percent=discount,
            total_price=line_total,
            paid_amount=paid_amount,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_summary_excludes_tax_and_counts_paid_unpaid(self):
        inv = self._invoice(tax_percent=Decimal("5.00"))
        self._item(inv, qty=4, unit=Decimal("10.00"), discount=Decimal("10"), paid=Decimal("18.00"))
        # gross 40, net 36, paid 18 → 2 paid copies, 2 unpaid

        payload = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()
        summary = payload["summary"]

        self.assertEqual(summary["copies_invoiced"], 4)
        self.assertEqual(summary["copies_paid"], 2)
        self.assertEqual(summary["copies_unpaid"], 2)
        self.assertEqual(summary["gross_value"], 40.0)
        self.assertEqual(summary["discount_value"], 4.0)
        self.assertEqual(summary["net_revenue"], 36.0)
        self.assertEqual(summary["amount_received"], 18.0)
        self.assertEqual(payload["currency"], "$")

    def test_complimentary_zero_revenue(self):
        inv = self._invoice()
        self._item(inv, qty=3, unit=Decimal("10.00"), discount=Decimal("100"), paid=Decimal("0"), total=Decimal("0"))

        summary = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()["summary"]
        self.assertEqual(summary["copies_complimentary"], 3)
        self.assertEqual(summary["copies_net_sold"], 0)
        self.assertEqual(summary["net_revenue"], 0.0)
        self.assertEqual(summary["gross_value"], 0.0)

    def test_returns_reduce_net_units_and_revenue(self):
        inv = self._invoice()
        item = self._item(inv, qty=10, unit=Decimal("10.00"), discount=Decimal("0"), paid=Decimal("100"))
        Return.objects.create(invoice_item=item, returned_quantity=4, return_date=date.today())

        summary = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()["summary"]
        self.assertEqual(summary["copies_returned"], 4)
        self.assertEqual(summary["copies_net_sold"], 6)
        self.assertEqual(summary["returned_revenue"], 40.0)
        self.assertEqual(summary["net_revenue"], 60.0)

    def test_child_invoice_excluded_to_avoid_double_count(self):
        parent = self._invoice()
        self._item(parent, qty=5, unit=Decimal("10.00"))
        child = self._invoice(main_invoice=parent, notes="child copy")
        self._item(child, qty=5, unit=Decimal("10.00"))

        summary = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()["summary"]
        self.assertEqual(summary["copies_invoiced"], 5)
        self.assertEqual(summary["net_revenue"], 50.0)

    def test_transfers_never_count_as_sales(self):
        inv = self._invoice()
        self._item(inv, qty=2, unit=Decimal("10.00"))
        Transfer.objects.create(
            product=self.product,
            from_warehouse=self.warehouse,
            to_warehouse=self.other_warehouse,
            quantity=7,
            shipping_cost=Decimal("0"),
            transfer_date=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
        )

        payload = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()
        self.assertEqual(payload["summary"]["copies_invoiced"], 2)
        self.assertEqual(payload["summary"]["net_revenue"], 20.0)
        types = {row["transaction_type"] for row in payload["transactions"]["results"]}
        self.assertIn("transfer", types)
        self.assertIn("sale", types)

    def test_warehouse_stock_included(self):
        by_wh = BookAnalyticsService(self.product.id, BookAnalyticsFilters()).build()["by_warehouse"]
        muscat = next(row for row in by_wh if row["warehouse_id"] == self.warehouse.id)
        self.assertEqual(muscat["current_stock"], 40)


class BookAnalyticsAPITests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="apiuser",
            email="api@example.com",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            isbn="978-2",
            title_ar="كتاب ٢",
            title_en="Book Two",
            price=Decimal("12.00"),
            is_direct_product=True,
        )
        self.warehouse = Warehouse.objects.create(
            name_en="WH", name_ar="م", location="Muscat"
        )
        self.customer = Customer.objects.create(institution_name="C1")
        inv = Invoice.objects.create(
            customer=self.customer,
            warehouse=self.warehouse,
            created_by=self.user,
            updated_by=self.user,
        )
        InvoiceItem.objects.create(
            invoice=inv,
            product=self.product,
            quantity=1,
            unit_price=Decimal("12.00"),
            discount_percent=Decimal("0"),
            total_price=Decimal("12.00"),
            paid_amount=Decimal("12.00"),
            created_by=self.user,
            updated_by=self.user,
        )

    def test_endpoint_returns_payload(self):
        res = self.client.get(f"/api/sales/products/{self.product.id}/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["product"]["id"], self.product.id)
        self.assertEqual(res.data["summary"]["copies_invoiced"], 1)

    def test_endpoint_404_for_missing_product(self):
        res = self.client.get("/api/sales/products/999999/analytics/")
        self.assertEqual(res.status_code, 404)

    def test_bad_payment_status(self):
        res = self.client.get(
            f"/api/sales/products/{self.product.id}/analytics/",
            {"payment_status": "nope"},
        )
        self.assertEqual(res.status_code, 400)
