"""Shared receipt layout for print preview, thermal print, and email."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

from database import get_all_settings
from models import Invoice, InvoiceItem
from utils import format_currency


def get_printer_width_chars(width_setting: str) -> int:
    return 32 if width_setting == "58mm" else 48


def _center(text: str, width: int) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return " " * pad + text


def _label_value(label: str, value: str, width: int) -> str:
    label = f"{label}:"
    value = value or ""
    gap = width - len(label) - len(value)
    if gap < 1:
        return f"{label} {value}"[:width]
    return label + (" " * gap) + value


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
            formatted = dt.strftime("%B %d, %Y  ·  %I:%M %p")
            if formatted.startswith("0"):
                formatted = formatted.replace(" 0", " ", 1)
            return formatted.replace(" 0", " ").replace("AM", "am").replace("PM", "pm")
        except ValueError:
            continue
    return created_at


def _item_columns(width: int) -> tuple[int, int, int, int]:
    if width <= 32:
        return 14, 3, 7, 7
    return 20, 4, 10, 10


def _wrap_text(text: str, width: int) -> list[str]:
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
            current = word[:width]
    if current:
        lines.append(current)
    return lines or [""]


def build_receipt_text(invoice: Invoice, items: list[InvoiceItem], settings: dict | None = None) -> str:
    settings = settings or get_all_settings()
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    double = _double_rule(width)
    single = _single_rule(width)
    blank = ""

    w_desc, w_qty, w_unit, w_total = _item_columns(width)
    header = f"{'Item':<{w_desc}} {'Qty':>{w_qty}} {'Price':>{w_unit}} {'Total':>{w_total}}"

    lines: list[str] = []

    # Decorative top
    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    # Business header
    biz = settings.get("business_name", "My Business").strip()
    lines.append(_center(biz.upper(), width))
    tagline = settings.get("business_tagline", "").strip()
    if tagline:
        lines.append(_center(tagline, width))
    lines.append(blank)

    for field in ("business_address", "business_phone", "business_website", "business_email"):
        value = settings.get(field, "").strip()
        if value:
            lines.append(_center(value, width))

    lines.append(blank)
    lines.append(_center("SALES RECEIPT", width))
    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    # Invoice details
    lines.append(_label_value("Receipt #", invoice.invoice_number, width))
    lines.append(_label_value("Date", _format_receipt_date(invoice.created_at), width))

    if invoice.customer_name or invoice.customer_phone:
        lines.append(blank)
        if invoice.customer_name:
            lines.append(_label_value("Customer", invoice.customer_name, width))
        if invoice.customer_phone:
            lines.append(_label_value("Phone", invoice.customer_phone, width))

    lines.append(blank)
    lines.append(single)
    lines.append(header)
    lines.append(single)

    # Line items
    for item in items:
        desc_lines = _wrap_text(item.description, w_desc)
        unit = format_currency(item.unit_price)
        total = format_currency(item.line_total)
        first = desc_lines[0]
        lines.append(f"{first:<{w_desc}} {item.qty:>{w_qty}} {unit:>{w_unit}} {total:>{w_total}}")
        for extra in desc_lines[1:]:
            lines.append(f"{extra:<{w_desc}}")
        if item.serial_number:
            lines.append(f"  S/N: {item.serial_number}")

    lines.append(single)
    lines.append(blank)

    tax_pct = int(invoice.tax_rate * 100)

    def money_row(label: str, amount: float) -> str:
        value = format_currency(amount)
        return f"{label:>{width - len(value) - 1}} {value}"

    lines.append(money_row("Subtotal", invoice.subtotal))
    if getattr(invoice, "discount_amount", 0) and invoice.discount_amount > 0:
        if invoice.discount_type == "percent":
            lines.append(money_row(f"Discount ({invoice.discount_value:g}%)", invoice.discount_amount))
        else:
            lines.append(money_row("Discount", invoice.discount_amount))
    lines.append(money_row(f"Tax ({tax_pct}%)", invoice.tax_amount))
    lines.append(blank)
    lines.append(money_row("TOTAL", invoice.total))
    lines.append(blank)
    lines.append(_label_value("Paid by", invoice.payment_method, width))
    lines.append(blank)
    lines.append(double)
    lines.append(blank)

    # Thank you block
    lines.append(_center("Thank you for your business!", width))
    lines.append(_center("We appreciate your visit.", width))
    lines.append(blank)

    footer = settings.get("receipt_footer", "").strip()
    if footer:
        for part in footer.split("\n"):
            for wrapped in _wrap_text(part, width):
                lines.append(_center(wrapped, width))
        lines.append(blank)

    gst = settings.get("gst_number", "").strip()
    if gst:
        lines.append(_center(f"HST Reg. {gst}", width))

    lines.append(blank)
    lines.append(double)
    lines.append(blank)
    lines.append(blank)
    return "\n".join(lines)


def resolve_logo_path(settings: dict) -> str:
    from config import DATA_DIR, ASSETS_DIR

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


def build_logo_escpos_bytes(logo_path: str, max_width: int = 384) -> bytes:
    """Convert a logo image to centered ESC/POS raster bytes."""
    return _pil_logo_escpos_bytes(logo_path, max_width)


def _pil_logo_escpos_bytes(logo_path: str, max_width: int = 384) -> bytes:
    from PIL import Image

    img = Image.open(logo_path).convert("RGBA")
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(background, img).convert("L")

    w, h = img.size
    if w > max_width:
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
