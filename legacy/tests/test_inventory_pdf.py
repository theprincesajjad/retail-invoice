"""Tests for in-stock inventory checklist PDF."""

from models import Product
from inventory_pdf import (
    build_inventory_checklist_pdf,
    group_by_category,
    in_stock_products,
)


def _products():
    return [
        Product(
            id=1, name="ThinkPad", serial_number="16GB", sku="92001",
            price=899.0, qty=2, category="Laptops", created_at="",
        ),
        Product(
            id=2, name="iPhone", serial_number="Blue", sku="110001",
            price=499.0, qty=1, category="Cell Phones", created_at="",
        ),
        Product(
            id=3, name="Gone", serial_number="", sku="x",
            price=10.0, qty=0, category="Monitors", created_at="",
        ),
        Product(
            id=4, name="Misc Cable", serial_number="", sku="c1",
            price=5.0, qty=3, category="", created_at="",
        ),
    ]


def test_in_stock_filters_qty():
    names = [p.name for p in in_stock_products(_products())]
    assert names == ["ThinkPad", "iPhone", "Misc Cable"]


def test_group_by_category_sort():
    groups = group_by_category(in_stock_products(_products()))
    assert [name for name, _ in groups] == ["Cell Phones", "Laptops", "Uncategorized"]
    assert groups[1][1][0].name == "ThinkPad"


def test_checklist_pdf_bytes():
    pdf = build_inventory_checklist_pdf(
        _products(),
        settings={"business_name": "Gadgets & Gold"},
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
