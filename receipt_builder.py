"""Shared receipt text formatting for print, preview, and email."""

from database import get_all_settings
from models import Invoice, InvoiceItem
from utils import format_currency


def get_printer_width_chars(width_setting: str) -> int:
    return 32 if width_setting == "58mm" else 48


def build_receipt_text(invoice: Invoice, items: list[InvoiceItem]) -> str:
    settings = get_all_settings()
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    rule = "-" * width
    lines: list[str] = []

    def center(text: str) -> str:
        text = text.strip()
        if len(text) >= width:
            return text[:width]
        pad = (width - len(text)) // 2
        return " " * pad + text

    lines.append(center(settings.get("business_name", "My Business")))
    lines.append(center(settings.get("business_address", "")))
    lines.append(center(f"Tel: {settings.get('business_phone', '')}"))
    lines.append(center(f"GST/HST#: {settings.get('gst_number', '')}"))
    lines.append(rule)
    lines.append(f"Invoice: {invoice.invoice_number}")
    lines.append(f"Date: {invoice.created_at or 'Just now'}")
    if invoice.customer_name:
        lines.append(f"Customer: {invoice.customer_name}")
    if invoice.customer_phone:
        lines.append(f"Phone: {invoice.customer_phone}")
    lines.append(rule)

    for item in items:
        line_total_str = format_currency(item.line_total)
        desc = item.description
        if item.qty > 1:
            desc = f"{item.qty}x {desc}"
        max_desc = width - len(line_total_str) - 1
        if len(desc) > max_desc:
            desc = desc[: max_desc - 3] + "..."
        spaces = width - len(desc) - len(line_total_str)
        lines.append(f"{desc}{' ' * spaces}{line_total_str}")
        if item.serial_number:
            lines.append(f"  S/N: {item.serial_number}")

    lines.append(rule)
    lines.append(f"{'Subtotal:':<{width - 10}}{format_currency(invoice.subtotal):>10}")
    if getattr(invoice, "discount_amount", 0) and invoice.discount_amount > 0:
        disc = format_currency(invoice.discount_amount)
        if invoice.discount_type == "percent":
            lines.append(f"{'Discount (' + str(invoice.discount_value).rstrip('0').rstrip('.') + '%):':<{width - 10}}{disc:>10}")
        else:
            lines.append(f"{'Discount:':<{width - 10}}{disc:>10}")
    tax_pct = int(invoice.tax_rate * 100)
    lines.append(f"{f'HST ({tax_pct}%):':<{width - 10}}{format_currency(invoice.tax_amount):>10}")
    lines.append(f"{'TOTAL:':<{width - 10}}{format_currency(invoice.total):>10}")
    lines.append(f"{'Payment:':<{width - 10}}{invoice.payment_method:>10}")
    lines.append(rule)
    lines.append(center("Thank you!"))
    lines.append(center("Please come again"))
    lines.append("")

    return "\n".join(lines)
