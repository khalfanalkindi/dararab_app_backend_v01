"""
Settle a single outstanding invoice into a paid child bill.

Per-invoice only (no multi-invoice settle). Copies every unpaid line as paid
onto a new child invoice, records a payment, and marks parent lines paid.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from common.models import ListItem, ListType
from sales.models import Invoice, InvoiceItem, Payment

ZERO = Decimal("0.00")
MONEY = Decimal("0.01")


class SettleInvoiceError(Exception):
    """Business-rule failure while settling an invoice."""

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY)


def _get_or_create_postpaid_payment_method() -> ListItem | None:
    list_type, _ = ListType.objects.get_or_create(
        code="payment_method",
        defaults={
            "name_en": "Payment Method",
            "name_ar": "طريقة الدفع",
        },
    )
    existing = ListItem.objects.filter(
        list_type=list_type,
        value__iexact="postpaid",
    ).first()
    if existing:
        return existing
    return ListItem.objects.create(
        list_type=list_type,
        value="postpaid",
        display_name_en="Postpaid",
        display_name_ar="آجل / مدفوع مسبقاً",
    )


@transaction.atomic
def settle_invoice(*, invoice_id: int, user=None) -> dict[str, Any]:
    """
    Settle one invoice: create a paid child from all unpaid items.

    Returns a dict with parent/child ids, amounts, and settled item count.
    """
    try:
        parent = (
            Invoice.objects.select_for_update()
            .select_related("customer", "warehouse", "invoice_type", "payment_method")
            .get(pk=invoice_id)
        )
    except Invoice.DoesNotExist as exc:
        raise SettleInvoiceError("Invoice not found.", status_code=404) from exc

    if not parent.customer_id or not parent.warehouse_id:
        raise SettleInvoiceError("Invoice is missing customer or warehouse.")

    unpaid_items = list(
        InvoiceItem.objects.select_for_update()
        .filter(invoice_id=parent.id, is_paid=False)
        .order_by("id")
    )
    if not unpaid_items:
        raise SettleInvoiceError("Invoice has no unpaid items to settle.")

    settle_total = _money(sum((_money(item.total_price) for item in unpaid_items), ZERO))
    if settle_total <= ZERO:
        raise SettleInvoiceError("Outstanding amount to settle must be greater than zero.")

    payment_method = _get_or_create_postpaid_payment_method() or parent.payment_method

    child = Invoice.objects.create(
        customer=parent.customer,
        warehouse=parent.warehouse,
        invoice_type=parent.invoice_type,
        payment_method=payment_method,
        is_returnable=parent.is_returnable,
        main_invoice=parent,
        notes=f"Settled from invoice #{parent.composite_id or parent.id}",
        global_discount_percent=ZERO,
        tax_percent=ZERO,
        created_by=user,
        updated_by=user,
    )

    child_item_ids: list[int] = []
    for item in unpaid_items:
        line_total = _money(item.total_price)
        child_item = InvoiceItem.objects.create(
            invoice=child,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_percent=item.discount_percent or ZERO,
            total_price=line_total,
            paid_amount=line_total,
            remaining_amount=ZERO,
            is_paid=True,
            created_by=user,
            updated_by=user,
        )
        child_item_ids.append(child_item.id)

        # Mark parent line fully paid (same semantics as outstanding child flow)
        item.paid_amount = line_total
        item.remaining_amount = ZERO
        item.is_paid = True
        item.updated_by = user
        item.save()

    payment = Payment.objects.create(
        invoice=child,
        amount=settle_total,
        payment_date=timezone.localdate(),
        notes=f"Settlement payment for child of invoice #{parent.composite_id or parent.id}",
        created_by=user,
        updated_by=user,
    )

    parent_note = (
        f"\nSettled via child invoice #{child.composite_id or child.id} "
        f"({len(unpaid_items)} item(s), {settle_total})."
    )
    parent.notes = f"{(parent.notes or '').rstrip()}{parent_note}".strip()
    parent.updated_by = user
    parent.save(update_fields=["notes", "updated_by", "updated_at"])

    return {
        "parent_invoice_id": parent.id,
        "parent_composite_id": parent.composite_id or str(parent.id),
        "child_invoice_id": child.id,
        "child_composite_id": child.composite_id or str(child.id),
        "settled_item_count": len(unpaid_items),
        "settled_amount": float(settle_total),
        "payment_id": payment.id,
        "child_item_ids": child_item_ids,
        "customer_id": parent.customer_id,
        "warehouse_id": parent.warehouse_id,
    }
