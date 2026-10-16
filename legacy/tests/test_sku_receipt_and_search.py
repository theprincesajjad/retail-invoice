"""SKU on receipts and Sales History search."""

import pytest

import config
import database
from models import Invoice, InvoiceItem, Product
from receipt_builder import build_receipt_text, sample_receipt_invoice


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    database.init_db()
    return database


def test_receipt_includes_sku_line():
    inv, items = sample_receipt_invoice({"tax_rate": "0.13", "business_name": "Shop"})
    text = build_receipt_text(inv, items, settings={
        "business_name": "Shop",
        "tax_rate": "0.13",
        "receipt_show_details": "1",
        "receipt_show_business_name": "1",
        "receipt_show_customer": "1",
        "receipt_width": "80mm",
    })
    assert "SKU: 92001" in text
    assert "Dell Latitude Laptop" in text


def test_search_invoices_by_line_sku(db):
    pid = db.add_product(
        Product(
            id=None,
            name="ThinkPad",
            serial_number="16GB",
            sku="92055",
            price=400.0,
            qty=2,
            category="Laptops",
        )
    )
    inv = Invoice(
        id=None,
        invoice_number="INV-2001",
        customer_name="Alex",
        customer_phone="",
        subtotal=400.0,
        tax_rate=0.0,
        tax_amount=0.0,
        total=400.0,
        payment_method="Cash",
        notes="",
        created_at="2026-10-16 12:00:00",
        items=[],
    )
    items = [
        InvoiceItem(
            id=None,
            invoice_id=None,
            product_id=pid,
            description="ThinkPad",
            serial_number="16GB",
            qty=1,
            unit_price=400.0,
            line_total=400.0,
            sku="92055",
        )
    ]
    db.save_invoice(inv, items)

    found = db.search_invoices("92055")
    assert len(found) == 1
    assert found[0].invoice_number == "INV-2001"
    assert found[0].items[0].sku == "92055"


def test_search_invoices_by_product_sku_when_line_blank(db):
    pid = db.add_product(
        Product(
            id=None,
            name="Phone",
            serial_number="",
            sku="110777",
            price=200.0,
            qty=3,
            category="Cell Phones",
        )
    )
    inv = Invoice(
        id=None,
        invoice_number="INV-2002",
        customer_name="Sam",
        customer_phone="",
        subtotal=200.0,
        tax_rate=0.0,
        tax_amount=0.0,
        total=200.0,
        payment_method="Cash",
        notes="",
        created_at="2026-10-16 13:00:00",
        items=[],
    )
    items = [
        InvoiceItem(
            id=None,
            invoice_id=None,
            product_id=pid,
            description="Phone",
            serial_number="",
            qty=1,
            unit_price=200.0,
            line_total=200.0,
            sku="110777",
        )
    ]
    db.save_invoice(inv, items)
    # Simulate older sale with blank stored sku
    with config.get_db_connection() as conn:
        conn.execute("UPDATE invoice_items SET sku = '' WHERE invoice_id = ?", (inv.id,))
        conn.commit()

    found = db.search_invoices("110777")
    assert any(i.invoice_number == "INV-2002" for i in found)
    loaded = db.get_invoice_by_id(inv.id)
    assert loaded.items[0].sku == "110777"  # resolved from product
