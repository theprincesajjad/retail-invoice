"""Tests for categories, inventory import, and inventory list."""

from pathlib import Path

import sqlite3

from categories import (
    DEFAULT_CATEGORIES,
    normalize_category,
    parse_categories,
    serialize_categories,
)
from inventory_list import build_inventory_list_text
from models import InvoiceItem, Product
from product_import import (
    INVENTORY_HEADERS,
    STATUS_IN_INVENTORY,
    import_products_from_file,
    read_product_rows,
    write_inventory_workbook,
)
from utils import compute_invoice_totals


def test_default_categories():
    assert "Laptops" in DEFAULT_CATEGORIES
    assert "Cell Phones" in DEFAULT_CATEGORIES
    assert parse_categories("") == DEFAULT_CATEGORIES


def test_serialize_roundtrip():
    raw = serialize_categories(["Laptops", "Other", "Laptops"])
    assert parse_categories(raw) == ["Laptops", "Other"]


def test_normalize_category():
    assert normalize_category("laptops", ["Laptops", "Other"]) == "Laptops"
    assert normalize_category("", ["Other"]) == "Other"


def test_inventory_workbook_has_status_and_category(tmp_path: Path):
    products = [
        Product(1, "Phone", "128GB", "1001", 299.0, 2, "Cell Phones", ""),
        Product(2, "Case", "", "1002", 15.0, 5, "Accessories", ""),
    ]
    path = write_inventory_workbook(tmp_path / "inv.xlsx", products, blank_rows=3)
    rows = read_product_rows(path)
    assert rows[0]["status"] == STATUS_IN_INVENTORY
    assert rows[0]["category"] == "Cell Phones"
    assert "Category" in INVENTORY_HEADERS
    assert "Status" in INVENTORY_HEADERS


def test_import_skips_without_sku_and_existing(tmp_path: Path, monkeypatch):
    import config
    import database

    db_path = tmp_path / "t.db"

    def conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(config, "get_db_connection", conn)
    monkeypatch.setattr(database, "get_db_connection", conn)
    database.init_db()

    from database import add_product, search_products

    add_product(Product(None, "Existing", "", "SKU-1", 10.0, 1, "Other", ""))

    csv_path = tmp_path / "import.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(",".join(INVENTORY_HEADERS) + "\n")
        f.write("SKU-1,Existing,,Other,1,10,In inventory\n")
        f.write(",NoSkuName,,Other,1,5,\n")
        f.write("SKU-2,Brand New,nice,Laptops,3,50,\n")
        f.write("SKU-1,Dup attempt,,Other,9,9,\n")

    result = import_products_from_file(csv_path)
    assert result.added == 1
    products = search_products("")
    skus = {p.sku for p in products}
    assert skus == {"SKU-1", "SKU-2"}
    new = next(p for p in products if p.sku == "SKU-2")
    assert new.category == "Laptops"


def test_discount_before_tax_still_works():
    items = [InvoiceItem(None, None, None, "A", "", 1, 100.0, 100.0)]
    _, discount, tax, total = compute_invoice_totals(items, 0.13, "percent", 10, "before_tax")
    assert discount == 10.0
    assert abs(tax - 11.7) < 1e-9


def test_inventory_list_text_contains_header():
    text = build_inventory_list_text(
        products=[
            Product(1, "Dell", "i5", "60000", 699.0, 1, "Laptops", ""),
        ],
        settings={
            "business_name": "Test Shop",
            "receipt_width": "80mm",
        },
    )
    assert "INVENTORY LIST" in text
    assert "LAPTOPS" in text
    assert "Dell" in text
