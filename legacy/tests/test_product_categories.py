"""Tests for product categories and SKU prefix rules."""

from product_categories import PRODUCT_CATEGORIES, SKU_CATEGORY_RULES, category_for_sku


def test_category_list():
    assert PRODUCT_CATEGORIES == [
        "Laptops",
        "Desktops",
        "Monitors",
        "Printers",
        "Cell Phones",
        "Tablets",
    ]


def test_sku_prefix_rules():
    assert category_for_sku("92055") == "Laptops"
    assert category_for_sku("92") == "Laptops"
    assert category_for_sku("110200") == "Cell Phones"
    assert category_for_sku("110") == "Cell Phones"
    assert category_for_sku("60000") == ""
    assert category_for_sku("") == ""
    # Longer prefix wins when both could match in theory
    assert SKU_CATEGORY_RULES[0][0] == "110"
