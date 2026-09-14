"""Accounting sales report PDF for a date range."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from database import get_all_settings
from models import Invoice
from utils import format_currency


def aggregate_monthly_totals(invoices: list[Invoice]) -> list[dict[str, Any]]:
    """Group non-voided invoices by calendar month.

    Returns rows sorted oldest→newest with keys:
    month_key (YYYY-MM), month_label (e.g. Sep 2026), invoices, revenue, tax, subtotal.
    """
    buckets: dict[str, dict[str, Any]] = {}
    for inv in invoices:
        if int(getattr(inv, "voided", 0) or 0):
            continue
        created = (inv.created_at or "")[:10]
        try:
            dt = datetime.strptime(created, "%Y-%m-%d")
        except ValueError:
            continue
        key = dt.strftime("%Y-%m")
        if key not in buckets:
            buckets[key] = {
                "month_key": key,
                "month_label": dt.strftime("%b %Y"),
                "invoices": 0,
                "revenue": 0.0,
                "tax": 0.0,
                "subtotal": 0.0,
            }
        row = buckets[key]
        row["invoices"] += 1
        row["revenue"] += float(inv.total or 0)
        row["tax"] += float(inv.tax_amount or 0)
        row["subtotal"] += float(inv.subtotal or 0)
    return [buckets[k] for k in sorted(buckets.keys())]


def build_monthly_totals_pdf(
    invoices: list[Invoice],
    *,
    period_label: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    settings: dict | None = None,
) -> bytes:
    """PDF of monthly rollups only — invoice count, revenue, tax, plus grand total."""
    settings = settings or get_all_settings()
    biz = (settings.get("business_name") or "My Business").strip()
    rows = aggregate_monthly_totals(invoices)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin_x = 0.6 * inch
    margin_top = 0.65 * inch
    margin_bottom = 0.6 * inch
    usable = width - 2 * margin_x
    y = height - margin_top
    today = datetime.now().strftime("%b %d, %Y")

    def ensure(need: float):
        nonlocal y
        if y - need < margin_bottom:
            c.showPage()
            y = height - margin_top

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, biz)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Monthly sales totals")
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    range_bits = [period_label] if period_label else []
    if start_date:
        range_bits.append(f"From {start_date[:10]}")
    if end_date:
        range_bits.append(f"to {end_date[:10]}")
    c.drawString(
        margin_x,
        y,
        f"Printed {today}  ·  {' · '.join(range_bits) if range_bits else 'Selected period'}",
    )
    c.setFillColorRGB(0, 0, 0)
    y -= 20

    if not rows:
        c.setFont("Helvetica", 11)
        c.drawString(margin_x, y, "No sales in this period.")
        c.save()
        return buffer.getvalue()

    col_month = margin_x
    col_count = margin_x + 2.2 * inch
    col_rev = margin_x + 3.6 * inch
    col_tax = margin_x + 5.2 * inch
    col_right = margin_x + usable

    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(col_month, y, "Month")
    c.drawString(col_count, y, "Invoices")
    c.drawString(col_rev, y, "Revenue")
    c.drawString(col_tax, y, "Tax")
    c.setFillColorRGB(0, 0, 0)
    y -= 6
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.line(margin_x, y, col_right, y)
    y -= 14

    total_inv = 0
    total_rev = 0.0
    total_tax = 0.0
    for row in rows:
        ensure(14)
        c.setFont("Helvetica", 10)
        c.drawString(col_month, y, row["month_label"])
        c.drawString(col_count, y, str(row["invoices"]))
        c.drawString(col_rev, y, format_currency(row["revenue"]))
        c.drawString(col_tax, y, format_currency(row["tax"]))
        total_inv += row["invoices"]
        total_rev += row["revenue"]
        total_tax += row["tax"]
        y -= 14

    y -= 6
    ensure(28)
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.line(margin_x, y + 10, col_right, y + 10)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(col_month, y, "Combined total")
    c.drawString(col_count, y, str(total_inv))
    c.drawString(col_rev, y, format_currency(total_rev))
    c.drawString(col_tax, y, format_currency(total_tax))
    y -= 16
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    month_word = "month" if len(rows) == 1 else "months"
    c.drawString(
        margin_x,
        y,
        f"{len(rows)} {month_word}  ·  voided sales excluded",
    )

    c.save()
    return buffer.getvalue()


def build_sales_report_pdf(
    invoices: list[Invoice],
    *,
    period_label: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    settings: dict | None = None,
) -> bytes:
    settings = settings or get_all_settings()
    biz = (settings.get("business_name") or "My Business").strip()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin_x = 0.6 * inch
    margin_top = 0.65 * inch
    margin_bottom = 0.6 * inch
    usable = width - 2 * margin_x
    y = height - margin_top
    today = datetime.now().strftime("%b %d, %Y")

    def ensure(need: float):
        nonlocal y
        if y - need < margin_bottom:
            c.showPage()
            y = height - margin_top

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, biz)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Sales report — accounting")
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    range_bits = [period_label] if period_label else []
    if start_date:
        range_bits.append(f"From {start_date[:10]}")
    if end_date:
        range_bits.append(f"to {end_date[:10]}")
    c.drawString(margin_x, y, f"Printed {today}  ·  {' · '.join(range_bits) if range_bits else 'All listed sales'}")
    c.setFillColorRGB(0, 0, 0)
    y -= 18

    total_sales = sum(inv.total for inv in invoices)
    total_tax = sum(inv.tax_amount for inv in invoices)
    total_sub = sum(inv.subtotal for inv in invoices)
    count = len(invoices)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, f"Sales: {count}")
    c.drawString(margin_x + 1.4 * inch, y, f"Subtotal: {format_currency(total_sub)}")
    c.drawString(margin_x + 3.4 * inch, y, f"Tax: {format_currency(total_tax)}")
    c.drawRightString(margin_x + usable, y, f"Total: {format_currency(total_sales)}")
    y -= 10
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.line(margin_x, y, margin_x + usable, y)
    y -= 16

    col_num = margin_x
    col_date = margin_x + 1.15 * inch
    col_cust = margin_x + 2.35 * inch
    col_pay = margin_x + 4.35 * inch
    col_total = margin_x + usable

    if not invoices:
        c.setFont("Helvetica", 11)
        c.drawString(margin_x, y, "No sales in this period.")
        c.save()
        return buffer.getvalue()

    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(col_num, y, "Receipt #")
    c.drawString(col_date, y, "Date")
    c.drawString(col_cust, y, "Customer")
    c.drawString(col_pay, y, "Paid by")
    c.drawRightString(col_total, y, "Total")
    c.setFillColorRGB(0, 0, 0)
    y -= 6
    c.line(margin_x, y, margin_x + usable, y)
    y -= 12

    for inv in invoices:
        ensure(14)
        c.setFont("Helvetica", 9)
        c.drawString(col_num, y, (inv.invoice_number or "")[:14])
        c.drawString(col_date, y, (inv.created_at or "")[:16])
        c.drawString(col_cust, y, (inv.customer_name or "Walk-in")[:28])
        c.drawString(col_pay, y, (inv.payment_method or "")[:10])
        c.drawRightString(col_total, y, format_currency(inv.total))
        y -= 12

    y -= 8
    ensure(24)
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.line(margin_x, y + 8, margin_x + usable, y + 8)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, f"{count} sales")
    c.drawRightString(col_total, y, format_currency(total_sales))
    y -= 14
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(margin_x, y, f"Tax collected {format_currency(total_tax)}  ·  Subtotal {format_currency(total_sub)}")

    c.save()
    return buffer.getvalue()
