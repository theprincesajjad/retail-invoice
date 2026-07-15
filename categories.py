"""Product category helpers — defaults plus custom categories from Setup."""

from __future__ import annotations

import json

DEFAULT_CATEGORIES = [
    "Cell Phones",
    "Laptops",
    "Desktops",
    "Monitors",
    "Printers",
    "Accessories",
    "Other",
]

SETTING_KEY = "product_categories"


def parse_categories(raw: str | None) -> list[str]:
    """Parse stored categories JSON (or newline list). Falls back to defaults."""
    text = (raw or "").strip()
    if not text:
        return list(DEFAULT_CATEGORIES)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            cats = [str(c).strip() for c in data if str(c).strip()]
            return cats or list(DEFAULT_CATEGORIES)
    except json.JSONDecodeError:
        pass
    cats = [line.strip() for line in text.splitlines() if line.strip()]
    return cats or list(DEFAULT_CATEGORIES)


def serialize_categories(categories: list[str]) -> str:
    cleaned: list[str] = []
    seen = set()
    for c in categories:
        name = (c or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return json.dumps(cleaned)


def get_product_categories() -> list[str]:
    from database import get_setting

    return parse_categories(get_setting(SETTING_KEY, ""))


def save_product_categories(categories: list[str]) -> list[str]:
    from database import save_setting

    cleaned = parse_categories(serialize_categories(categories))
    # Ensure defaults remain available even if user clears everything
    if not cleaned:
        cleaned = list(DEFAULT_CATEGORIES)
    save_setting(SETTING_KEY, serialize_categories(cleaned))
    return cleaned


def normalize_category(name: str, allowed: list[str] | None = None) -> str:
    """Match a category case-insensitively; unknown names are kept as typed."""
    raw = (name or "").strip()
    if not raw:
        return "Other"
    cats = allowed or get_product_categories()
    for c in cats:
        if c.lower() == raw.lower():
            return c
    return raw
