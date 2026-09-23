"""
Royalty settlement helpers.

Persists Calculate results into RoyaltySettlement open rows.
Settle locks the open row and opens the next cycle.
Does not mutate invoices, payments, inventory, or POS flows.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from math import floor
from typing import Any, Optional

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from sales.models import InvoiceItem, Payment, RoyaltySettlement


def project_first_settle_available_at(project) -> Optional[datetime]:
    """First settle is allowed only after project.created_at + 12 months."""
    created = getattr(project, "created_at", None)
    if not created:
        return None
    try:
        return created + relativedelta(months=12)
    except Exception:
        return created + timedelta(days=365)


def settle_gate_for_contract(*, contract, project) -> dict[str, Any]:
    """
    Calculate may run anytime.
    First Settle requires project age >= 12 months.
    Later settles (after at least one settled row) are allowed.
    """
    prior = has_prior_settlement(contract_id=contract.id)
    available_at = project_first_settle_available_at(project)
    now = timezone.now()
    if prior:
        return {
            "can_settle": True,
            "first_settle_only_gate": False,
            "settle_available_at": available_at.isoformat() if available_at else None,
            "reason": None,
        }
    if available_at is None:
        return {
            "can_settle": False,
            "first_settle_only_gate": True,
            "settle_available_at": None,
            "reason": "Project created_at is missing; cannot verify 12-month settle gate",
        }
    if now < available_at:
        return {
            "can_settle": False,
            "first_settle_only_gate": True,
            "settle_available_at": available_at.isoformat(),
            "reason": (
                "First settlement is allowed only after 12 months from project creation "
                f"(available from {available_at.date().isoformat()})"
            ),
        }
    return {
        "can_settle": True,
        "first_settle_only_gate": True,
        "settle_available_at": available_at.isoformat(),
        "reason": None,
    }


def resolve_period_start(*, contract, project):
    """
    Cycle start = last settled_at for this contract, else project.created_at.
    """
    last_settled = (
        RoyaltySettlement.objects.filter(
            contract_id=contract.id,
            status=RoyaltySettlement.Status.SETTLED,
        )
        .order_by("-settled_at", "-id")
        .first()
    )
    if last_settled and last_settled.settled_at:
        return last_settled.settled_at
    if getattr(project, "created_at", None):
        return project.created_at
    return timezone.now()


def has_prior_settlement(*, contract_id: int) -> bool:
    return RoyaltySettlement.objects.filter(
        contract_id=contract_id,
        status=RoyaltySettlement.Status.SETTLED,
    ).exists()


def get_open_settlement(*, contract_id: int) -> Optional[RoyaltySettlement]:
    return RoyaltySettlement.objects.filter(
        contract_id=contract_id,
        status=RoyaltySettlement.Status.OPEN,
    ).first()


def compute_period_actual_paid(*, product_id: int, period_start: datetime) -> int:
    """
    Paid-copy count for royalty period only (does not write ProductSalesStats).
    Same proportion rule as ProductSalesStats, scoped by invoice item created_at.
    """
    items = InvoiceItem.objects.filter(
        product_id=product_id,
        created_at__gte=period_start,
        invoice__main_invoice__isnull=True,
    )
    total_actual = 0
    for item in items:
        if item.total_price and item.total_price > 0:
            paid_proportion = float(item.paid_amount or 0) / float(item.total_price)
            total_actual += floor(paid_proportion * int(item.quantity or 0))
        elif item.is_paid:
            total_actual += int(item.quantity or 0)
    return int(total_actual)


def compute_period_paid_amount(*, product_id: int, period_start: datetime) -> Decimal:
    """
    Sum latest invoice_paid_amount for invoices that have this product,
    only counting payments created on/after period_start.
    """
    from sales.models import Invoice

    invoices = Invoice.objects.filter(
        invoiceitem__product_id=product_id,
    ).distinct()
    total = Decimal("0.00")
    for invoice in invoices:
        latest_payment = (
            Payment.objects.filter(
                invoice=invoice,
                created_at__gte=period_start,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if latest_payment and latest_payment.invoice_paid_amount:
            total += Decimal(str(latest_payment.invoice_paid_amount))
    return total.quantize(Decimal("0.01"))


def compute_retail_royalties_v1_invoice_paid(
    *,
    product_id: int,
    period_start: datetime,
    fixed_amount: Decimal,
    commission_percent: Decimal,
    prior_settled: bool,
) -> dict[str, Any]:
    """
    V1 BACKUP — previous retail_price formula (do not use in production path).

    Used invoice-level Payment.invoice_paid_amount, then:
    - prior settled: RA = sum_paid × %
    - first cycle: if sum_paid < advance → not eligible; else RA = (sum_paid − advance) × %
    """
    sum_paid_amount = compute_period_paid_amount(
        product_id=product_id,
        period_start=period_start,
    )
    commission_as_decimal = Decimal(str(commission_percent)) / Decimal("100")
    fixed_amount_value = Decimal(str(fixed_amount))

    if prior_settled:
        if sum_paid_amount <= 0:
            return {
                "eligible": False,
                "RA": None,
                "reason": (
                    f"No paid amount in current cycle since {period_start.isoformat()}"
                ),
                "details": {
                    "version": "v1_invoice_paid_backup",
                    "sum_paid_amount": float(sum_paid_amount),
                    "fixed_amount": float(fixed_amount_value),
                    "period_start": period_start.isoformat(),
                    "prior_settled": True,
                },
            }
        ra = (sum_paid_amount * commission_as_decimal).quantize(Decimal("0.01"))
        return {
            "eligible": True,
            "RA": ra,
            "reason": "",
            "details": {
                "version": "v1_invoice_paid_backup",
                "sum_paid_amount": float(sum_paid_amount),
                "fixed_amount": float(fixed_amount_value),
                "Z": float(sum_paid_amount),
                "period_start": period_start.isoformat(),
                "prior_settled": True,
                "commission_percent": float(commission_percent),
            },
        }

    if sum_paid_amount < fixed_amount_value:
        return {
            "eligible": False,
            "RA": None,
            "reason": (
                f"Sum of paid amount ({float(sum_paid_amount)}) is less than "
                f"advance payment ({float(fixed_amount_value)})"
            ),
            "details": {
                "version": "v1_invoice_paid_backup",
                "sum_paid_amount": float(sum_paid_amount),
                "fixed_amount": float(fixed_amount_value),
            },
        }

    z = sum_paid_amount - fixed_amount_value
    ra = (z * commission_as_decimal).quantize(Decimal("0.01"))
    z_float = float(z)
    z_out = int(z_float) if z_float.is_integer() else z_float
    return {
        "eligible": True,
        "RA": ra,
        "reason": "",
        "details": {
            "version": "v1_invoice_paid_backup",
            "sum_paid_amount": float(sum_paid_amount),
            "fixed_amount": float(fixed_amount_value),
            "Z": z_out,
            "commission_percent": float(commission_percent),
        },
    }


def compute_retail_royalties_from_paid_net_revenue(
    *,
    product_id: int,
    period_start: datetime,
    fixed_amount: Decimal,
    commission_percent: Decimal,
    prior_settled: bool,
) -> dict[str, Any]:
    """
    Current retail_price formula (matches book-sales paid net revenue).

    1. paid_net_revenue = BookAnalytics summary.net_revenue with payment_status=paid
       for invoices from period_start through today (same rules as /reports/book-sales).
    2. royalty_earned = paid_net_revenue × (commission_percent / 100)
    3. unrecovered_advance = 0 if prior_settled else fixed_amount
    4. amount_due = max(0, royalty_earned − unrecovered_advance)
    """
    from sales.services.book_analytics import BookAnalyticsFilters, BookAnalyticsService

    if timezone.is_aware(period_start):
        start_date = timezone.localtime(period_start).date()
    else:
        start_date = period_start.date()
    end_date = timezone.localdate()
    if end_date < start_date:
        end_date = start_date

    payload = BookAnalyticsService(
        product_id,
        BookAnalyticsFilters(
            start_date=start_date,
            end_date=end_date,
            payment_status="paid",
            page=1,
            page_size=1,
        ),
    ).build()

    paid_net_revenue = Decimal(str(payload["summary"]["net_revenue"] or 0)).quantize(
        Decimal("0.01")
    )
    commission_as_decimal = Decimal(str(commission_percent)) / Decimal("100")
    royalty_earned = (paid_net_revenue * commission_as_decimal).quantize(Decimal("0.01"))
    fixed_amount_value = Decimal(str(fixed_amount)).quantize(Decimal("0.01"))
    unrecovered_advance = (
        Decimal("0.00") if prior_settled else fixed_amount_value
    )
    amount_due = royalty_earned - unrecovered_advance
    if amount_due < 0:
        amount_due = Decimal("0.00")

    details = {
        "version": "v2_paid_net_revenue",
        "paid_net_revenue": float(paid_net_revenue),
        "royalty_earned": float(royalty_earned),
        "unrecovered_advance": float(unrecovered_advance),
        "amount_due": float(amount_due),
        "fixed_amount": float(fixed_amount_value),
        "commission_percent": float(commission_percent),
        "period_start": period_start.isoformat(),
        "period_start_date": start_date.isoformat(),
        "period_end_date": end_date.isoformat(),
        "prior_settled": prior_settled,
        "formula": "amount_due = max(0, paid_net_revenue × % − unrecovered_advance)",
    }

    if paid_net_revenue <= 0:
        return {
            "eligible": False,
            "RA": None,
            "reason": (
                f"No paid net revenue in current cycle "
                f"({start_date.isoformat()} → {end_date.isoformat()})"
            ),
            "details": details,
        }

    if amount_due <= 0:
        return {
            "eligible": False,
            "RA": None,
            "reason": (
                f"Royalty earned ({float(royalty_earned)}) does not exceed "
                f"unrecovered advance ({float(unrecovered_advance)})"
            ),
            "details": details,
        }

    return {
        "eligible": True,
        "RA": amount_due,
        "reason": "",
        "details": details,
    }


def compute_list_price_ra_v1_price_transactions(
    *,
    product,
    period_start: datetime,
    Y: Decimal,
    commission_as_decimal: Decimal,
) -> dict[str, Any]:
    """
    V1 BACKUP — previous list_price Step 4 only (do not use in production path).

    RA = Y × sum(printrun.price × invoice_item_count_in_edition_window) × (commission/100)
    Eligibility (X, Y) is unchanged and computed by the caller.
    """
    from datetime import datetime

    from inventory.models import PrintRun

    print_runs = list(
        PrintRun.objects.filter(product=product).order_by("published_at", "edition_number")
    )
    if not print_runs:
        raise ValueError(
            "No PrintRuns found for this product. PrintRuns are required for list_price calculation."
        )

    sum_price_transactions = Decimal("0")
    for i, print_run in enumerate(print_runs):
        start_date = timezone.make_aware(
            datetime.combine(print_run.published_at, datetime.min.time())
        )
        if i + 1 < len(print_runs):
            next_print_run = print_runs[i + 1]
            end_date = timezone.make_aware(
                datetime.combine(next_print_run.published_at, datetime.min.time())
            )
        else:
            end_date = timezone.now()

        range_start = start_date if start_date >= period_start else period_start
        if range_start >= end_date:
            transaction_count = 0
        else:
            transaction_count = InvoiceItem.objects.filter(
                product=product,
                created_at__gte=range_start,
                created_at__lt=end_date,
            ).count()

        sum_price_transactions += Decimal(str(print_run.price or 0)) * Decimal(
            str(transaction_count)
        )

    ra = (Decimal(str(Y)) * sum_price_transactions * commission_as_decimal).quantize(
        Decimal("0.01")
    )
    return {
        "RA": ra,
        "details": {
            "version": "v1_list_price_transactions_backup",
            "sum_price_transactions": float(sum_price_transactions),
            "formula": "RA = Y × sum(printrun.price × transaction_count) × %",
        },
    }


def compute_list_price_ra_from_paid_copies(
    *,
    Y: Decimal,
    book_price: Decimal,
    commission_percent: Decimal,
) -> dict[str, Any]:
    """
    Current list_price Step 4 (eligibility unchanged in the view).

    RA = paid eligible copies (Y) × book list price × (commission_percent / 100)
    """
    commission_as_decimal = Decimal(str(commission_percent)) / Decimal("100")
    price_value = Decimal(str(book_price))
    y_value = Decimal(str(Y))
    ra = (y_value * price_value * commission_as_decimal).quantize(Decimal("0.01"))
    return {
        "RA": ra,
        "details": {
            "version": "v2_list_price_paid_copies",
            "Y": float(y_value) if not float(y_value).is_integer() else int(y_value),
            "book_price": float(price_value),
            "commission_percent": float(commission_percent),
            "formula": "RA = Y × book_price × (commission_percent / 100)",
        },
    }


@transaction.atomic
def upsert_open_royalty_settlement(
    *,
    contract,
    project,
    product,
    user=None,
    eligible: bool,
    amount_due: Optional[Decimal | float | int] = None,
    reason: str = "",
    details: Optional[dict[str, Any]] = None,
) -> RoyaltySettlement:
    """
    Create or update the single open RoyaltySettlement for a contract.
    """
    now = timezone.now()
    amount = Decimal(str(amount_due if amount_due is not None else 0)).quantize(
        Decimal("0.01")
    )

    open_row = (
        RoyaltySettlement.objects.select_for_update()
        .filter(contract_id=contract.id, status=RoyaltySettlement.Status.OPEN)
        .first()
    )

    if open_row is None:
        open_row = RoyaltySettlement(
            contract=contract,
            project=project,
            product=product,
            period_start=resolve_period_start(contract=contract, project=project),
            status=RoyaltySettlement.Status.OPEN,
            currency="USD",
            created_by=user,
        )

    open_row.project = project
    open_row.product = product
    open_row.period_end = now
    open_row.amount_due = amount
    open_row.eligible = bool(eligible)
    open_row.reason = reason or ""
    open_row.calculation_details = details
    open_row.calculated_at = now
    open_row.calculated_by = user
    open_row.updated_by = user
    open_row.status = RoyaltySettlement.Status.OPEN
    open_row.save()
    return open_row


@transaction.atomic
def settle_open_royalty_settlement(
    *,
    settlement_id: int,
    user=None,
    amount_paid: Optional[Decimal | float | int] = None,
) -> dict[str, RoyaltySettlement]:
    """
    Mark open settlement as settled and create the next open cycle row (amount 0).
    """
    now = timezone.now()
    row = (
        RoyaltySettlement.objects.select_for_update()
        .select_related("contract", "project", "product")
        .filter(id=settlement_id)
        .first()
    )
    if row is None:
        raise serializers.ValidationError({"settlement_id": "Settlement not found"})
    if row.status != RoyaltySettlement.Status.OPEN:
        raise serializers.ValidationError(
            {"status": f"Only open settlements can be settled (current={row.status})"}
        )
    if not row.eligible or Decimal(str(row.amount_due or 0)) <= 0:
        raise serializers.ValidationError(
            {"amount_due": "Cannot settle: no positive eligible amount due"}
        )

    gate = settle_gate_for_contract(contract=row.contract, project=row.project)
    if not gate.get("can_settle"):
        raise serializers.ValidationError(
            {"settle_gate": gate.get("reason") or "Settlement not yet allowed"}
        )

    paid = (
        Decimal(str(amount_paid)).quantize(Decimal("0.01"))
        if amount_paid is not None
        else Decimal(str(row.amount_due)).quantize(Decimal("0.01"))
    )

    row.status = RoyaltySettlement.Status.SETTLED
    row.amount_paid = paid
    row.settled_at = now
    row.settled_by = user
    row.period_end = now
    row.updated_by = user
    row.open_contract_id = None
    row.save()

    next_open = RoyaltySettlement(
        contract=row.contract,
        project=row.project,
        product=row.product,
        period_start=now,
        period_end=None,
        amount_due=Decimal("0.00"),
        currency=row.currency or "USD",
        status=RoyaltySettlement.Status.OPEN,
        eligible=False,
        reason="New cycle after settlement — run Calculate when ready",
        calculation_details=None,
        created_by=user,
        updated_by=user,
    )
    next_open.save()

    return {"settled": row, "next_open": next_open}


def settlement_payload(row: RoyaltySettlement, *, include_titles: bool = False) -> dict[str, Any]:
    gate = None
    if row.contract_id and row.project_id:
        try:
            gate = settle_gate_for_contract(contract=row.contract, project=row.project)
        except Exception:
            gate = None

    settled_by_name = None
    if getattr(row, "settled_by_id", None) and row.settled_by:
        full = f"{row.settled_by.first_name or ''} {row.settled_by.last_name or ''}".strip()
        settled_by_name = full or row.settled_by.username

    payload: dict[str, Any] = {
        "id": row.id,
        "status": row.status,
        "contract_id": row.contract_id,
        "project_id": row.project_id,
        "product_id": row.product_id,
        "period_start": row.period_start.isoformat() if row.period_start else None,
        "period_end": row.period_end.isoformat() if row.period_end else None,
        "amount_due": float(row.amount_due or 0),
        "amount_paid": float(row.amount_paid) if row.amount_paid is not None else None,
        "currency": row.currency,
        "eligible": row.eligible,
        "reason": row.reason or None,
        "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
        "settled_at": row.settled_at.isoformat() if row.settled_at else None,
        "settled_by_name": settled_by_name,
        "settle_gate": gate,
    }

    if include_titles:
        contract = row.contract if row.contract_id else None
        project = row.project if row.project_id else None
        product = row.product if row.product_id else None
        payload["contract_title"] = (contract.title if contract else None) or None
        payload["project_title_ar"] = (project.title_ar if project else None) or None
        payload["project_title_en"] = (project.title_original if project else None) or None
        payload["product_title_ar"] = (product.title_ar if product else None) or None
        payload["product_title_en"] = (product.title_en if product else None) or None
        payload["product_isbn"] = (product.isbn if product else None) or None

    return payload


def list_settlements_for_contract(
    *,
    contract_id: int,
    status: str | None = None,
) -> list[RoyaltySettlement]:
    qs = (
        RoyaltySettlement.objects.filter(contract_id=contract_id)
        .select_related("contract", "project", "product", "settled_by")
        .order_by("-settled_at", "-id")
    )
    if status:
        qs = qs.filter(status=status)
    return list(qs)
