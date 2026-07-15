"""Shared receipt layout for print preview, thermal print, and email.

Designed for fixed-width thermal fonts (48 chars @ 80mm, 32 @ 58mm).
Column widths always sum to the paper width so headers never wrap.
"""

from __future__ import annotations

import os
from datetime import datetime

from database import get_all_settings
from models import Invoice, InvoiceItem
from utils import format_currency


def get_printer_width_chars(width_setting: str) -> int:
    return 32 if width_setting == "58mm" else 48


def _on(settings: dict, key: str, default: str = "1") -> bool:
    return str(settings.get(key, default)).strip() not in ("0", "false", "False", "no", "")


def _center(text: str, width: int) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return " " * pad + text


def _inline(label: str, value: str, width: int) -> str:
    """Keep label and value on one left-aligned line (no right-pad gap)."""
    text = f"{label}: {value or ''}".strip()
    if len(text) <= width:
        return text
    return text[:width]


def _double_rule(width: int) -> str:
    return "=" * width


def _single_rule(width: int) -> str:
    return "-" * width


def _format_receipt_date(created_at: str | None) -> str:
    if not created_at:
        return "Just now"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(created_at, fmt)
            # Compact — fits 80mm and 58mm with "Date: " prefix
            formatted = dt.strftime("%b %d, %Y %I:%M %p")
            return formatted.replace(" 0", " ").lstrip("0").replace("AM", "am").replace("PM", "pm")
        except ValueError:
            continue
    return created_at


def _item_columns(width: int) -> tuple[int, int, int, int]:
    """Return desc/qty/price/total widths that fit exactly in `width` chars.

    Layout: DESC + ' ' + QTY + ' ' + PRICE + ' ' + TOTAL  (3 gaps)
    """
    gaps = 3
    if width <= 32:
        w_qty, w_unit, w_total = 3, 7, 7
    else:
        w_qty, w_unit, w_total = 4, 10, 10
    w_desc = width - gaps - w_qty - w_unit - w_total
    if w_desc < 8:
        # Narrow paper: steal from price/total until desc is usable
        deficit = 8 - w_desc
        take_unit = min(deficit, max(0, w_unit - 6))
        w_unit -= take_unit
        deficit -= take_unit
        w_total -= min(deficit, max(0, w_total - 6))
        w_desc = width - gaps - w_qty - w_unit - w_total
    return w_desc, w_qty, w_unit, w_total


def _wrap_text(text: str, width: int) -> list[str]:
    """Word-wrap to `width`, hard-breaking long words. Never returns a line > width."""
    width = max(1, width)
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= width:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            while len(word) > width:
                lines.append(word[:width])
                word = word[width:]
            current = word
    if current:
        lines.append(current)
    return [line[:width] for line in (lines or [""])]


def _format_item_line(
    desc: str, qty: str, price: str, total: str,
    w_desc: int, w_qty: int, w_unit: int, w_total: int,
) -> str:
    """One receipt item row; Item text is hard-clamped to the Item column."""
    return (
        f"{desc[:w_desc]:<{w_desc}} "
        f"{qty[:w_qty]:>{w_qty}} "
        f"{price[:w_unit]:>{w_unit}} "
        f"{total[:w_total]:>{w_total}}"
    )


def _format_item_cont(desc: str, w_desc: int, w_qty: int, w_unit: int, w_total: int) -> str:
    """Continuation / Details line: text only in Item column; Qty/Price/Total blank."""
    blank_qty = " " * w_qty
    blank_unit = " " * w_unit
    blank_total = " " * w_total
    return f"{desc[:w_desc]:<{w_desc}} {blank_qty} {blank_unit} {blank_total}"


def build_receipt_text(invoice: Invoice, items: list[InvoiceItem], settings: dict | None = None) -> str:
    settings = settings or get_all_settings()
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    double = _double_rule(width)
    single = _single_rule(width)
    blank = ""
    spacing = settings.get("receipt_header_spacing", "normal")
    extra_blank_after_contact = spacing == "roomy"

    w_desc, w_qty, w_unit, w_total = _item_columns(width)
    header = f"{'Item':<{w_desc}} {'Qty':>{w_qty}} {'Price':>{w_unit}} {'Total':>{w_total}}"

    lines: list[str] = []

    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    # Business header
    if _on(settings, "receipt_show_business_name", "1"):
        biz = settings.get("business_name", "My Business").strip()
        if biz:
            lines.append(_center(biz.upper(), width))

    if _on(settings, "receipt_show_tagline", "1"):
        tagline = settings.get("business_tagline", "").strip()
        if tagline:
            lines.append(_center(tagline, width))

    lines.append(blank)

    contact_fields = []
    if _on(settings, "receipt_show_address", "1"):
        contact_fields.append("business_address")
    if _on(settings, "receipt_show_phone", "1"):
        contact_fields.append("business_phone")
    if _on(settings, "receipt_show_website", "1"):
        contact_fields.append("business_website")
    if _on(settings, "receipt_show_email", "1"):
        contact_fields.append("business_email")

    for field in contact_fields:
        value = settings.get(field, "").strip()
        if value:
            lines.append(_center(value, width))
            if extra_blank_after_contact:
                lines.append(blank)

    if contact_fields and not extra_blank_after_contact:
        lines.append(blank)

    lines.append(_center("SALES RECEIPT", width))
    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    # Invoice details — inline (never split label/value across lines)
    lines.append(_inline("Receipt #", invoice.invoice_number, width))
    lines.append(_inline("Date", _format_receipt_date(invoice.created_at), width))

    if _on(settings, "receipt_show_customer", "1"):
        if invoice.customer_name:
            lines.append(_inline("Customer", invoice.customer_name, width))
        if invoice.customer_phone:
            lines.append(_inline("Phone", invoice.customer_phone, width))
        email = getattr(invoice, "customer_email", "") or ""
        if email:
            lines.append(_inline("Email", email, width))

    lines.append(blank)
    lines.append(single)
    lines.append(header)
    lines.append(single)

    for item in items:
        desc_lines = _wrap_text(item.description, w_desc)
        unit = format_currency(item.unit_price)
        total = format_currency(item.line_total)
        qty_s = str(item.qty)
        lines.append(
            _format_item_line(desc_lines[0], qty_s, unit, total, w_desc, w_qty, w_unit, w_total)
        )
        for extra in desc_lines[1:]:
            lines.append(_format_item_cont(extra, w_desc, w_qty, w_unit, w_total))
        if item.serial_number and _on(settings, "receipt_show_details", "1"):
            for detail_line in _wrap_text(f"Details: {item.serial_number}", w_desc):
                lines.append(_format_item_cont(detail_line, w_desc, w_qty, w_unit, w_total))
        # One blank line between items for readability on thermal paper
        lines.append(blank)

    lines.append(single)
    lines.append(blank)

    tax_pct = int(invoice.tax_rate * 100)

    def money_row(label: str, amount: float) -> str:
        value = format_currency(amount)
        return f"{label:>{width - len(value) - 1}} {value}"

    lines.append(money_row("Subtotal", invoice.subtotal))
    timing = getattr(invoice, "discount_timing", "before_tax") or "before_tax"
    has_discount = getattr(invoice, "discount_amount", 0) and invoice.discount_amount > 0

    def discount_row():
        when = "after tax" if timing == "after_tax" else "before tax"
        if invoice.discount_type == "percent":
            lines.append(money_row(f"Discount ({invoice.discount_value:g}% {when})", invoice.discount_amount))
        else:
            lines.append(money_row(f"Discount ({when})", invoice.discount_amount))

    if has_discount and timing != "after_tax":
        discount_row()
    lines.append(money_row(f"Tax ({tax_pct}%)", invoice.tax_amount))
    if has_discount and timing == "after_tax":
        discount_row()
    lines.append(blank)
    lines.append(money_row("TOTAL", invoice.total))
    lines.append(blank)
    lines.append(_inline("Paid by", invoice.payment_method, width))

    notes = (getattr(invoice, "notes", None) or "").strip()
    if notes and _on(settings, "receipt_show_notes", "1"):
        lines.append(blank)
        lines.append("Notes:")
        for note_line in _wrap_text(notes, width):
            lines.append(note_line)

    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    if _on(settings, "receipt_show_thanks", "1"):
        lines.append(_center("Thank you for your business!", width))
        lines.append(_center("We appreciate your visit.", width))
        lines.append(blank)

    if _on(settings, "receipt_show_footer", "1"):
        footer = settings.get("receipt_footer", "").strip()
        if footer:
            for part in footer.split("\n"):
                for wrapped in _wrap_text(part, width):
                    lines.append(_center(wrapped, width))
            lines.append(blank)

    if _on(settings, "receipt_show_gst", "1"):
        gst = settings.get("gst_number", "").strip()
        if gst:
            lines.append(_center(f"HST Reg. {gst}", width))

    lines.append(blank)
    lines.append(double)
    lines.append(blank)
    lines.append(blank)
    return "\n".join(lines)


def sample_receipt_invoice(settings: dict | None = None) -> tuple[Invoice, list[InvoiceItem]]:
    """Sample sale used by Setup preview and test print."""
    settings = settings or get_all_settings()
    tax_rate = float(settings.get("tax_rate", "0.13") or "0.13")
    items = [
        InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description="Dell Latitude Laptop",
            serial_number="i5 8250U 32GB / 512GB / 15.6 / Win 11",
            qty=1, unit_price=699.99, line_total=699.99,
        ),
        InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description="Case",
            serial_number="",
            qty=1, unit_price=15.00, line_total=15.00,
        ),
    ]
    subtotal = sum(i.line_total for i in items)
    tax_amount = round(subtotal * tax_rate, 2)
    invoice = Invoice(
        id=None,
        invoice_number="INV-786-0001",
        customer_name="Rebecca",
        customer_phone="647-889-1668",
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=round(subtotal + tax_amount, 2),
        payment_method="Card",
        notes="Sample preview note",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        items=items,
        discount_type="",
        discount_value=0,
        discount_amount=0,
    )
    return invoice, items


def resolve_logo_path(settings: dict) -> str:
    from config import DATA_DIR, ASSETS_DIR

    if not _on(settings, "receipt_show_logo", "1"):
        return ""

    logo_path = settings.get("logo_path", "")
    if logo_path and os.path.exists(logo_path):
        return logo_path

    base = os.path.basename(logo_path) if logo_path else ""
    for candidate in (
        DATA_DIR / "logo.png",
        DATA_DIR / "logo.jpg",
        DATA_DIR / "logo.bmp",
        DATA_DIR / base if base else DATA_DIR / "logo.png",
        ASSETS_DIR / "logo.png",
        ASSETS_DIR / base if base else ASSETS_DIR / "logo.png",
    ):
        try:
            if candidate and os.path.exists(candidate):
                return str(candidate)
        except Exception:
            pass
    return ""


def build_logo_escpos_bytes(logo_path: str, max_width: int = 512) -> bytes:
    """Convert a logo image to centered ESC/POS raster bytes."""
    return _pil_logo_escpos_bytes(logo_path, max_width)


def prepare_logo_image(logo_path: str, max_width: int = 512):
    """Load and scale logo for thermal print (returns a PIL Image)."""
    from PIL import Image

    img = Image.open(logo_path).convert("RGBA")
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(background, img).convert("RGB")

    w, h = img.size
    if w != max_width:
        h = max(1, int(h * max_width / w))
        w = max_width
        img = img.resize((w, h), Image.Resampling.LANCZOS)
    return img


def _pil_logo_escpos_bytes(logo_path: str, max_width: int = 512) -> bytes:
    from PIL import Image

    img = Image.open(logo_path).convert("RGBA")
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(background, img).convert("L")

    w, h = img.size
    if w != max_width:
        h = max(1, int(h * max_width / w))
        w = max_width
        img = img.resize((w, h), Image.Resampling.LANCZOS)

    img = img.point(lambda p: 0 if p < 160 else 255, mode="1")
    width_bytes = (w + 7) // 8
    height = h

    data = bytearray()
    data.extend(b"\x1b\x61\x01")
    data.extend(b"\x1d\x76\x30\x00")
    data.extend(width_bytes.to_bytes(2, "little"))
    data.extend(height.to_bytes(2, "little"))

    pixels = img.load()
    for y in range(height):
        for x_byte in range(width_bytes):
            byte = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < w and pixels[x, y] == 0:
                    byte |= 1 << (7 - bit)
            data.append(byte)

    data.extend(b"\x1b\x61\x00\n\n")
    return bytes(data)
