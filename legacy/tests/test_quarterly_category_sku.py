"""Quarterly date ranges, category-filtered product search, sales helpers."""

from datetime import datetime

import pytest

import config
import database
from models import Invoice, InvoiceItem, Product
from sales_report_pdf import build_monthly_totals_pdf, build_sales_report_pdf
from utils import current_quarter_label, parse_report_date, quarter_date_range


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    database.init_db()
    return database


def test_current_quarter_label_october():
    assert current_quarter_label(datetime(2026, 10, 16)) == "Q4 2026"
    assert current_quarter_label(datetime(2026, 1, 5)) == "Q1 2026"
    assert current_quarter_label(datetime(2026, 4, 1)) == "Q2 2026"
    assert current_quarter_label(datetime(2026, 7, 31)) == "Q3 2026"


def test_quarter_date_range_q4():
    start, end = quarter_date_range("Q4 2026")
    assert start == "2026-10-01 00:00:00"
    assert end == "2026-12-31 23:59:59"
    start, end = quarter_date_range("Q1 2026")
    assert start == "2026-01-01 00:00:00"
    assert end == "2026-03-31 23:59:59"
    assert quarter_date_range("not-a-quarter") == (None, None)


def test_quarterly_range_finds_sales_and_exports(db, tmp_path):
    pid = db.add_product(
        Product(None, "Laptop", "16GB", "92001", 100.0, 10, "Laptops")
    )
    for month, day, num in [(10, 5, "1001"), (11, 10, "1101"), (12, 15, "1201")]:
        inv = Invoice(
            None,
            f"INV-{num}",
            "Pat",
            "",
            100.0,
            0.13,
            13.0,
            113.0,
            "Cash",
            "",
            f"2026-{month:02d}-{day:02d} 12:00:00",
            [],
        )
        items = [
            InvoiceItem(
                None, None, pid, "Laptop", "16GB", 1, 100.0, 100.0, sku="92001"
            )
        ]
        iid = db.save_invoice(inv, items)
        with config.get_db_connection() as conn:
            conn.execute(
                "UPDATE invoices SET created_at=? WHERE id=?",
                (f"2026-{month:02d}-{day:02d} 12:00:00", iid),
            )
            conn.commit()

    start, end = quarter_date_range("Q4 2026")
    found = db.search_invoices("", start, end, include_items=False)
    assert len(found) == 3
    # Q1 should be empty — the old Quarterly default that made export look broken
    q1_start, q1_end = quarter_date_range("Q1 2026")
    assert db.search_invoices("", q1_start, q1_end, include_items=False) == []

    sales = build_sales_report_pdf(
        found,
        period_label="Q4 2026",
        start_date=start,
        end_date=end,
        settings={"business_name": "Shop"},
    )
    monthly = build_monthly_totals_pdf(
        found,
        period_label="Q4 2026",
        start_date=start,
        end_date=end,
        settings={"business_name": "Shop"},
    )
    assert sales[:4] == b"%PDF"
    assert monthly[:4] == b"%PDF"
    (tmp_path / "q4-sales.pdf").write_bytes(sales)
    (tmp_path / "q4-monthly.pdf").write_bytes(monthly)


def test_search_products_category_filter(db):
    db.add_product(Product(None, "ThinkPad", "", "92001", 500.0, 2, "Laptops"))
    db.add_product(Product(None, "iPhone", "", "110001", 400.0, 3, "Cell Phones"))
    db.add_product(Product(None, "Dell Tower", "", "80001", 300.0, 1, "Desktops"))

    all_hits = db.search_products("")
    assert len(all_hits) == 3

    laptops = db.search_products("", category="Laptops")
    assert len(laptops) == 1
    assert laptops[0].sku == "92001"

    phones = db.search_products("iPhone", category="Cell Phones")
    assert len(phones) == 1
    assert phones[0].name == "iPhone"

    # Search limited to Laptops must not return phones
    assert db.search_products("iPhone", category="Laptops") == []

    # All categories aliases behave like no filter
    assert len(db.search_products("", category="All categories")) == 3
    assert len(db.search_products("", category=None)) == 3


def test_custom_from_to_still_parses_for_multi_month():
    start = parse_report_date("2026-07-01")
    end = parse_report_date("2026-09-30", end_of_day=True)
    assert start == "2026-07-01 00:00:00"
    assert end == "2026-09-30 23:59:59"
