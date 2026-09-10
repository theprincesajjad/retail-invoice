"""Fixed product categories and SKU prefix batch rules."""

from __future__ import annotations

PRODUCT_CATEGORIES = [
    "Laptops",
    "Desktops",
    "Monitors",
    "Printers",
    "Cell Phones",
    "Tablets",
]

# Longer prefixes first
SKU_CATEGORY_RULES: list[tuple[str, str]] = [
    ("110", "Cell Phones"),
    ("92", "Laptops"),
]


def category_for_sku(sku: str) -> str:
    """Return matching category for a SKU prefix, or empty string."""
    s = (sku or "").strip()
    if not s:
        return ""
    for prefix, category in SKU_CATEGORY_RULES:
        if s.startswith(prefix):
            return category
    return ""
