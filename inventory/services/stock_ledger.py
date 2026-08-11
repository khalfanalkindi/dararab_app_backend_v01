"""
Stock ledger helpers (Phase 2).

Every inventory quantity change should go through this module so analytics
can compute opening/closing stock and typed movements.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from inventory.models import Inventory, StockMovement


ALLOWED_MOVEMENT_TYPES = {choice.value for choice in StockMovement.MovementType}


class StockLedgerError(serializers.ValidationError):
    """Raised when a stock change cannot be applied."""


def _aware(dt: Optional[datetime] = None) -> datetime:
    if dt is None:
        return timezone.now()
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


@transaction.atomic
def apply_delta(
    *,
    product_id: int,
    warehouse_id: int,
    delta: int,
    movement_type: str,
    user=None,
    occurred_at: Optional[datetime] = None,
    notes: str = "",
    reference_code: str = "",
    invoice_id: Optional[int] = None,
    invoice_item_id: Optional[int] = None,
    transfer_id: Optional[int] = None,
    return_id: Optional[int] = None,
    allow_negative: bool = False,
) -> StockMovement:
    """
    Apply a signed quantity change to Inventory and append a StockMovement row.
    Caller should already be inside a transaction when composing multi-step flows.
    """
    if movement_type not in ALLOWED_MOVEMENT_TYPES:
        raise StockLedgerError({"movement_type": f"Invalid movement_type: {movement_type}"})
    if delta == 0:
        raise StockLedgerError({"quantity": "quantity_delta must be non-zero"})

    inv, _ = Inventory.objects.select_for_update().get_or_create(
        product_id=product_id,
        warehouse_id=warehouse_id,
        defaults={
            "quantity": 0,
            "created_by": user,
            "updated_by": user,
        },
    )
    before = int(inv.quantity or 0)
    after = before + int(delta)
    if after < 0 and not allow_negative:
        raise StockLedgerError({
            "quantity": (
                f"Insufficient inventory. Available: {before}, "
                f"Requested change: {delta}"
            )
        })

    inv.quantity = after
    inv.updated_by = user
    inv.save(update_fields=["quantity", "updated_by", "updated_at"])

    return StockMovement.objects.create(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity_delta=int(delta),
        quantity_before=before,
        quantity_after=after,
        occurred_at=_aware(occurred_at),
        notes=notes or "",
        reference_code=reference_code or "",
        invoice_id=invoice_id,
        invoice_item_id=invoice_item_id,
        transfer_id=transfer_id,
        return_id=return_id,
        created_by=user,
        updated_by=user,
    )


@transaction.atomic
def set_absolute_quantity(
    *,
    product_id: int,
    warehouse_id: int,
    new_quantity: int,
    movement_type: str = StockMovement.MovementType.ADJUSTMENT,
    user=None,
    occurred_at: Optional[datetime] = None,
    notes: str = "",
    reference_code: str = "",
    invoice_id: Optional[int] = None,
    invoice_item_id: Optional[int] = None,
    transfer_id: Optional[int] = None,
    return_id: Optional[int] = None,
    allow_negative: bool = False,
) -> Optional[StockMovement]:
    """
    Set inventory to an absolute quantity and record the delta.
    Returns None if quantity is unchanged.
    """
    if new_quantity < 0 and not allow_negative:
        raise StockLedgerError({"quantity": "Quantity cannot be negative"})

    inv, _ = Inventory.objects.select_for_update().get_or_create(
        product_id=product_id,
        warehouse_id=warehouse_id,
        defaults={
            "quantity": 0,
            "created_by": user,
            "updated_by": user,
        },
    )
    before = int(inv.quantity or 0)
    delta = int(new_quantity) - before
    if delta == 0:
        return None

    return apply_delta(
        product_id=product_id,
        warehouse_id=warehouse_id,
        delta=delta,
        movement_type=movement_type,
        user=user,
        occurred_at=occurred_at,
        notes=notes,
        reference_code=reference_code,
        invoice_id=invoice_id,
        invoice_item_id=invoice_item_id,
        transfer_id=transfer_id,
        return_id=return_id,
        allow_negative=allow_negative,
    )


def sum_delta(
    *,
    product_id: int,
    warehouse_id: Optional[int] = None,
    before: Optional[datetime] = None,
    until: Optional[datetime] = None,
    movement_types: Optional[list[str]] = None,
) -> int:
    """Sum quantity_delta for a product (optionally warehouse + time window)."""
    qs = StockMovement.objects.filter(product_id=product_id)
    if warehouse_id is not None:
        qs = qs.filter(warehouse_id=warehouse_id)
    if before is not None:
        qs = qs.filter(occurred_at__lt=_aware(before))
    if until is not None:
        qs = qs.filter(occurred_at__lte=_aware(until))
    if movement_types:
        qs = qs.filter(movement_type__in=movement_types)
    return int(qs.aggregate(total=Sum("quantity_delta"))["total"] or 0)


def opening_closing_stock(
    *,
    product_id: int,
    warehouse_id: Optional[int] = None,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
    current_quantity: Optional[int] = None,
) -> dict[str, int]:
    """
    Compute opening/closing stock for a period from the ledger.

    opening = sum(deltas before start)   [0 if no start]
    period  = sum(deltas in [start, end])
    closing = opening + period

    When end_dt is omitted and current_quantity is provided, closing uses the
    live inventory snapshot and opening is derived as closing - period.
    """
    now = timezone.now()
    end = _aware(end_dt) if end_dt else now
    start = _aware(start_dt) if start_dt else None

    if start is not None:
        opening = sum_delta(product_id=product_id, warehouse_id=warehouse_id, before=start)
        period = sum_delta_between(
            product_id=product_id,
            warehouse_id=warehouse_id,
            start=start,
            end=end,
        )
    else:
        opening = 0
        period = sum_delta(product_id=product_id, warehouse_id=warehouse_id, until=end)

    closing = opening + period

    if end_dt is None and current_quantity is not None:
        closing = int(current_quantity)
        if start is not None:
            opening = closing - period

    return {
        "opening_stock": opening,
        "closing_stock": closing,
        "period_net_delta": period,
    }


def sum_delta_between(
    *,
    product_id: int,
    warehouse_id: Optional[int] = None,
    start: datetime,
    end: datetime,
) -> int:
    qs = StockMovement.objects.filter(
        product_id=product_id,
        occurred_at__gte=_aware(start),
        occurred_at__lte=_aware(end),
    )
    if warehouse_id is not None:
        qs = qs.filter(warehouse_id=warehouse_id)
    return int(qs.aggregate(total=Sum("quantity_delta"))["total"] or 0)


def movement_type_totals(
    *,
    product_id: int,
    warehouse_id: Optional[int] = None,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
) -> dict[str, int]:
    """Absolute units moved per type (uses abs of outbound for readability where noted)."""
    qs = StockMovement.objects.filter(product_id=product_id)
    if warehouse_id is not None:
        qs = qs.filter(warehouse_id=warehouse_id)
    if start_dt is not None:
        qs = qs.filter(occurred_at__gte=_aware(start_dt))
    if end_dt is not None:
        qs = qs.filter(occurred_at__lte=_aware(end_dt))

    totals = {key: 0 for key in ALLOWED_MOVEMENT_TYPES}
    for row in qs.values("movement_type").annotate(total=Sum("quantity_delta")):
        key = row["movement_type"]
        totals[key] = int(row["total"] or 0)
    return totals
