"""Accounting sales report PDF for a date range."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from database import get_all_settings
from models import Invoice
from utils import format_currency


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
