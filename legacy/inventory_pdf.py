"""In-stock inventory checklist PDF for store floor counts."""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from database import get_all_settings, search_products
from models import Product
from utils import format_currency


def in_stock_products(products: list[Product] | None = None) -> list[Product]:
    items = products if products is not None else search_products("")
    return [p for p in items if p.qty > 0]


def group_by_category(products: list[Product]) -> list[tuple[str, list[Product]]]:
    groups: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        key = (p.category or "").strip() or "Uncategorized"
        groups[key].append(p)
    for items in groups.values():
        items.sort(key=lambda p: ((p.name or "").lower(), (p.sku or "").lower()))

    def sort_key(name: str) -> tuple[int, str]:
        return (1 if name == "Uncategorized" else 0, name.lower())

    return [(name, groups[name]) for name in sorted(groups.keys(), key=sort_key)]


def build_inventory_checklist_pdf(
    products: list[Product] | None = None,
    settings: dict | None = None,
) -> bytes:
    """Letter-size checklist: in-stock only, sorted by category, with checkboxes."""
    if settings is None:
        try:
            settings = get_all_settings()
        except Exception:
            settings = {}
    biz = (settings.get("business_name") or "My Business").strip()
    in_stock = in_stock_products(products)
    grouped = group_by_category(in_stock)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin_x = 0.6 * inch
    margin_top = 0.65 * inch
    margin_bottom = 0.6 * inch
    usable_w = width - 2 * margin_x

    y = height - margin_top
    today = datetime.now().strftime("%b %d, %Y")

    def ensure_space(need: float) -> None:
        nonlocal y
        if y - need < margin_bottom:
            c.showPage()
            y = height - margin_top

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, biz)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Inventory checklist — in stock")
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.drawString(
        margin_x,
        y,
        f"Printed {today}  ·  qty greater than 0  ·  sorted by category",
    )
    c.setFillColorRGB(0, 0, 0)
    y -= 20

    col_sku = margin_x
    col_name = margin_x + 1.1 * inch
    col_qty = margin_x + usable_w - 1.55 * inch
    col_price = margin_x + usable_w - 0.55 * inch
    col_check = margin_x + usable_w

    if not grouped:
        c.setFont("Helvetica", 11)
        c.drawString(margin_x, y, "No in-stock products.")
        c.save()
        return buffer.getvalue()

    for category, items in grouped:
        ensure_space(36)
        c.setFillColorRGB(0.94, 0.94, 0.94)
        c.rect(margin_x, y - 4, usable_w, 16, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_x + 4, y, category)
        c.setFont("Helvetica", 9)
        label = f"{len(items)} item" if len(items) == 1 else f"{len(items)} items"
        c.drawRightString(col_check, y, label)
        y -= 18

        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(col_sku, y, "SKU")
        c.drawString(col_name, y, "Name / details")
        c.drawRightString(col_qty, y, "Qty")
        c.drawRightString(col_price, y, "Price")
        c.drawRightString(col_check, y, "✓")
        c.setFillColorRGB(0, 0, 0)
        y -= 6
        c.setStrokeColorRGB(0.78, 0.78, 0.78)
        c.line(margin_x, y, margin_x + usable_w, y)
        y -= 12

        for item in items:
            ensure_space(28)
            c.setFont("Helvetica", 9)
            c.drawString(col_sku, y, (item.sku or "—")[:16])
            c.drawString(col_name, y, (item.name or "")[:48])
            c.drawRightString(col_qty, y, str(item.qty))
            c.drawRightString(col_price, y, format_currency(item.price))
            c.setStrokeColorRGB(0.45, 0.45, 0.45)
            c.rect(col_check - 10, y - 2, 9, 9, fill=0, stroke=1)
            y -= 12
            if (item.serial_number or "").strip():
                ensure_space(14)
                c.setFont("Helvetica", 8)
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.drawString(col_name, y, item.serial_number.strip()[:70])
                c.setFillColorRGB(0, 0, 0)
                y -= 10
            y -= 4

        y -= 8

    ensure_space(20)
    total_items = sum(len(items) for _, items in grouped)
    total_units = sum(p.qty for _, items in grouped for p in items)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(
        margin_x,
        y,
        f"{total_items} products  ·  {total_units} units in stock",
    )
    c.save()
    return buffer.getvalue()
