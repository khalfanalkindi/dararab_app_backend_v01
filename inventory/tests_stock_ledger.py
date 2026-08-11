from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from inventory.models import Inventory, Product, StockMovement, Warehouse
from inventory.services.stock_ledger import (
    apply_delta,
    opening_closing_stock,
    set_absolute_quantity,
)
from users.models import CustomUser


class StockLedgerHelperTests(SimpleTestCase):
    def test_opening_closing_math_without_db(self):
        # Pure function contract when no rows: opening 0, closing 0
        result = opening_closing_stock(product_id=999999)
        self.assertEqual(result["opening_stock"], 0)
        self.assertEqual(result["closing_stock"], 0)


class StockLedgerServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="stockuser",
            email="stock@example.com",
            password="pass12345",
        )
        self.product = Product.objects.create(
            isbn="978-stock",
            title_ar="مخزون",
            title_en="Stock Book",
            price=Decimal("5.00"),
            is_direct_product=True,
        )
        self.wh_a = Warehouse.objects.create(name_en="A", name_ar="أ", location="Muscat")
        self.wh_b = Warehouse.objects.create(name_en="B", name_ar="ب", location="Dubai")
        Inventory.objects.create(product=self.product, warehouse=self.wh_a, quantity=100)

    def test_sale_decrements_and_logs(self):
        move = apply_delta(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            delta=-3,
            movement_type=StockMovement.MovementType.SALE,
            user=self.user,
        )
        inv = Inventory.objects.get(product=self.product, warehouse=self.wh_a)
        self.assertEqual(inv.quantity, 97)
        self.assertEqual(move.quantity_before, 100)
        self.assertEqual(move.quantity_after, 97)
        self.assertEqual(move.movement_type, "sale")

    def test_transfer_pair(self):
        apply_delta(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            delta=-10,
            movement_type=StockMovement.MovementType.TRANSFER_OUT,
            user=self.user,
            transfer_id=1,
        )
        apply_delta(
            product_id=self.product.id,
            warehouse_id=self.wh_b.id,
            delta=10,
            movement_type=StockMovement.MovementType.TRANSFER_IN,
            user=self.user,
            transfer_id=1,
        )
        self.assertEqual(
            Inventory.objects.get(product=self.product, warehouse=self.wh_a).quantity, 90
        )
        self.assertEqual(
            Inventory.objects.get(product=self.product, warehouse=self.wh_b).quantity, 10
        )

    def test_set_absolute_adjustment(self):
        set_absolute_quantity(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            new_quantity=80,
            movement_type=StockMovement.MovementType.DAMAGE,
            user=self.user,
        )
        inv = Inventory.objects.get(product=self.product, warehouse=self.wh_a)
        self.assertEqual(inv.quantity, 80)
        move = StockMovement.objects.latest("id")
        self.assertEqual(move.quantity_delta, -20)
        self.assertEqual(move.movement_type, "damage")

    def test_opening_closing_with_period(self):
        now = timezone.now()
        apply_delta(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            delta=-5,
            movement_type=StockMovement.MovementType.SALE,
            user=self.user,
            occurred_at=now - timedelta(days=2),
        )
        apply_delta(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            delta=-2,
            movement_type=StockMovement.MovementType.SALE,
            user=self.user,
            occurred_at=now,
        )
        start = now - timedelta(days=1)
        end = now + timedelta(hours=1)
        oc = opening_closing_stock(
            product_id=self.product.id,
            warehouse_id=self.wh_a.id,
            start_dt=start,
            end_dt=end,
        )
        # Before start: -5 from initial 0 ledger perspective (no opening seed)
        # Note: opening is sum of deltas before start, not live inventory seed.
        self.assertEqual(oc["period_net_delta"], -2)
