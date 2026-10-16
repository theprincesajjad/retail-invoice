"""Tests for inventory CSV export / import with date stamp rules."""

from pathlib import Path

from models import Product
from product_import import (
    TEMPLATE_HEADERS,
    import_products_from_file,
    read_product_rows,
    today_date_stamp,
    write_csv_template,
    write_products_csv,
)


def test_template_headers_include_category_and_date():
    assert TEMPLATE_HEADERS[-2:] == ["Category", "Date Stamp"]


def test_export_csv_roundtrip(tmp_path: Path):
    products = [
        Product(
            id=1, name="Pad", serial_number="Silver", sku="110999",
            price=10, qty=2, category="Cell Phones", import_date="2026-09-04",
        ),
    ]
    path = write_products_csv(tmp_path / "out.csv", products)
    text = path.read_text(encoding="utf-8")
    assert "Category,Date Stamp" in text.replace(" ", "") or "Category,Date Stamp" in text
    assert "110999" in text and "Cell Phones" in text and "2026-09-04" in text
    rows = read_product_rows(path)
    assert rows[0]["sku"] == "110999"
    assert rows[0]["import_date"] == "2026-09-04"


def test_import_skips_dated_rows(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "in.csv"
    csv_path.write_text(
        "SKU,Product Name,Details,Qty,Price,Category,Date Stamp\n"
        "92-1,Old Laptop,,1,100,Laptops,2026-01-01\n"
        "92-2,New Laptop,,2,200,Laptops,\n",
        encoding="utf-8",
    )

    added: list[Product] = []
    updated: list[Product] = []

    def fake_add(p: Product):
        added.append(p)
        return 1

    def fake_update(p: Product):
        updated.append(p)

    def fake_search(q=""):
        return []

    monkeypatch.setattr("database.add_product", fake_add)
    monkeypatch.setattr("database.update_product", fake_update)
    monkeypatch.setattr("database.search_products", fake_search)

    result = import_products_from_file(csv_path)
    assert result.added == 1
    assert result.skipped_dated == 1
    assert added[0].sku == "92-2"
    assert added[0].import_date == today_date_stamp()
    assert added[0].category == "Laptops"


def test_csv_template_has_blank_date(tmp_path: Path):
    path = write_csv_template(tmp_path / "t.csv")
    rows = read_product_rows(path)
    assert all(r["import_date"] == "" for r in rows)
    assert any(r["category"] == "Laptops" for r in rows)
