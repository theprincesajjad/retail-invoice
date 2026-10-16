"""Regression tests for multi-month sales range export and invoice load."""

from pathlib import Path

import pytest

import config
import database
from models import Invoice, InvoiceItem, Product
from receipt_builder import build_receipt_text
from sales_report_pdf import build_monthly_totals_pdf, build_sales_report_pdf
from utils import parse_report_date


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    database.init_db()
    return database


def _seed_three_months(db):
    pid = db.add_product(
        Product(None, "Laptop", "16GB", "92001", 100.0, 10, "Laptops")
    )
    for month, day, num in [(7, 5, "0701"), (8, 10, "0801"), (9, 15, "0901")]:
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
    return pid


def test_three_month_range_finds_sales_and_items(db):
    _seed_three_months(db)
    start = parse_report_date("2026-07-01")
    end = parse_report_date("2026-09-30", end_of_day=True)
    found = db.search_invoices("", start, end)
    assert len(found) == 3
    for inv in found:
        fresh = db.get_invoice_by_id(inv.id)
        assert fresh is not None
        assert len(fresh.items) == 1
        text = build_receipt_text(
            fresh,
            fresh.items,
            settings={
                "business_name": "Shop",
                "receipt_width": "80mm",
                "receipt_show_details": "1",
                "receipt_show_business_name": "1",
                "tax_rate": "0.13",
            },
        )
        assert "Laptop" in text
        assert "SKU: 92001" in text


def test_three_month_exports(db, tmp_path: Path):
    _seed_three_months(db)
    start = "2026-07-01 00:00:00"
    end = "2026-09-30 23:59:59"
    invoices = [
        inv
        for inv in db.search_invoices("", start, end)
        if not int(getattr(inv, "voided", 0) or 0)
    ]
    assert len(invoices) == 3
    label = f"{start[:10]} to {end[:10]}"
    sales = build_sales_report_pdf(
        invoices,
        period_label=label,
        start_date=start,
        end_date=end,
        settings={"business_name": "Shop"},
    )
    monthly = build_monthly_totals_pdf(
        invoices,
        period_label=label,
        start_date=start,
        end_date=end,
        settings={"business_name": "Shop"},
    )
    assert sales[:4] == b"%PDF"
    assert monthly[:4] == b"%PDF"
    (tmp_path / "sales.pdf").write_bytes(sales)
    (tmp_path / "monthly.pdf").write_bytes(monthly)
