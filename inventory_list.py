"""Build a printable inventory list (thermal / preview)."""

from __future__ import annotations

from datetime import datetime

from categories import get_product_categories
from database import get_all_settings, search_products
from models import Product
from receipt_builder import get_printer_width_chars
from utils import format_currency


def build_inventory_list_text(
    products: list[Product] | None = None,
    settings: dict | None = None,
) -> str:
    settings = settings or get_all_settings()
    products = list(products if products is not None else search_products(""))
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    double = "=" * width
    single = "-" * width
    blank = ""

    lines: list[str] = [
        blank,
        double,
        blank,
        _center((settings.get("business_name") or "My Business").strip().upper(), width),
        _center("INVENTORY LIST", width),
        blank,
        _center(datetime.now().strftime("%b %d, %Y %I:%M %p").replace(" 0", " ").lstrip("0"), width),
        blank,
        double,
        blank,
    ]

    if not products:
        lines.append("No products in inventory.")
        lines.append(blank)
        lines.append(double)
        return "\n".join(lines)

    # Group by category
    cats = get_product_categories()
    by_cat: dict[str, list[Product]] = {c: [] for c in cats}
    other_key = "Other"
    if other_key not in by_cat:
        by_cat[other_key] = []
    for p in products:
        cat = (p.category or "").strip() or other_key
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(p)

    total_qty = 0
    total_value = 0.0

    for cat, items in by_cat.items():
        if not items:
            continue
        lines.append(cat.upper())
        lines.append(single)
        for p in sorted(items, key=lambda x: (x.name or "").lower()):
            total_qty += p.qty
            total_value += p.qty * p.price
            sku = (p.sku or "—")[:12]
            name = (p.name or "")[: max(8, width - 22)]
            qty_s = str(p.qty)
            price_s = format_currency(p.price)
            # SKU + name on first line; qty/price on same if room
            line1 = f"{sku}  {name}"
            lines.append(line1[:width])
            lines.append(f"  Qty {qty_s}   {price_s}"[:width])
            if p.serial_number:
                detail = f"  {p.serial_number}"[:width]
                lines.append(detail)
            lines.append(blank)
        lines.append(blank)

    lines.append(double)
    lines.append(f"Items: {len(products)}"[:width])
    lines.append(f"Total qty: {total_qty}"[:width])
    lines.append(f"Stock value: {format_currency(total_value)}"[:width])
    lines.append(blank)
    lines.append(double)
    lines.append(blank)
    return "\n".join(lines)


def _center(text: str, width: int) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return " " * pad + text
