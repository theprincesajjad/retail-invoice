"""Tests for inventory Excel sync (Status / date sold / category tabs)."""

from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

import config
import database
from inventory_excel_sync import (
    STATUS_IN_STOCK,
    STATUS_SOLD,
    SYNC_HEADERS,
    category_sheet_plan,
    export_inventory_excel,
    organize_products_for_excel,
    organize_products_for_sheet,
    product_status,
    pull_inventory_excel,
    read_sync_rows,
    sheet_title_for_category,
    sync_inventory_excel,
    write_inventory_excel,
)
from models import Invoice, InvoiceItem, Product
from product_categories import PRODUCT_CATEGORIES


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    database.init_db()
    return database


def _product(**kwargs):
    base = dict(
        id=None,
        name="Laptop",
        serial_number="i5 16GB",
        sku="92001",
        price=500.0,
        qty=1,
        category="Laptops",
        import_date="2026-09-01",
        sold_date="",
    )
    base.update(kwargs)
    return Product(**base)


def test_sync_headers():
    assert SYNC_HEADERS == [
        "SKU",
        "Status",
        "Product Description",
        "Details",
        "qty",
        "Category",
        "price",
        "date added",
        "date sold",
    ]


def test_category_sheet_plan_includes_all_builtin_tabs():
    products = [
        _product(sku="92001", category="Laptops"),
        _product(id=2, sku="110001", name="Phone", category="Cell Phones"),
        _product(id=3, sku="99999", name="Cable", category="Accessories"),
    ]
    plan = category_sheet_plan(products)
    titles = [t for t, _ in plan]
    for cat in PRODUCT_CATEGORIES:
        assert sheet_title_for_category(cat) in titles
    assert "Accessories" in titles
    by_title = {t: items for t, items in plan}
    assert [p.sku for p in by_title["Laptops"]] == ["92001"]
    assert [p.sku for p in by_title["Cell Phones"]] == ["110001"]
    assert [p.sku for p in by_title["Accessories"]] == ["99999"]
    assert by_title["Monitors"] == []


def test_write_and_read_roundtrip(tmp_path: Path):
    products = [
        _product(sku="92001", qty=1, sold_date=""),
        _product(id=2, sku="110001", name="Phone", qty=0, sold_date="2026-09-10", category="Cell Phones"),
    ]
    path = write_inventory_excel(tmp_path / "inv.xlsx", products)
    wb = load_workbook(path, data_only=True)
    assert wb.sheetnames[: len(PRODUCT_CATEGORIES)] == [
        sheet_title_for_category(c) for c in PRODUCT_CATEGORIES
    ]
    wb.close()

    rows = read_sync_rows(path)
    assert len(rows) == 2
    by_sku = {r["sku"]: r for r in rows}
    assert by_sku["92001"]["status"] == STATUS_IN_STOCK
    assert by_sku["92001"]["category"] == "Laptops"
    assert by_sku["92001"]["sheet"] == "Laptops"
    assert by_sku["110001"]["status"] == STATUS_SOLD
    assert by_sku["110001"]["name"] == "Phone"
    assert by_sku["110001"]["sold_date"] == "2026-09-10"
    assert by_sku["110001"]["sheet"] == "Cell Phones"


def test_excel_one_sheet_per_category_sorted_by_sku(tmp_path: Path):
    products = [
        _product(sku="92050", name="B Laptop", category="Laptops"),
        _product(id=2, sku="92010", name="A Laptop", category="Laptops"),
        _product(id=3, sku="110200", name="B Phone", category="Cell Phones"),
        _product(id=4, sku="110050", name="A Phone", category="Cell Phones"),
        _product(id=5, sku="60001", name="Monitor", category="Monitors"),
    ]
    # Flat helper still sorts with gaps (legacy)
    organized = organize_products_for_excel(products)
    assert len(organized) == 5 + 3 + 3

    laptops = organize_products_for_sheet(
        [p for p in products if p.category == "Laptops"]
    )
    assert [p.sku for p in laptops] == ["92010", "92050"]

    path = write_inventory_excel(tmp_path / "sorted.xlsx", products)
    wb = load_workbook(path, data_only=True)
    assert "Laptops" in wb.sheetnames
    assert "Cell Phones" in wb.sheetnames
    assert "Monitors" in wb.sheetnames
    laptop_skus = [
        row[0]
        for row in wb["Laptops"].iter_rows(min_row=2, values_only=True)
        if row[0]
    ]
    phone_skus = [
        row[0]
        for row in wb["Cell Phones"].iter_rows(min_row=2, values_only=True)
        if row[0]
    ]
    wb.close()
    assert laptop_skus == ["92010", "92050"]
    assert phone_skus == ["110050", "110200"]

    rows = read_sync_rows(path)
    assert {r["sku"] for r in rows} == {"110050", "110200", "92010", "92050", "60001"}


def test_sync_pulls_new_sku_from_category_tab(db, tmp_path: Path):
    path = tmp_path / "inventory.xlsx"
    # Start with empty category tabs
    write_inventory_excel(path, [])
    wb = load_workbook(path)
    ws = wb["Laptops"]
    ws.append(["92NEW", STATUS_IN_STOCK, "From Excel", "", 2, "Laptops", 199.0, "", ""])
    wb.save(path)
    wb.close()

    result = sync_inventory_excel(path)
    assert result.added == 1
    assert result.exported >= 1
    found = [p for p in db.list_all_products() if p.sku == "92NEW"]
    assert len(found) == 1
    assert found[0].name == "From Excel"
    assert found[0].qty == 2
    assert found[0].category == "Laptops"
    rows = read_sync_rows(path)
    assert any(r["sku"] == "92NEW" and r["status"] == STATUS_IN_STOCK for r in rows)
    # Missing categories still present after rewrite
    wb = load_workbook(path)
    for cat in PRODUCT_CATEGORIES:
        assert sheet_title_for_category(cat) in wb.sheetnames
    wb.close()


def test_sheet_name_fills_category_when_column_blank(db, tmp_path: Path):
    path = tmp_path / "inventory.xlsx"
    write_inventory_excel(path, [])
    wb = load_workbook(path)
    ws = wb["Cell Phones"]
    # Category column left blank — tab name should supply it on pull
    ws.append(["110999", STATUS_IN_STOCK, "Blank Cat Phone", "", 1, None, 99.0, "", ""])
    wb.save(path)
    wb.close()

    result = pull_inventory_excel(path)
    assert result.added == 1
    phone = [p for p in db.list_all_products() if p.sku == "110999"][0]
    assert phone.category == "Cell Phones"


def test_extra_category_gets_its_own_tab(tmp_path: Path):
    path = write_inventory_excel(
        tmp_path / "extra.xlsx",
        [_product(sku="50001", name="Dock", category="Docks")],
    )
    wb = load_workbook(path)
    assert "Docks" in wb.sheetnames
    for cat in PRODUCT_CATEGORIES:
        assert sheet_title_for_category(cat) in wb.sheetnames
    dock_rows = [
        row for row in wb["Docks"].iter_rows(min_row=2, values_only=True) if row[0]
    ]
    wb.close()
    assert dock_rows[0][0] == "50001"
    assert dock_rows[0][2] == "Dock"


def test_sale_sets_sold_date_and_excel(db, tmp_path: Path):
    pid = db.add_product(_product(qty=1, sold_date=""))
    inv = Invoice(
        id=None,
        invoice_number="INV-1001",
        customer_name="Pat",
        customer_phone="",
        subtotal=500.0,
        tax_rate=0.0,
        tax_amount=0.0,
        total=500.0,
        payment_method="Cash",
        notes="",
        created_at="2026-09-14 12:00:00",
        items=[],
    )
    items = [
        InvoiceItem(
            id=None,
            invoice_id=None,
            product_id=pid,
            description="Laptop",
            serial_number="",
            qty=1,
            unit_price=500.0,
            line_total=500.0,
        )
    ]
    db.save_invoice(inv, items)
    product = db.search_products("92001", stock="All items")[0]
    assert product.qty == 0
    assert product.sold_date
    assert product_status(product) == STATUS_SOLD

    path = tmp_path / "inv.xlsx"
    db.save_setting("inventory_excel_path", str(path))
    export_inventory_excel(path)
    rows = read_sync_rows(path)
    sold = next(r for r in rows if r["sku"] == "92001")
    assert sold["status"] == STATUS_SOLD
    assert sold["sold_date"] == product.sold_date
    assert sold["sheet"] == "Laptops"


def test_void_clears_sold_date(db):
    pid = db.add_product(_product(qty=1))
    inv = Invoice(
        id=None,
        invoice_number="INV-1002",
        customer_name="Pat",
        customer_phone="",
        subtotal=500.0,
        tax_rate=0.0,
        tax_amount=0.0,
        total=500.0,
        payment_method="Cash",
        notes="",
        created_at="2026-09-14 12:00:00",
        items=[],
    )
    items = [
        InvoiceItem(
            id=None,
            invoice_id=None,
            product_id=pid,
            description="Laptop",
            serial_number="",
            qty=1,
            unit_price=500.0,
            line_total=500.0,
        )
    ]
    db.save_invoice(inv, items)
    assert db.search_products("92001", stock="All items")[0].qty == 0
    db.void_invoice(inv.id)
    restored = db.search_products("92001", stock="All items")[0]
    assert restored.qty == 1
    assert (restored.sold_date or "") == ""


def test_pull_status_sold_forces_qty_zero(db, tmp_path: Path):
    db.add_product(_product(sku="92SOLD", qty=1, sold_date=""))
    path = tmp_path / "inv.xlsx"
    write_inventory_excel(
        path,
        [_product(sku="92SOLD", qty=0, sold_date="2026-08-01")],
    )
    wb = load_workbook(path)
    ws = wb["Laptops"]
    # Find the 92SOLD row and force Sold
    for row_idx in range(2, ws.max_row + 1):
        if ws.cell(row=row_idx, column=1).value == "92SOLD":
            ws.cell(row=row_idx, column=2, value=STATUS_SOLD)
            ws.cell(row=row_idx, column=5, value=0)
            ws.cell(row=row_idx, column=9, value="2026-08-01")
            break
    wb.save(path)
    wb.close()

    pull_inventory_excel(path)
    p = [x for x in db.list_all_products() if x.sku == "92SOLD"][0]
    assert p.qty == 0
    assert p.sold_date == "2026-08-01"


def test_legacy_single_sheet_inventory_still_imports(db, tmp_path: Path):
    """Older inventory.xlsx with one Inventory sheet still pulls on sync."""
    path = tmp_path / "legacy.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws.append(SYNC_HEADERS)
    ws.append(["92077", STATUS_IN_STOCK, "Legacy Row", "", 1, "Laptops", 50.0, "", ""])
    wb.save(path)
    wb.close()

    result = sync_inventory_excel(path)
    assert result.added == 1
    assert any(p.sku == "92077" for p in db.list_all_products())
    # Rewrite upgrades to category tabs
    wb = load_workbook(path)
    assert "Laptops" in wb.sheetnames
    assert "Inventory" not in wb.sheetnames
    wb.close()
