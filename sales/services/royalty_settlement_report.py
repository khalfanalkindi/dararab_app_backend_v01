"""
Simple bilingual royalty settlement reports (PDF + Excel).

Generated on the backend so the royalties page only downloads blobs.
Preamble text is intentionally minimal until the official wording arrives.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import arabic_reshaper
from bidi.algorithm import get_display
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from sales.models import RoyaltySettlement

ASSETS_DIR = Path(__file__).resolve().parent.parent / "report_assets"
LOGO_PATH = ASSETS_DIR / "dararab-logo-1.png"
FONTS_DIR = ASSETS_DIR / "fonts"

_FONTS_REGISTERED = False

# Placeholder until official preamble is provided by the client.
PREAMBLE_EN = (
    "This is a provisional royalty settlement summary. "
    "Official preamble text will be inserted here when received."
)
PREAMBLE_AR = (
    "هذا ملخص تسوية إتاوات مؤقت. "
    "سيُستبدل نص الديباجة الرسمي هنا عند استلامه."
)


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(
        TTFont("NotoSans", str(FONTS_DIR / "NotoSans-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("NotoSans-Bold", str(FONTS_DIR / "NotoSans-Bold.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("NotoNaskhArabic", str(FONTS_DIR / "NotoNaskhArabic-Regular.ttf"))
    )
    _FONTS_REGISTERED = True


def _ar(text: str) -> str:
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))


def _fmt_dt(value: Optional[datetime]) -> str:
    if not value:
        return "—"
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%Y-%m-%d %H:%M")


def _fmt_money(amount: Any, currency: str = "USD") -> str:
    try:
        n = float(amount or 0)
    except (TypeError, ValueError):
        n = 0.0
    return f"{n:,.2f} {currency or 'USD'}"


def _user_display(user) -> str:
    if not user:
        return "—"
    full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return full or getattr(user, "username", None) or str(user)


COMPANY_NAME = "DarArab for Publishing & Translation"
COMPANY_ADDRESS = "Seeb, Muscat, Sultanate of Oman"
COMPANY_TEL = "+96871523542"
COMPANY_EMAIL = "info@dararab.co.uk"
COMPANY_WEB = "dararab.co.uk"


def report_context(row: RoyaltySettlement) -> dict[str, Any]:
    """Flatten settlement + related titles for PDF/Excel builders."""
    from django.db.models import Sum

    from inventory.models import Inventory

    contract = row.contract
    project = row.project
    product = row.product
    details = row.calculation_details if isinstance(row.calculation_details, dict) else {}
    author = None
    rights_owner = None
    if product is not None:
        author = product.author
        rights_owner = product.rights_owner
    if author is None and project is not None:
        author = project.author
    if rights_owner is None and project is not None:
        rights_owner = project.rights_owner
    stock_remaining = (
        Inventory.objects.filter(product_id=row.product_id).aggregate(total=Sum("quantity"))[
            "total"
        ]
        or 0
    )

    return {
        "id": row.id,
        "status": row.status,
        "currency": row.currency or "USD",
        "amount_due": float(row.amount_due or 0),
        "amount_paid": float(row.amount_paid) if row.amount_paid is not None else None,
        "eligible": bool(row.eligible),
        "reason": row.reason or "",
        "period_start": row.period_start,
        "period_end": row.period_end,
        "calculated_at": row.calculated_at,
        "settled_at": row.settled_at,
        "contract_id": row.contract_id,
        "contract_title": (contract.title if contract else None) or f"Contract #{row.contract_id}",
        "project_id": row.project_id,
        "project_title_ar": (project.title_ar if project else None) or "",
        "project_title_en": (project.title_original if project else None) or "",
        "product_id": row.product_id,
        "product_title_ar": (product.title_ar if product else None) or "",
        "product_title_en": (product.title_en if product else None) or "",
        "product_isbn": (product.isbn if product else None) or "",
        "settled_by": _user_display(row.settled_by),
        "calculated_by": _user_display(row.calculated_by),
        "details": details,
        "royalties_type": details.get("royalties_type") or "",
        "commission_percent": details.get("commission_percent"),
        "Y": details.get("Y"),
        "X": details.get("X"),
        "actual_paid": details.get("actual_paid"),
        "author_name": str(author) if author else "—",
        "rights_owner_name": str(rights_owner) if rights_owner else "—",
        "stock_remaining": int(stock_remaining),
        "book_title": (
            (product.title_en if product else None)
            or (product.title_ar if product else None)
            or (project.title_original if project else None)
            or (project.title_ar if project else None)
            or "—"
        ),
    }


def build_excel_bytes(row: RoyaltySettlement) -> bytes:
    """
    Accounting-friendly one-row summary — no calculation detail dump.
    """
    ctx = report_context(row)
    wb = Workbook()
    ws = wb.active
    ws.title = "Royalty Settlement"

    headers = [
        "Settlement ID",
        "Status",
        "Contract ID",
        "Contract Title",
        "Project ID",
        "Project (AR)",
        "Project (EN)",
        "Product ID",
        "Product (AR)",
        "Product (EN)",
        "ISBN",
        "Period Start",
        "Period End",
        "Amount Due",
        "Amount Paid",
        "Currency",
        "Settled At",
        "Settled By",
    ]
    values = [
        ctx["id"],
        ctx["status"],
        ctx["contract_id"],
        ctx["contract_title"],
        ctx["project_id"],
        ctx["project_title_ar"],
        ctx["project_title_en"],
        ctx["product_id"],
        ctx["product_title_ar"],
        ctx["product_title_en"],
        ctx["product_isbn"],
        _fmt_dt(ctx["period_start"]),
        _fmt_dt(ctx["period_end"]),
        ctx["amount_due"],
        ctx["amount_paid"] if ctx["amount_paid"] is not None else "",
        ctx["currency"],
        _fmt_dt(ctx["settled_at"]),
        ctx["settled_by"],
    ]

    ws.append(headers)
    ws.append(values)

    header_font = Font(bold=True)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[cell.column_letter].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_pdf_bytes(row: RoyaltySettlement) -> bytes:
    """
    A4 sales and royalty statement.

    Header matches the sales invoice: logo plus Seeb address, telephone,
    email, and website. Body follows the annual statement layout.
    """
    _register_fonts()
    ctx = report_context(row)
    details = ctx["details"] if isinstance(ctx["details"], dict) else {}

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 16 * mm
    y = height - margin

    def ensure(space: float) -> None:
        nonlocal y
        if y < margin + space:
            c.showPage()
            y = height - margin
            _register_fonts()

    def rule() -> None:
        nonlocal y
        c.setStrokeColor(colors.HexColor("#222222"))
        c.setLineWidth(0.6)
        c.line(margin, y, width - margin, y)
        y -= 6 * mm

    def section(title: str) -> None:
        nonlocal y
        ensure(16 * mm)
        c.setFillColor(colors.black)
        c.setFont("NotoSans-Bold", 10)
        c.drawString(margin, y, title)
        y -= 2.5 * mm
        c.setStrokeColor(colors.HexColor("#222222"))
        c.setLineWidth(0.8)
        c.line(margin, y, width - margin, y)
        y -= 6 * mm

    def pair(label: str, value: str, bold: bool = False) -> None:
        nonlocal y
        ensure(8 * mm)
        c.setFillColor(colors.black)
        c.setFont("NotoSans", 9)
        c.drawString(margin, y, label)
        c.setFont("NotoSans-Bold" if bold else "NotoSans", 9)
        text = value or "—"
        if len(text) > 70:
            text = text[:67] + "..."
        c.drawRightString(width - margin, y, text)
        y -= 5.2 * mm

    if LOGO_PATH.exists():
        logo_w = 28 * mm
        logo_h = 16 * mm
        c.drawImage(
            str(LOGO_PATH),
            (width - logo_w) / 2,
            y - logo_h,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= logo_h + 3 * mm

    c.setFillColor(colors.black)
    c.setFont("NotoSans-Bold", 12)
    c.drawCentredString(width / 2, y, COMPANY_NAME)
    y -= 5 * mm
    c.setFont("NotoSans", 8)
    for line in (
        COMPANY_ADDRESS,
        f"Tel: {COMPANY_TEL}",
        f"Email: {COMPANY_EMAIL}",
        f"Web: {COMPANY_WEB}",
    ):
        c.drawCentredString(width / 2, y, line)
        y -= 4 * mm
    y -= 2 * mm
    rule()

    c.setFont("NotoSans-Bold", 13)
    c.drawCentredString(width / 2, y, "ANNUAL STATEMENT")
    y -= 5.5 * mm
    c.setFont("NotoSans", 10)
    c.drawCentredString(width / 2, y, "Sales and royalty statement")
    y -= 7 * mm

    period = details.get("period_start_date") or _fmt_dt(ctx["period_start"])
    period_end = details.get("period_end_date") or _fmt_dt(ctx["period_end"])
    pair("BOOK TITLE", ctx["book_title"], bold=True)
    pair("AUTHOR / RIGHTS OWNER", f"{ctx['author_name']} / {ctx['rights_owner_name']}")
    pair("REPORTING PERIOD", f"{period}  —  {period_end}")
    pair("CURRENCY", ctx["currency"] or "USD")
    y -= 2 * mm

    copies_paid = int(details.get("copies_paid") or 0)
    copies_complimentary = int(details.get("copies_complimentary") or 0)
    author_complimentary = int(details.get("author_copies_complimentary") or 0)
    author_other = int(details.get("author_copies_paid") or 0)
    gift_copies = max(0, copies_complimentary - author_complimentary)
    author_copies = author_complimentary + author_other
    copies_sold = max(0, copies_paid - author_other)
    damaged = int(details.get("damaged_copies") or 0)
    lost = int(details.get("lost_copies") or 0)
    censorship = int(details.get("censorship_copies") or 0)
    excluded_total = gift_copies + author_copies + damaged + lost + censorship

    section("SALES AND STOCK COPIES")
    pair("Copies sold during the period", str(copies_sold))
    pair("Complimentary copies - gifts", str(gift_copies))
    pair("Author copies (DARARAB, any discount)", str(author_copies))
    pair("Written off - damaged", str(damaged))
    pair("Written off - lost", str(lost))
    pair("Written off - withdrawn by censorship", str(censorship))
    pair("Total complimentary and written-off copies", str(excluded_total), bold=True)
    pair("Copies remaining in stock", str(ctx["stock_remaining"]))
    y -= 2 * mm

    section("ROYALTY CALCULATION")
    pair(
        "Sales income after all discounts",
        _fmt_money(details.get("paid_net_revenue"), ctx["currency"]),
    )
    pair(
        "Author copies excluded (DARARAB)",
        _fmt_money(details.get("author_paid_net_revenue"), ctx["currency"]),
    )
    pair(
        "Written-off value",
        _fmt_money(details.get("writeoff_value"), ctx["currency"]),
    )
    pair(
        "Royalty basis",
        _fmt_money(details.get("royalty_base"), ctx["currency"]),
        bold=True,
    )
    cover = details.get("book_price")
    pair(
        "Cover price per copy (if applicable)",
        _fmt_money(cover, ctx["currency"]) if cover is not None else "—",
    )
    percent = details.get("commission_percent")
    pair("Royalty percentage (%)", f"{percent}%" if percent is not None else "—")
    pair(
        "Unrecovered advance",
        _fmt_money(details.get("unrecovered_advance"), ctx["currency"]),
    )
    y -= 2 * mm

    section("ROYALTIES EARNED")
    earned = details.get("royalty_earned")
    pair(
        "Royalty earned",
        _fmt_money(earned if earned is not None else ctx["amount_due"], ctx["currency"]),
    )
    pair(
        "Amount due",
        _fmt_money(ctx["amount_due"], ctx["currency"]),
        bold=True,
    )
    if not ctx["eligible"] and ctx["reason"]:
        y -= 1 * mm
        c.setFont("NotoSans", 8)
        for line in _wrap_text(ctx["reason"], 100):
            ensure(6 * mm)
            c.drawString(margin, y, line)
            y -= 4 * mm

    y -= 4 * mm
    c.setFont("NotoSans", 8)
    for line in (
        "Sales figures are net of returns. Complimentary and written-off copies earn no royalties.",
        "Author copies recorded under contact person DARARAB are excluded once, at any discount.",
        "Thank you for entrusting your work to DarArab.",
        "Please contact us if you would like any clarification regarding this statement.",
    ):
        ensure(6 * mm)
        c.drawString(margin, y, line)
        y -= 4.2 * mm

    c.setFont("NotoSans", 8)
    c.drawString(margin, 12 * mm, COMPANY_EMAIL)
    c.drawRightString(width - margin, 12 * mm, "Private and confidential")

    c.save()
    return buf.getvalue()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def report_filename(row: RoyaltySettlement, fmt: str) -> str:
    ext = "pdf" if fmt == "pdf" else "xlsx"
    return f"royalty-settlement-{row.id}.{ext}"
