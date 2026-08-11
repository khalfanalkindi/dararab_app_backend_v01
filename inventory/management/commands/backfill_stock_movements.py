"""
Backfill StockMovement rows from historical InvoiceItem, Transfer, and Return data.

Safe to re-run: skips products that already have ledger rows unless --force.

Usage:
  python manage.py backfill_stock_movements
  python manage.py backfill_stock_movements --product-id 12
  python manage.py backfill_stock_movements --force
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import StockMovement, Transfer
from sales.models import InvoiceItem, Return


class Command(BaseCommand):
    help = "Backfill StockMovement ledger from sales, transfers, and returns"

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=None)
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild movements even if ledger rows already exist for the product",
        )

    def handle(self, *args, **options):
        product_id = options.get("product_id")
        force = options.get("force")

        product_ids = set()
        sale_qs = InvoiceItem.objects.filter(
            product__isnull=False,
            invoice__main_invoice__isnull=True,
        )
        transfer_qs = Transfer.objects.all()
        return_qs = Return.objects.filter(invoice_item__product__isnull=False)

        if product_id:
            sale_qs = sale_qs.filter(product_id=product_id)
            transfer_qs = transfer_qs.filter(product_id=product_id)
            return_qs = return_qs.filter(invoice_item__product_id=product_id)

        product_ids.update(sale_qs.values_list("product_id", flat=True).distinct())
        product_ids.update(transfer_qs.values_list("product_id", flat=True).distinct())
        product_ids.update(return_qs.values_list("invoice_item__product_id", flat=True).distinct())

        created = 0
        skipped = 0

        for pid in sorted(p for p in product_ids if p):
            existing = StockMovement.objects.filter(product_id=pid).exists()
            if existing and not force:
                skipped += 1
                self.stdout.write(f"skip product {pid} (ledger exists; use --force)")
                continue

            with transaction.atomic():
                if force:
                    StockMovement.objects.filter(product_id=pid).delete()

                # Historical sales (do NOT change live Inventory — only ledger)
                for item in sale_qs.filter(product_id=pid).select_related("invoice"):
                    invoice = item.invoice
                    if not invoice or not invoice.warehouse_id:
                        continue
                    qty = int(item.quantity or 0)
                    if qty <= 0:
                        continue
                    discount = Decimal(str(item.discount_percent or 0))
                    total = Decimal(str(item.total_price or 0))
                    mtype = (
                        StockMovement.MovementType.COMPLIMENTARY
                        if discount >= 100 or total <= 0
                        else StockMovement.MovementType.SALE
                    )
                    occurred = invoice.created_at or timezone.now()
                    created += self._ledger_only(
                        product_id=pid,
                        warehouse_id=invoice.warehouse_id,
                        delta=-qty,
                        movement_type=mtype,
                        occurred_at=occurred,
                        invoice_id=invoice.id,
                        invoice_item_id=item.id,
                        reference_code=invoice.composite_id or str(invoice.id),
                        notes="Backfill from invoice item",
                    )

                for t in transfer_qs.filter(product_id=pid):
                    qty = int(t.quantity or 0)
                    if qty <= 0:
                        continue
                    occurred = t.transfer_date or timezone.now()
                    created += self._ledger_only(
                        product_id=pid,
                        warehouse_id=t.from_warehouse_id,
                        delta=-qty,
                        movement_type=StockMovement.MovementType.TRANSFER_OUT,
                        occurred_at=occurred,
                        transfer_id=t.id,
                        notes="Backfill transfer out",
                    )
                    created += self._ledger_only(
                        product_id=pid,
                        warehouse_id=t.to_warehouse_id,
                        delta=qty,
                        movement_type=StockMovement.MovementType.TRANSFER_IN,
                        occurred_at=occurred,
                        transfer_id=t.id,
                        notes="Backfill transfer in",
                    )

                for r in return_qs.filter(invoice_item__product_id=pid).select_related(
                    "invoice_item__invoice"
                ):
                    item = r.invoice_item
                    invoice = item.invoice if item else None
                    if not invoice or not invoice.warehouse_id:
                        continue
                    qty = int(r.returned_quantity or 0)
                    if qty <= 0:
                        continue
                    occurred = None
                    if r.return_date:
                        occurred = timezone.make_aware(
                            datetime.combine(r.return_date, datetime.min.time())
                        )
                    created += self._ledger_only(
                        product_id=pid,
                        warehouse_id=invoice.warehouse_id,
                        delta=qty,
                        movement_type=StockMovement.MovementType.RETURN,
                        occurred_at=occurred or timezone.now(),
                        invoice_id=invoice.id,
                        invoice_item_id=item.id,
                        return_id=r.id,
                        reference_code=invoice.composite_id or str(invoice.id),
                        notes="Backfill return (ledger only; inventory not changed)",
                    )

            self.stdout.write(self.style.SUCCESS(f"backfilled product {pid}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done. movements_created={created} products_skipped={skipped}")
        )

    def _ledger_only(self, **kwargs) -> int:
        """
        Write a StockMovement without mutating Inventory.
        Backfill must not disturb live stock balances.
        """
        product_id = kwargs["product_id"]
        warehouse_id = kwargs["warehouse_id"]
        delta = int(kwargs["delta"])
        from inventory.models import Inventory

        inv = Inventory.objects.filter(product_id=product_id, warehouse_id=warehouse_id).first()
        before = int(inv.quantity or 0) if inv else 0
        # For historical rows, before/after are approximate (not reconstructed chronologically)
        StockMovement.objects.create(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=kwargs["movement_type"],
            quantity_delta=delta,
            quantity_before=before,
            quantity_after=before,  # inventory unchanged during backfill
            occurred_at=kwargs["occurred_at"],
            notes=kwargs.get("notes") or "",
            reference_code=kwargs.get("reference_code") or "",
            invoice_id=kwargs.get("invoice_id"),
            invoice_item_id=kwargs.get("invoice_item_id"),
            transfer_id=kwargs.get("transfer_id"),
            return_id=kwargs.get("return_id"),
        )
        return 1
