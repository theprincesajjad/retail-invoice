"""Tests for totals math and product spreadsheet import."""

from pathlib import Path

from models import InvoiceItem
from product_import import (
    TEMPLATE_HEADERS,
    read_product_rows,
    write_csv_template,
    write_excel_template,
)
from utils import compute_invoice_totals


def _items():
    return [
        InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description="A", serial_number="", qty=1, unit_price=100.0, line_total=100.0,
        )
    ]


def test_discount_before_tax_percent():
    subtotal, discount, tax, total = compute_invoice_totals(
        _items(), 0.13, "percent", 10, "before_tax",
    )
    assert subtotal == 100.0
    assert discount == 10.0
    assert abs(tax - 11.7) < 1e-9
    assert abs(total - 101.7) < 1e-9


def test_discount_after_tax_percent():
    subtotal, discount, tax, total = compute_invoice_totals(
        _items(), 0.13, "percent", 10, "after_tax",
    )
    assert subtotal == 100.0
    assert abs(tax - 13.0) < 1e-9
    assert abs(discount - 11.3) < 1e-9  # 10% of 113
    assert abs(total - 101.7) < 1e-9


def test_discount_after_tax_fixed():
    subtotal, discount, tax, total = compute_invoice_totals(
        _items(), 0.13, "fixed", 5, "after_tax",
    )
    assert abs(tax - 13.0) < 1e-9
    assert discount == 5.0
    assert abs(total - 108.0) < 1e-9


def test_excel_template_headers_and_rows(tmp_path: Path):
    path = write_excel_template(tmp_path / "t.xlsx")
    rows = read_product_rows(path)
    assert len(rows) == 2
    assert rows[0]["name"] == "Dell Latitude Laptop"
    assert rows[0]["sku"] == "60000"
    assert rows[0]["price"] == "699.99"


def test_csv_template_roundtrip(tmp_path: Path):
    path = write_csv_template(tmp_path / "t.csv")
    rows = read_product_rows(path)
    assert {r["sku"] for r in rows} == {"60000", "60001"}
    text = path.read_text(encoding="utf-8")
    assert ",".join(TEMPLATE_HEADERS) in text


def test_receipt_blank_line_between_items():
    from receipt_builder import build_receipt_text
    from models import Invoice
    from datetime import datetime

    items = [
        InvoiceItem(None, None, None, "Item One", "", 1, 10, 10),
        InvoiceItem(None, None, None, "Item Two", "", 1, 20, 20),
    ]
    inv = Invoice(
        id=None, invoice_number="INV-786-0001", customer_name="", customer_phone="",
        subtotal=30, tax_rate=0.13, tax_amount=3.9, total=33.9,
        payment_method="Cash", notes="", created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        items=items,
    )
    text = build_receipt_text(inv, items, settings={
        "receipt_width": "80mm",
        "business_name": "Shop",
        "receipt_show_business_name": "1",
        "receipt_show_tagline": "0",
        "receipt_show_address": "0",
        "receipt_show_phone": "0",
        "receipt_show_website": "0",
        "receipt_show_email": "0",
        "receipt_show_customer": "0",
        "receipt_show_details": "0",
        "receipt_show_notes": "0",
        "receipt_show_thanks": "0",
        "receipt_show_footer": "0",
        "receipt_show_gst": "0",
        "receipt_header_spacing": "normal",
    })
    # Item One line, blank, Item Two line
    assert "Item One" in text and "Item Two" in text
    idx1 = text.index("Item One")
    idx2 = text.index("Item Two")
    between = text[idx1:idx2]
    assert "\n\n" in between or between.count("\n") >= 2
