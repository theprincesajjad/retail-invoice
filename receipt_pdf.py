"""Generate receipt PDF bytes for email attachment."""

import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from models import Invoice, InvoiceItem
from receipt_builder import build_receipt_text


def build_receipt_pdf(invoice: Invoice, items: list[InvoiceItem]) -> bytes:
    text = build_receipt_text(invoice, items)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch
    c.setFont("Courier", 10)
    for line in text.splitlines():
        if y < inch:
            c.showPage()
            c.setFont("Courier", 10)
            y = height - inch
        c.drawString(inch, y, line)
        y -= 13
    c.save()
    return buffer.getvalue()
