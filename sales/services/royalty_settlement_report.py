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


def report_context(row: RoyaltySettlement) -> dict[str, Any]:
    """Flatten settlement + related titles for PDF/Excel builders."""
    contract = row.contract
    project = row.project
    product = row.product
    details = row.calculation_details if isinstance(row.calculation_details, dict) else {}

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
    Simple A4 bilingual PDF: logo, placeholder preamble, summary, signatures.
    """
    _register_fonts()
    ctx = report_context(row)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    y = height - margin

    # Logo
    if LOGO_PATH.exists():
        logo_w = 42 * mm
        logo_h = 18 * mm
        c.drawImage(
            str(LOGO_PATH),
            (width - logo_w) / 2,
            y - logo_h,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= logo_h + 6 * mm
    else:
        y -= 4 * mm

    # Brand / title
    c.setFont("NotoSans-Bold", 14)
    c.drawCentredString(width / 2, y, "DarArab Publishing")
    y -= 7 * mm
    c.setFont("NotoNaskhArabic", 13)
    c.drawCentredString(width / 2, y, _ar("دار عرب للنشر"))
    y -= 9 * mm

    c.setFont("NotoSans-Bold", 12)
    c.drawCentredString(width / 2, y, "Royalty Settlement Report")
    y -= 6 * mm
    c.setFont("NotoNaskhArabic", 12)
    c.drawCentredString(width / 2, y, _ar("تقرير تسوية الإتاوات"))
    y -= 8 * mm

    # Divider
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.8)
    c.line(margin, y, width - margin, y)
    y -= 8 * mm

    # Preamble (placeholder)
    c.setFont("NotoSans", 8)
    for line in _wrap_text(PREAMBLE_EN, 95):
        c.drawString(margin, y, line)
        y -= 4 * mm
    y -= 1 * mm
    c.setFont("NotoNaskhArabic", 9)
    for line in _wrap_text(PREAMBLE_AR, 70):
        c.drawRightString(width - margin, y, _ar(line))
        y -= 5 * mm
    y -= 4 * mm

    # Summary rows: (en_label, ar_label, value) where value is str or (en, ar)
    rows: list[tuple[str, str, Any]] = [
        ("Settlement ID", "رقم التسوية", f"#{ctx['id']}"),
        ("Status", "الحالة", ctx["status"]),
        ("Contract", "العقد", f"#{ctx['contract_id']} — {ctx['contract_title']}"),
        (
            "Project",
            "المشروع",
            (ctx["project_title_en"] or "—", ctx["project_title_ar"] or ""),
        ),
        (
            "Product",
            "المنتج",
            (ctx["product_title_en"] or "—", ctx["product_title_ar"] or ""),
        ),
        ("ISBN", "ردمك", ctx["product_isbn"] or "—"),
        ("Period start", "بداية الفترة", _fmt_dt(ctx["period_start"])),
        ("Period end", "نهاية الفترة", _fmt_dt(ctx["period_end"])),
        ("Amount due", "المبلغ المستحق", _fmt_money(ctx["amount_due"], ctx["currency"])),
        (
            "Amount paid",
            "المبلغ المدفوع",
            _fmt_money(ctx["amount_paid"], ctx["currency"])
            if ctx["amount_paid"] is not None
            else "—",
        ),
        ("Settled at", "تاريخ التسوية", _fmt_dt(ctx["settled_at"])),
        ("Settled by", "تم بواسطة", ctx["settled_by"]),
    ]

    # Light calc summary (not a full dump)
    if ctx.get("Y") is not None:
        rows.append(("Eligible copies (Y)", "النسخ المؤهلة (Y)", str(ctx["Y"])))
    if ctx.get("commission_percent") is not None:
        rows.append(
            ("Commission %", "نسبة العمولة", f"{ctx['commission_percent']}%")
        )
    if ctx.get("royalties_type"):
        rows.append(("Royalty type", "نوع الإتاوة", str(ctx["royalties_type"])))

    for en_label, ar_label, value in rows:
        if y < 55 * mm:
            c.showPage()
            y = height - margin
            _register_fonts()

        c.setFont("NotoSans", 8)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(margin, y, en_label)
        c.setFont("NotoNaskhArabic", 8)
        c.drawRightString(width - margin, y, _ar(ar_label))
        y -= 4.2 * mm

        c.setFillColor(colors.black)
        en_val, ar_val = value if isinstance(value, tuple) else (str(value), "")
        en_val = str(en_val or "—")
        if len(en_val) > 110:
            en_val = en_val[:107] + "..."
        c.setFont("NotoSans", 9)
        c.drawString(margin + 2 * mm, y, en_val)
        y -= 4.5 * mm
        if ar_val:
            c.setFont("NotoNaskhArabic", 9)
            c.drawRightString(width - margin - 2 * mm, y, _ar(str(ar_val)))
            y -= 5.5 * mm
        else:
            y -= 2 * mm

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#333333"))
    c.line(margin, y, width - margin, y)
    y -= 12 * mm

    # Signature blocks
    box_w = (width - 2 * margin - 10 * mm) / 2
    box_h = 28 * mm
    left_x = margin
    right_x = margin + box_w + 10 * mm

    def _sig_box(x: float, title_en: str, title_ar: str) -> None:
        c.setStrokeColor(colors.HexColor("#888888"))
        c.setLineWidth(0.6)
        c.rect(x, y - box_h, box_w, box_h, stroke=1, fill=0)
        c.setFillColor(colors.black)
        c.setFont("NotoSans-Bold", 8)
        c.drawString(x + 3 * mm, y - 5 * mm, title_en)
        c.setFont("NotoNaskhArabic", 8)
        c.drawRightString(x + box_w - 3 * mm, y - 5 * mm, _ar(title_ar))
        c.setFont("NotoSans", 7)
        c.drawString(x + 3 * mm, y - box_h + 10 * mm, "Name / الاسم: ____________________")
        c.drawString(x + 3 * mm, y - box_h + 5 * mm, "Signature / التوقيع: ______________")
        c.drawString(x + 3 * mm, y - box_h + 1.5 * mm, "Date / التاريخ: ____________________")

    _sig_box(left_x, "Prepared by", "أعدّه")
    _sig_box(right_x, "Approved by", "اعتمد")

    # Footer
    c.setFont("NotoSans", 7)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawCentredString(
        width / 2,
        10 * mm,
        f"Generated {timezone.localtime().strftime('%Y-%m-%d %H:%M')} · Settlement #{ctx['id']}",
    )

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
