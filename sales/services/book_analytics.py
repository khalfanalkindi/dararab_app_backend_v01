"""
Title-level Book Sales Analytics (Phase 1).

Reads the same InvoiceItem / Return / Transfer / Inventory records used by
POS, invoicing, and stock — no separate manual totals.

Counting rules (frozen for Phase 1):
- Revenue = line total_price after discounts; tax excluded.
- Transfers are never sales.
- Lines with discount_percent >= 100 or total_price == 0 → complimentary (0 revenue).
- Returns reduce net units and net revenue (pro-rata on line total_price).
- Child invoices (main_invoice set) are excluded to avoid double-counting
  parent/child copies of the same lines.
- Channel = invoice_type ListItem.
- Currency for this report is always USD ($); OMR remains POS display-only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from math import floor
from typing import Any, Optional

from django.utils import timezone

from inventory.models import Inventory, PrintRun, Product, Transfer
from sales.models import InvoiceItem, Return


class BookAnalyticsError(ValueError):
    """Invalid filters or missing product for book analytics."""


ZERO = Decimal("0.00")
QUANTIZE = Decimal("0.01")

DISCOUNT_BANDS = (
    ("0", "0%", Decimal("0"), Decimal("0")),
    ("1_25", "1–25%", Decimal("0.01"), Decimal("25")),
    ("26_50", "26–50%", Decimal("26"), Decimal("50")),
    ("51_99", "51–99%", Decimal("51"), Decimal("99.99")),
    ("100", "100% (complimentary)", Decimal("100"), Decimal("100")),
)


def _d(value: Any) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal) -> float:
    return float(value.quantize(QUANTIZE))


def _is_complimentary(discount_percent: Decimal, total_price: Decimal) -> bool:
    return discount_percent >= Decimal("100") or total_price <= ZERO


def _payment_status(paid_amount: Decimal, total_price: Decimal, is_paid: bool) -> str:
    if total_price <= ZERO or is_paid or paid_amount >= total_price:
        return "paid"
    if paid_amount > ZERO:
        return "partial"
    return "unpaid"


def _paid_quantity(quantity: int, paid_amount: Decimal, total_price: Decimal, is_paid: bool) -> int:
    if quantity <= 0:
        return 0
    if total_price <= ZERO:
        return quantity if is_paid or paid_amount > ZERO else 0
    if is_paid or paid_amount >= total_price:
        return quantity
    proportion = float(paid_amount) / float(total_price)
    return max(0, min(quantity, floor(proportion * quantity)))


def _band_key(discount_percent: Decimal) -> str:
    if discount_percent <= ZERO:
        return "0"
    if discount_percent >= Decimal("100"):
        return "100"
    if discount_percent <= Decimal("25"):
        return "1_25"
    if discount_percent <= Decimal("50"):
        return "26_50"
    return "51_99"


@dataclass
class BookAnalyticsFilters:
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    warehouse_id: Optional[int] = None
    customer_id: Optional[int] = None
    customer_type_id: Optional[int] = None
    invoice_type_id: Optional[int] = None
    payment_status: Optional[str] = None  # paid | partial | unpaid
    invoice_search: Optional[str] = None
    discount_min: Optional[Decimal] = None
    discount_max: Optional[Decimal] = None
    page: int = 1
    page_size: int = 50

    def echo(self) -> dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "warehouse_id": self.warehouse_id,
            "customer_id": self.customer_id,
            "customer_type_id": self.customer_type_id,
            "invoice_type_id": self.invoice_type_id,
            "payment_status": self.payment_status,
            "invoice_search": self.invoice_search,
            "discount_min": float(self.discount_min) if self.discount_min is not None else None,
            "discount_max": float(self.discount_max) if self.discount_max is not None else None,
            "page": self.page,
            "page_size": self.page_size,
        }


class BookAnalyticsService:
    MAX_PAGE_SIZE = 200

    def __init__(self, product_id: int, filters: BookAnalyticsFilters):
        self.product_id = product_id
        self.filters = filters
        if filters.page < 1:
            raise BookAnalyticsError("page must be >= 1")
        if filters.page_size < 1 or filters.page_size > self.MAX_PAGE_SIZE:
            raise BookAnalyticsError(f"page_size must be between 1 and {self.MAX_PAGE_SIZE}")
        if filters.payment_status and filters.payment_status not in {"paid", "partial", "unpaid"}:
            raise BookAnalyticsError("payment_status must be paid, partial, or unpaid")
        if filters.start_date and filters.end_date and filters.start_date > filters.end_date:
            raise BookAnalyticsError("start_date must be on or before end_date")
        if (filters.start_date and not filters.end_date) or (filters.end_date and not filters.start_date):
            raise BookAnalyticsError("Both start_date and end_date are required when filtering by date")

    def build(self) -> dict[str, Any]:
        product = (
            Product.objects.select_related("genre", "author")
            .filter(pk=self.product_id)
            .first()
        )
        if not product:
            raise BookAnalyticsError("Product not found")

        items = list(self._sale_items_queryset())
        returns_by_item = self._returns_by_item_id([item.id for item in items])
        transfers = list(self._transfers_queryset())
        stock_rows = list(
            Inventory.objects.filter(product_id=self.product_id)
            .select_related("warehouse")
            .order_by("warehouse__name_en")
        )

        summary, by_warehouse, by_channel, discounts, customers, sale_rows = self._aggregate_sales(
            items, returns_by_item
        )
        transfer_rows = self._transfer_rows(transfers)
        return_rows = self._return_transaction_rows(items, returns_by_item)
        by_warehouse = self._merge_warehouse_stock(by_warehouse, stock_rows)
        by_warehouse = self._enrich_warehouse_ledger(by_warehouse)
        stock_summary = self._stock_summary(stock_rows)

        transactions = sorted(
            sale_rows + transfer_rows + return_rows,
            key=lambda row: (row["date"] or "", row["transaction_type"], row.get("id") or 0),
            reverse=True,
        )
        total_transactions = len(transactions)
        start = (self.filters.page - 1) * self.filters.page_size
        end = start + self.filters.page_size
        page_rows = transactions[start:end]

        published_at = (
            PrintRun.objects.filter(product_id=self.product_id)
            .order_by("published_at", "edition_number")
            .values_list("published_at", flat=True)
            .first()
        )

        return {
            "currency": "$",
            "generated_at": timezone.now().isoformat(),
            "product": {
                "id": product.id,
                "isbn": product.isbn,
                "title_ar": product.title_ar,
                "title_en": product.title_en,
                "price": _money(_d(product.price)) if product.price is not None else None,
                "genre": product.genre.display_name_en if product.genre else None,
                "author": str(product.author) if product.author else None,
                "published_at": published_at.isoformat() if published_at else None,
            },
            "filters": self.filters.echo(),
            "rules": {
                "revenue": "line total_price after discounts; tax excluded",
                "transfers": "never counted as sales",
                "complimentary": "discount_percent >= 100 or total_price == 0",
                "returns": "reduce net units and net revenue pro-rata; Phase 2 restocks warehouse",
                "child_invoices": "excluded (main_invoice set) to avoid double-counting",
                "channel": "invoice_type",
                "currency": "USD ($); OMR is POS display-only",
                "stock_ledger": "opening/closing from StockMovement when date range set",
            },
            "summary": summary,
            "stock": stock_summary,
            "by_warehouse": by_warehouse,
            "by_channel": by_channel,
            "discounts": discounts,
            "customers": customers,
            "transactions": {
                "count": total_transactions,
                "page": self.filters.page,
                "page_size": self.filters.page_size,
                "results": page_rows,
            },
        }

    def _sale_items_queryset(self):
        qs = (
            InvoiceItem.objects.filter(product_id=self.product_id, product__isnull=False)
            # Parent/root invoices only — child copies would double-count.
            .filter(invoice__main_invoice__isnull=True)
            .select_related(
                "invoice",
                "invoice__customer",
                "invoice__customer__customer_type",
                "invoice__warehouse",
                "invoice__invoice_type",
                "invoice__created_by",
                "product",
            )
            .order_by("-invoice__created_at", "-id")
        )

        f = self.filters
        if f.start_date and f.end_date:
            start_dt = timezone.make_aware(datetime.combine(f.start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(f.end_date, datetime.max.time()))
            qs = qs.filter(invoice__created_at__gte=start_dt, invoice__created_at__lte=end_dt)
        if f.warehouse_id:
            qs = qs.filter(invoice__warehouse_id=f.warehouse_id)
        if f.customer_id:
            qs = qs.filter(invoice__customer_id=f.customer_id)
        if f.customer_type_id:
            qs = qs.filter(invoice__customer__customer_type_id=f.customer_type_id)
        if f.invoice_type_id:
            qs = qs.filter(invoice__invoice_type_id=f.invoice_type_id)
        if f.invoice_search:
            term = f.invoice_search.strip()
            qs = qs.filter(
                models_q_invoice_search(term)
            )
        if f.discount_min is not None:
            qs = qs.filter(discount_percent__gte=f.discount_min)
        if f.discount_max is not None:
            qs = qs.filter(discount_percent__lte=f.discount_max)

        return qs

    def _transfers_queryset(self):
        qs = (
            Transfer.objects.filter(product_id=self.product_id)
            .select_related("from_warehouse", "to_warehouse", "created_by")
            .order_by("-transfer_date", "-id")
        )
        f = self.filters
        if f.start_date and f.end_date:
            start_dt = timezone.make_aware(datetime.combine(f.start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(f.end_date, datetime.max.time()))
            qs = qs.filter(transfer_date__gte=start_dt, transfer_date__lte=end_dt)
        if f.warehouse_id:
            qs = qs.filter(
                models_q_transfer_warehouse(f.warehouse_id)
            )
        # Customer / payment / discount filters do not apply to transfers.
        if f.customer_id or f.customer_type_id or f.payment_status or f.invoice_type_id or f.invoice_search:
            return Transfer.objects.none()
        if f.discount_min is not None or f.discount_max is not None:
            return Transfer.objects.none()
        return qs

    def _returns_by_item_id(self, item_ids: list[int]) -> dict[int, list[Return]]:
        if not item_ids:
            return {}
        mapping: dict[int, list[Return]] = defaultdict(list)
        for row in Return.objects.filter(invoice_item_id__in=item_ids).order_by("return_date", "id"):
            mapping[row.invoice_item_id].append(row)
        return mapping

    def _aggregate_sales(self, items: list[InvoiceItem], returns_by_item: dict[int, list[Return]]):
        copies_invoiced = 0
        copies_paid = 0
        copies_unpaid = 0
        copies_complimentary = 0
        copies_returned = 0
        copies_net_sold = 0
        gross_value = ZERO
        discount_value = ZERO
        net_revenue = ZERO
        amount_received = ZERO
        amount_outstanding = ZERO
        returned_revenue = ZERO

        warehouse_map: dict[int, dict[str, Any]] = {}
        channel_map: dict[str, dict[str, Any]] = {}
        band_map = {
            key: {
                "key": key,
                "label": label,
                "copies": 0,
                "gross_value": ZERO,
                "net_value": ZERO,
                "discount_value": ZERO,
            }
            for key, label, _lo, _hi in DISCOUNT_BANDS
        }
        customer_map: dict[int, dict[str, Any]] = {}
        sale_rows: list[dict[str, Any]] = []

        for item in items:
            invoice = item.invoice
            quantity = int(item.quantity or 0)
            unit_price = _d(item.unit_price)
            discount_percent = _d(item.discount_percent)
            total_price = _d(item.total_price)
            paid_amount = _d(item.paid_amount)
            remaining_amount = _d(item.remaining_amount)
            complimentary = _is_complimentary(discount_percent, total_price)
            status = _payment_status(paid_amount, total_price, bool(item.is_paid))

            if self.filters.payment_status and status != self.filters.payment_status:
                continue

            gross = unit_price * Decimal(quantity)
            discount_amt = gross - total_price
            if discount_amt < ZERO:
                discount_amt = ZERO

            item_returns = returns_by_item.get(item.id, [])
            returned_qty = sum(int(r.returned_quantity or 0) for r in item_returns)
            if returned_qty > quantity:
                returned_qty = quantity
            returned_rev = ZERO
            if quantity > 0 and returned_qty > 0 and total_price > ZERO:
                returned_rev = (total_price * Decimal(returned_qty) / Decimal(quantity)).quantize(QUANTIZE)

            paid_qty = _paid_quantity(quantity, paid_amount, total_price, bool(item.is_paid))
            unpaid_qty = max(0, quantity - paid_qty)

            # Summary (complimentary copies counted separately; 0 revenue)
            copies_invoiced += quantity
            copies_returned += returned_qty
            if complimentary:
                copies_complimentary += quantity
            else:
                copies_paid += paid_qty
                copies_unpaid += unpaid_qty
                copies_net_sold += max(0, quantity - returned_qty)
                gross_value += gross
                discount_value += discount_amt
                net_revenue += total_price
                amount_received += paid_amount
                amount_outstanding += remaining_amount
                returned_revenue += returned_rev

            # Warehouse
            wh = invoice.warehouse
            wh_id = wh.id if wh else 0
            wh_row = warehouse_map.setdefault(
                wh_id,
                {
                    "warehouse_id": wh.id if wh else None,
                    "warehouse_name": wh.name_en if wh else "No Warehouse",
                    "copies_sold": 0,
                    "copies_returned": 0,
                    "copies_complimentary": 0,
                    "net_revenue": ZERO,
                    "current_stock": 0,
                },
            )
            wh_row["copies_sold"] += quantity
            wh_row["copies_returned"] += returned_qty
            if complimentary:
                wh_row["copies_complimentary"] += quantity
            else:
                wh_row["net_revenue"] += total_price - returned_rev

            # Channel (invoice_type)
            channel = invoice.invoice_type
            channel_key = str(channel.id) if channel else "unknown"
            ch_row = channel_map.setdefault(
                channel_key,
                {
                    "invoice_type_id": channel.id if channel else None,
                    "channel": channel.display_name_en if channel else "Unknown",
                    "channel_value": channel.value if channel else None,
                    "copies": 0,
                    "net_revenue": ZERO,
                },
            )
            ch_row["copies"] += quantity
            if not complimentary:
                ch_row["net_revenue"] += total_price - returned_rev

            # Discount bands
            band = band_map[_band_key(discount_percent)]
            band["copies"] += quantity
            band["gross_value"] += gross
            band["net_value"] += total_price
            band["discount_value"] += discount_amt

            # Customers
            customer = invoice.customer
            if customer:
                c_row = customer_map.setdefault(
                    customer.id,
                    {
                        "customer_id": customer.id,
                        "customer_name": customer.institution_name,
                        "customer_type": (
                            customer.customer_type.display_name_en
                            if customer.customer_type
                            else None
                        ),
                        "customer_type_value": (
                            customer.customer_type.value if customer.customer_type else None
                        ),
                        "copies": 0,
                        "copies_returned": 0,
                        "discount_value": ZERO,
                        "net_value": ZERO,
                        "amount_received": ZERO,
                        "amount_outstanding": ZERO,
                        "payment_statuses": set(),
                        "last_purchase_date": None,
                        "invoice_count": 0,
                        "_invoice_ids": set(),
                    },
                )
                c_row["copies"] += quantity
                c_row["copies_returned"] += returned_qty
                c_row["discount_value"] += discount_amt
                if not complimentary:
                    c_row["net_value"] += total_price - returned_rev
                    c_row["amount_received"] += paid_amount
                    c_row["amount_outstanding"] += remaining_amount
                c_row["payment_statuses"].add(status)
                inv_date = invoice.created_at.date().isoformat() if invoice.created_at else None
                if inv_date and (
                    c_row["last_purchase_date"] is None or inv_date > c_row["last_purchase_date"]
                ):
                    c_row["last_purchase_date"] = inv_date
                if invoice.id not in c_row["_invoice_ids"]:
                    c_row["_invoice_ids"].add(invoice.id)
                    c_row["invoice_count"] += 1

            created_by = invoice.created_by
            sale_rows.append(
                {
                    "id": item.id,
                    "date": invoice.created_at.date().isoformat() if invoice.created_at else None,
                    "transaction_type": "complimentary" if complimentary else "sale",
                    "invoice_id": invoice.id,
                    "composite_id": invoice.composite_id or str(invoice.id),
                    "customer_id": customer.id if customer else None,
                    "customer_name": customer.institution_name if customer else None,
                    "channel": channel.display_name_en if channel else None,
                    "warehouse_id": wh.id if wh else None,
                    "warehouse_name": wh.name_en if wh else None,
                    "quantity": quantity,
                    "list_price": _money(unit_price),
                    "discount_percent": float(discount_percent),
                    "final_unit_price": _money(total_price / quantity) if quantity else 0.0,
                    "net_amount": _money(total_price),
                    "payment_status": status,
                    "paid_amount": _money(paid_amount),
                    "remaining_amount": _money(remaining_amount),
                    "returned_quantity": returned_qty,
                    "salesperson": (
                        (
                            getattr(created_by, "username", None)
                            or getattr(created_by, "email", None)
                        )
                        if created_by
                        else None
                    ),
                }
            )

        # Net revenue after returns (complimentary already 0)
        net_revenue_after_returns = net_revenue - returned_revenue
        if net_revenue_after_returns < ZERO:
            net_revenue_after_returns = ZERO

        avg_discount = float((discount_value / gross_value * 100) if gross_value > ZERO else ZERO)

        summary = {
            "copies_invoiced": copies_invoiced,
            "copies_paid": copies_paid,
            "copies_unpaid": copies_unpaid,
            "copies_returned": copies_returned,
            "copies_complimentary": copies_complimentary,
            "copies_net_sold": copies_net_sold,
            "gross_value": _money(gross_value),
            "discount_value": _money(discount_value),
            "average_discount_percent": round(avg_discount, 2),
            "net_revenue": _money(net_revenue_after_returns),
            "amount_received": _money(amount_received),
            "amount_outstanding": _money(amount_outstanding),
            "returned_revenue": _money(returned_revenue),
        }

        by_warehouse = []
        for row in warehouse_map.values():
            by_warehouse.append(
                {
                    **row,
                    "net_revenue": _money(row["net_revenue"]),
                    "copies_net": max(0, row["copies_sold"] - row["copies_returned"]),
                }
            )
        by_warehouse.sort(key=lambda r: r["copies_sold"], reverse=True)

        by_channel = []
        for row in channel_map.values():
            by_channel.append({**row, "net_revenue": _money(row["net_revenue"])})
        by_channel.sort(key=lambda r: r["copies"], reverse=True)

        discounts = []
        for key, label, _lo, _hi in DISCOUNT_BANDS:
            row = band_map[key]
            discounts.append(
                {
                    "key": key,
                    "label": label,
                    "copies": row["copies"],
                    "gross_value": _money(row["gross_value"]),
                    "net_value": _money(row["net_value"]),
                    "discount_value": _money(row["discount_value"]),
                }
            )

        customers = []
        for row in customer_map.values():
            statuses = row.pop("payment_statuses")
            row.pop("_invoice_ids")
            if "unpaid" in statuses and ("paid" in statuses or "partial" in statuses):
                rollup_status = "mixed"
            elif statuses == {"paid"}:
                rollup_status = "paid"
            elif statuses == {"partial"} or ("partial" in statuses and "paid" in statuses):
                rollup_status = "partial"
            elif statuses == {"unpaid"}:
                rollup_status = "unpaid"
            else:
                rollup_status = "mixed"
            customers.append(
                {
                    **row,
                    "discount_value": _money(row["discount_value"]),
                    "net_value": _money(row["net_value"]),
                    "amount_received": _money(row["amount_received"]),
                    "amount_outstanding": _money(row["amount_outstanding"]),
                    "payment_status": rollup_status,
                    "is_repeat": row["invoice_count"] > 1,
                }
            )
        customers.sort(key=lambda r: (r["net_value"], r["copies"]), reverse=True)

        return summary, by_warehouse, by_channel, discounts, customers, sale_rows

    def _merge_warehouse_stock(self, by_warehouse: list[dict], stock_rows: list[Inventory]):
        by_id = {row["warehouse_id"]: row for row in by_warehouse if row["warehouse_id"] is not None}
        for inv in stock_rows:
            row = by_id.get(inv.warehouse_id)
            if row:
                row["current_stock"] = int(inv.quantity or 0)
            else:
                by_warehouse.append(
                    {
                        "warehouse_id": inv.warehouse_id,
                        "warehouse_name": inv.warehouse.name_en if inv.warehouse else "No Warehouse",
                        "copies_sold": 0,
                        "copies_returned": 0,
                        "copies_complimentary": 0,
                        "copies_net": 0,
                        "net_revenue": 0.0,
                        "current_stock": int(inv.quantity or 0),
                    }
                )
        by_warehouse.sort(key=lambda r: (r["copies_sold"], r["current_stock"]), reverse=True)
        return by_warehouse

    def _period_bounds(self):
        f = self.filters
        if not f.start_date or not f.end_date:
            return None, None
        start_dt = timezone.make_aware(datetime.combine(f.start_date, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(f.end_date, datetime.max.time()))
        return start_dt, end_dt

    def _enrich_warehouse_ledger(self, by_warehouse: list[dict]) -> list[dict]:
        from inventory.models import StockMovement
        from inventory.services.stock_ledger import opening_closing_stock, movement_type_totals

        start_dt, end_dt = self._period_bounds()
        warehouse_filter = self.filters.warehouse_id

        for row in by_warehouse:
            wh_id = row.get("warehouse_id")
            if warehouse_filter and wh_id != warehouse_filter:
                continue
            if not wh_id:
                row.update({
                    "opening_stock": None,
                    "closing_stock": row.get("current_stock", 0),
                    "sold": 0,
                    "returned": 0,
                    "transferred_in": 0,
                    "transferred_out": 0,
                    "damaged": 0,
                    "lost": 0,
                    "reserved": 0,
                    "adjusted": 0,
                    "complimentary_issued": 0,
                })
                continue

            oc = opening_closing_stock(
                product_id=self.product_id,
                warehouse_id=wh_id,
                start_dt=start_dt,
                end_dt=end_dt,
                current_quantity=int(row.get("current_stock") or 0),
            )
            totals = movement_type_totals(
                product_id=self.product_id,
                warehouse_id=wh_id,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            MT = StockMovement.MovementType
            row.update({
                "opening_stock": oc["opening_stock"],
                "closing_stock": oc["closing_stock"] if end_dt else int(row.get("current_stock") or 0),
                "sold": abs(min(0, totals.get(MT.SALE, 0))),
                "returned": max(0, totals.get(MT.RETURN, 0) + totals.get(MT.RESTOCK, 0)),
                "transferred_in": max(0, totals.get(MT.TRANSFER_IN, 0)),
                "transferred_out": abs(min(0, totals.get(MT.TRANSFER_OUT, 0))),
                "damaged": abs(min(0, totals.get(MT.DAMAGE, 0))),
                "lost": abs(min(0, totals.get(MT.LOSS, 0))),
                "reserved": abs(min(0, totals.get(MT.RESERVED, 0))),
                "adjusted": totals.get(MT.ADJUSTMENT, 0),
                "complimentary_issued": abs(min(0, totals.get(MT.COMPLIMENTARY, 0))),
            })
        return by_warehouse

    def _stock_summary(self, stock_rows: list[Inventory]) -> dict[str, Any]:
        from inventory.models import StockMovement
        from inventory.services.stock_ledger import opening_closing_stock, movement_type_totals

        start_dt, end_dt = self._period_bounds()
        warehouse_id = self.filters.warehouse_id
        current = sum(int(r.quantity or 0) for r in stock_rows if not warehouse_id or r.warehouse_id == warehouse_id)
        oc = opening_closing_stock(
            product_id=self.product_id,
            warehouse_id=warehouse_id,
            start_dt=start_dt,
            end_dt=end_dt,
            current_quantity=current,
        )
        totals = movement_type_totals(
            product_id=self.product_id,
            warehouse_id=warehouse_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        MT = StockMovement.MovementType
        return {
            "opening_stock": oc["opening_stock"],
            "closing_stock": oc["closing_stock"] if end_dt else current,
            "current_stock": current,
            "period_net_delta": oc["period_net_delta"],
            "sold": abs(min(0, totals.get(MT.SALE, 0))),
            "returned": max(0, totals.get(MT.RETURN, 0) + totals.get(MT.RESTOCK, 0)),
            "transferred_in": max(0, totals.get(MT.TRANSFER_IN, 0)),
            "transferred_out": abs(min(0, totals.get(MT.TRANSFER_OUT, 0))),
            "damaged": abs(min(0, totals.get(MT.DAMAGE, 0))),
            "lost": abs(min(0, totals.get(MT.LOSS, 0))),
            "reserved": abs(min(0, totals.get(MT.RESERVED, 0))),
            "adjusted": totals.get(MT.ADJUSTMENT, 0),
            "complimentary_issued": abs(min(0, totals.get(MT.COMPLIMENTARY, 0))),
            "ledger_complete": StockMovement.objects.filter(product_id=self.product_id).exists(),
        }

    def _transfer_rows(self, transfers: list[Transfer]) -> list[dict[str, Any]]:
        rows = []
        for t in transfers:
            when = t.transfer_date
            date_str = None
            if when:
                date_str = when.date().isoformat() if hasattr(when, "date") else str(when)[:10]
            created_by = t.created_by
            rows.append(
                {
                    "id": t.id,
                    "date": date_str,
                    "transaction_type": "transfer",
                    "invoice_id": None,
                    "composite_id": None,
                    "customer_id": None,
                    "customer_name": None,
                    "channel": None,
                    "warehouse_id": t.from_warehouse_id,
                    "warehouse_name": (
                        f"{t.from_warehouse.name_en if t.from_warehouse else '?'} → "
                        f"{t.to_warehouse.name_en if t.to_warehouse else '?'}"
                    ),
                    "quantity": int(t.quantity or 0),
                    "list_price": 0.0,
                    "discount_percent": 0.0,
                    "final_unit_price": 0.0,
                    "net_amount": 0.0,
                    "payment_status": None,
                    "paid_amount": 0.0,
                    "remaining_amount": 0.0,
                    "returned_quantity": 0,
                    "salesperson": (
                        (
                            getattr(created_by, "username", None)
                            or getattr(created_by, "email", None)
                        )
                        if created_by
                        else None
                    ),
                    "from_warehouse_id": t.from_warehouse_id,
                    "to_warehouse_id": t.to_warehouse_id,
                }
            )
        return rows

    def _return_transaction_rows(
        self, items: list[InvoiceItem], returns_by_item: dict[int, list[Return]]
    ) -> list[dict[str, Any]]:
        """Separate return events in the transaction timeline (in addition to sale returned_quantity)."""
        item_by_id = {item.id: item for item in items}
        rows = []
        for item_id, returns in returns_by_item.items():
            item = item_by_id.get(item_id)
            if not item:
                continue
            invoice = item.invoice
            for r in returns:
                qty = int(r.returned_quantity or 0)
                total_price = _d(item.total_price)
                quantity = int(item.quantity or 0)
                rev = ZERO
                if quantity > 0 and qty > 0 and total_price > ZERO:
                    rev = (total_price * Decimal(qty) / Decimal(quantity)).quantize(QUANTIZE)
                rows.append(
                    {
                        "id": r.id,
                        "date": r.return_date.isoformat() if r.return_date else None,
                        "transaction_type": "return",
                        "invoice_id": invoice.id,
                        "composite_id": invoice.composite_id or str(invoice.id),
                        "customer_id": invoice.customer_id,
                        "customer_name": (
                            invoice.customer.institution_name if invoice.customer else None
                        ),
                        "channel": (
                            invoice.invoice_type.display_name_en if invoice.invoice_type else None
                        ),
                        "warehouse_id": invoice.warehouse_id,
                        "warehouse_name": invoice.warehouse.name_en if invoice.warehouse else None,
                        "quantity": qty,
                        "list_price": _money(_d(item.unit_price)),
                        "discount_percent": float(_d(item.discount_percent)),
                        "final_unit_price": _money(_d(item.unit_price)),
                        "net_amount": _money(-rev),
                        "payment_status": None,
                        "paid_amount": 0.0,
                        "remaining_amount": 0.0,
                        "returned_quantity": qty,
                        "salesperson": None,
                        "invoice_item_id": item.id,
                    }
                )
        return rows


def models_q_invoice_search(term: str):
    from django.db.models import Q

    q = Q(invoice__composite_id__icontains=term) | Q(invoice__notes__icontains=term)
    if term.isdigit():
        q = q | Q(invoice_id=int(term))
    return q


def models_q_transfer_warehouse(warehouse_id: int):
    from django.db.models import Q

    return Q(from_warehouse_id=warehouse_id) | Q(to_warehouse_id=warehouse_id)
