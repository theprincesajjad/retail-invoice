"""Generate receipt PDF bytes for email attachment."""

import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from models import Invoice, InvoiceItem
from receipt_builder import build_receipt_text
from database import get_all_settings


def build_receipt_pdf(invoice: Invoice, items: list[InvoiceItem]) -> bytes:
    settings = get_all_settings()
    text = build_receipt_text(invoice, items, settings)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    biz_name = settings.get("business_name", "My Business")
    y = height - inch * 0.75
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, biz_name)
    y -= 24
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, f"Receipt {invoice.invoice_number}")
    y -= 36

    c.setFont("Courier", 12)
    for line in text.splitlines():
        if y < inch:
            c.showPage()
            c.setFont("Courier", 12)
            y = height - inch
        c.drawString(inch * 0.75, y, line)
        y -= 16
    c.save()
    return buffer.getvalue()
