"""Two-way inventory Excel sync (local working inventory list).

Workbook layout: one worksheet tab per product category. Sync always
ensures tabs exist for every built-in category (plus any extra categories
from the database). New products typed into a tab inherit that category.

Columns:
  SKU, Status, Product Description, Details, qty, Category, price, date added, date sold
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models import Product
from product_categories import PRODUCT_CATEGORIES, category_for_sku
from product_import import _parse_price, _parse_qty, today_date_stamp

SYNC_HEADERS = [
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

STATUS_IN_STOCK = "In-Stock"
STATUS_SOLD = "Sold"

UNCATEGORIZED_SHEET = "Uncategorized"
BLANK_ROWS_PER_SHEET = 5  # empty rows at end of each tab for typing new SKUs

_HEADER_ALIASES = {
    "sku": "SKU",
    "code": "SKU",
    "product sku": "SKU",
    "status": "Status",
    "product description": "Product Description",
    "description": "Product Description",
    "product name": "Product Description",
    "name": "Product Description",
    "details": "Details",
    "detail": "Details",
    "serial": "Details",
    "serial number": "Details",
    "qty": "qty",
    "quantity": "qty",
    "stock": "qty",
    "category": "Category",
    "catagory": "Category",
    "cat": "Category",
    "price": "price",
    "unit price": "price",
    "date added": "date added",
    "date stamp": "date added",
    "import date": "date added",
    "date sold": "date sold",
    "sold date": "date sold",
    "sold": "date sold",
}

_SHEET_TITLE_FORBIDDEN = set('\\/?*[]:')


@dataclass
class SyncResult:
    path: Path
    added: int = 0
    updated: int = 0
    exported: int = 0
    created_file: bool = False
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def default_inventory_excel_path() -> Path:
    from config import DATA_DIR

    return Path(DATA_DIR) / "inventory.xlsx"


def resolve_inventory_excel_path(path: str | Path | None = None) -> Path:
    from database import get_setting

    if path:
        return Path(path)
    stored = (get_setting("inventory_excel_path") or "").strip()
    if stored:
        return Path(stored)
    return default_inventory_excel_path()


def product_status(product: Product) -> str:
    return STATUS_IN_STOCK if int(getattr(product, "qty", 0) or 0) > 0 else STATUS_SOLD


def sheet_title_for_category(category: str) -> str:
    """Excel-safe worksheet title for a category (max 31 chars)."""
    raw = (category or "").strip() or UNCATEGORIZED_SHEET
    cleaned = "".join("_" if ch in _SHEET_TITLE_FORBIDDEN else ch for ch in raw)
    cleaned = cleaned.strip() or UNCATEGORIZED_SHEET
    return cleaned[:31]


def category_for_sheet_title(title: str) -> str:
    """Map a worksheet title back to a category name."""
    name = (title or "").strip()
    if not name or name.casefold() == UNCATEGORIZED_SHEET.casefold():
        return ""
    # Prefer the canonical PRODUCT_CATEGORIES spelling when titles match
    for cat in PRODUCT_CATEGORIES:
        if sheet_title_for_category(cat).casefold() == name.casefold():
            return cat
    return name


def _sku_sort_key(sku: str) -> tuple:
    """Sort SKUs low → high (numeric when possible)."""
    text = (sku or "").strip()
    if not text:
        return (1, 0, "")
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        try:
            return (0, int(digits), text.casefold())
        except ValueError:
            pass
    return (1, 0, text.casefold())


def organize_products_for_sheet(products: list[Product]) -> list[Product]:
    """Sort products by SKU low→high within a single category sheet."""
    return sorted(products, key=lambda p: _sku_sort_key(p.sku or ""))


def organize_products_for_excel(products: list[Product]) -> list[Product | None]:
    """
    Legacy helper: flat list sorted by category then SKU, with blank gaps.

    Prefer category_sheet_plan() / per-sheet tabs for new workbooks.
    """
    def _category_sort_key(category: str) -> tuple:
        cat = (category or "").strip()
        if not cat:
            return (1, "")
        return (0, cat.casefold())

    ordered = sorted(
        products,
        key=lambda p: (_category_sort_key(getattr(p, "category", "") or ""), _sku_sort_key(p.sku or "")),
    )
    if not ordered:
        return []

    rows: list[Product | None] = []
    prev_cat = None
    for p in ordered:
        cat = (getattr(p, "category", "") or "").strip().casefold()
        if prev_cat is not None and cat != prev_cat:
            rows.extend([None, None, None])
        rows.append(p)
        prev_cat = cat
    return rows


def category_sheet_plan(products: list[Product]) -> list[tuple[str, list[Product]]]:
    """
    Ordered (sheet_title, products) pairs for the workbook.

    Always includes every PRODUCT_CATEGORIES tab (empty if needed), then any
    extra categories found on products, then Uncategorized when needed.
    """
    by_cat: dict[str, list[Product]] = {}
    for p in products:
        cat = (getattr(p, "category", "") or "").strip()
        key = cat if cat else ""
        by_cat.setdefault(key, []).append(p)

    plan: list[tuple[str, list[Product]]] = []
    seen_titles: set[str] = set()

    for cat in PRODUCT_CATEGORIES:
        title = sheet_title_for_category(cat)
        if title.casefold() in seen_titles:
            continue
        seen_titles.add(title.casefold())
        items = organize_products_for_sheet(by_cat.pop(cat, []))
        # Also claim products whose category matches case-insensitively
        for key in list(by_cat.keys()):
            if key and key.casefold() == cat.casefold():
                items.extend(by_cat.pop(key))
        items = organize_products_for_sheet(items)
        plan.append((title, items))

    extras = sorted(
        (k for k in by_cat.keys() if k),
        key=lambda c: c.casefold(),
    )
    for cat in extras:
        title = sheet_title_for_category(cat)
        # Avoid colliding with a built-in tab title
        base = title
        n = 2
        while title.casefold() in seen_titles:
            suffix = f" ({n})"
            title = (base[: 31 - len(suffix)] + suffix)[:31]
            n += 1
        seen_titles.add(title.casefold())
        plan.append((title, organize_products_for_sheet(by_cat.pop(cat))))

    uncategorized = by_cat.pop("", [])
    # Any leftovers (shouldn't happen)
    for leftover in by_cat.values():
        uncategorized.extend(leftover)
    if uncategorized or UNCATEGORIZED_SHEET.casefold() not in seen_titles:
        # Only add Uncategorized tab when there are uncategorized products,
        # or keep it if it was already present — always add when products exist
        # without a category. Skip empty Uncategorized to keep the workbook tidy
        # unless the user already had one (handled on read). For export we only
        # create it when needed.
        if uncategorized:
            title = sheet_title_for_category(UNCATEGORIZED_SHEET)
            if title.casefold() not in seen_titles:
                plan.append((title, organize_products_for_sheet(uncategorized)))

    return plan


def _write_sheet_header(ws) -> None:
    from openpyxl.styles import Font

    for col, header in enumerate(SYNC_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)


def _append_product_row(ws, product: Product, category_label: str) -> None:
    status = product_status(product)
    sold = (getattr(product, "sold_date", "") or "") if status == STATUS_SOLD else ""
    ws.append([
        product.sku or "",
        status,
        product.name or "",
        product.serial_number or "",
        int(product.qty or 0),
        category_label or (product.category or ""),
        float(product.price or 0),
        getattr(product, "import_date", "") or "",
        sold,
    ])


def _set_column_widths(ws) -> None:
    widths = {
        "A": 14, "B": 12, "C": 32, "D": 28, "E": 8,
        "F": 14, "G": 10, "H": 14, "I": 14,
    }
    for letter, width in widths.items():
        ws.column_dimensions[letter].width = width


def write_inventory_excel(path: Path | str, products: list[Product]) -> Path:
    """Rewrite the inventory workbook — one tab per category."""
    from openpyxl import Workbook

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    plan = category_sheet_plan(products)
    wb = Workbook()
    # Remove the default sheet after creating the first category tab
    default = wb.active

    for index, (title, items) in enumerate(plan):
        if index == 0:
            ws = default
            ws.title = title
        else:
            ws = wb.create_sheet(title)
        _write_sheet_header(ws)
        category_label = category_for_sheet_title(title)
        for p in items:
            _append_product_row(ws, p, category_label)
        for _ in range(BLANK_ROWS_PER_SHEET):
            ws.append([None] * len(SYNC_HEADERS))
        _set_column_widths(ws)

    if not plan:
        # Shouldn't happen (PRODUCT_CATEGORIES is non-empty), but keep a stub
        default.title = sheet_title_for_category(PRODUCT_CATEGORIES[0])
        _write_sheet_header(default)
        _set_column_widths(default)

    wb.save(path)
    return path


def _normalize_header(raw: str) -> str | None:
    key = (raw or "").strip().lower()
    return _HEADER_ALIASES.get(key)


def _map_headers(raw_headers) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, h in enumerate(raw_headers):
        canon = _normalize_header(str(h) if h is not None else "")
        if canon and canon not in mapping:
            mapping[canon] = i
    return mapping


def _cell(row: list, index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    val = row[index]
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


def _rows_from_worksheet(ws, sheet_category: str) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = ["" if c is None else str(c) for c in rows[0]]
    mapping = _map_headers(headers)
    if "Product Description" not in mapping and "SKU" not in mapping:
        return []

    out: list[dict] = []
    for row_num, row in enumerate(rows[1:], start=2):
        data = list(row) if row else []
        if not data or all(c is None or str(c).strip() == "" for c in data):
            continue
        name = _cell(data, mapping.get("Product Description"))
        sku = _cell(data, mapping.get("SKU"))
        if not name and not sku:
            continue
        category = _cell(data, mapping.get("Category")) or sheet_category
        out.append({
            "row": row_num,
            "sheet": ws.title,
            "sku": sku,
            "status": _cell(data, mapping.get("Status")),
            "name": name or "Untitled product",
            "serial_number": _cell(data, mapping.get("Details")),
            "qty": _cell(data, mapping.get("qty")),
            "category": category,
            "price": _cell(data, mapping.get("price")),
            "import_date": _cell(data, mapping.get("date added")),
            "sold_date": _cell(data, mapping.get("date sold")),
        })
    return out


def read_sync_rows(path: Path | str) -> list[dict]:
    """Read product rows from every category tab in the workbook."""
    from openpyxl import load_workbook

    path = Path(path)
    if not path.exists():
        raise ValueError(f"File not found: {path}")

    wb = load_workbook(path, read_only=True, data_only=True)
    out: list[dict] = []
    try:
        for ws in wb.worksheets:
            sheet_category = category_for_sheet_title(ws.title)
            out.extend(_rows_from_worksheet(ws, sheet_category))
    finally:
        wb.close()

    if not out:
        # Distinguish empty workbook vs wrong layout: require at least one
        # sheet with recognizable headers when the file has any sheets.
        wb2 = load_workbook(path, read_only=True, data_only=True)
        try:
            has_header = False
            for ws in wb2.worksheets:
                rows = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))
                if not rows:
                    continue
                mapping = _map_headers(["" if c is None else str(c) for c in rows[0]])
                if "Product Description" in mapping or "SKU" in mapping:
                    has_header = True
                    break
        finally:
            wb2.close()
        if not has_header:
            raise ValueError(
                "Missing required column: Product Description or SKU.\n"
                f"Expected headings on each category tab: {', '.join(SYNC_HEADERS)}"
            )
    return out


def _find_by_sku(sku: str) -> Product | None:
    from database import search_products

    sku = (sku or "").strip()
    if not sku:
        return None
    matches = [
        p for p in search_products(sku, stock="All items")
        if (p.sku or "").strip().lower() == sku.lower()
    ]
    return matches[0] if matches else None


def pull_inventory_excel(path: Path | str) -> SyncResult:
    """Import new/changed rows from the Excel file into the database."""
    from database import add_product, update_product

    path = Path(path)
    result = SyncResult(path=path)
    try:
        rows = read_sync_rows(path)
    except ValueError as e:
        result.errors.append(str(e))
        return result

    for row in rows:
        try:
            price = _parse_price(row["price"])
            qty = _parse_qty(row["qty"]) if (row.get("qty") or "").strip() != "" else None
            if price < 0:
                raise ValueError("price cannot be negative")
            if qty is not None and qty < 0:
                raise ValueError("qty cannot be negative")
        except ValueError as e:
            sheet = row.get("sheet") or ""
            loc = f"{sheet} row {row['row']}" if sheet else f"Row {row['row']}"
            result.errors.append(f"{loc}: {e}")
            continue

        status = (row.get("status") or "").strip()
        status_l = status.lower()
        sold_date = (row.get("sold_date") or "").strip()
        import_date = (row.get("import_date") or "").strip() or today_date_stamp()

        if status_l in ("sold", "sale"):
            if qty is None:
                qty = 0
            qty = 0
            sold_date = sold_date or today_date_stamp()
        else:
            if qty is None:
                qty = 1
            if qty > 0:
                sold_date = ""
            elif not sold_date:
                sold_date = today_date_stamp()

        category = (row.get("category") or "").strip()
        if not category:
            category = category_for_sku(row["sku"])

        product = Product(
            id=None,
            name=row["name"],
            serial_number=row["serial_number"],
            sku=row["sku"],
            price=price,
            qty=qty,
            category=category,
            created_at="",
            import_date=import_date,
            sold_date=sold_date,
        )

        existing = _find_by_sku(product.sku)
        if existing:
            product.id = existing.id
            # Keep app sold_date if excel blank but qty is zero
            if product.qty <= 0 and not product.sold_date:
                product.sold_date = getattr(existing, "sold_date", "") or today_date_stamp()
            if product.qty > 0:
                product.sold_date = ""
            update_product(product)
            result.updated += 1
        else:
            if not product.sku and not product.name:
                continue
            add_product(product)
            result.added += 1

    return result


def export_inventory_excel(path: Path | str | None = None) -> SyncResult:
    """Write current DB inventory to the Excel file (create if missing)."""
    from database import list_all_products, save_setting

    path = resolve_inventory_excel_path(path)
    created = not path.exists()
    products = list_all_products()
    write_inventory_excel(path, products)
    save_setting("inventory_excel_path", str(path))
    return SyncResult(path=path, exported=len(products), created_file=created)


def sync_inventory_excel(path: Path | str | None = None) -> SyncResult:
    """
    Two-way sync:
      1) Pull new/edited rows from every category tab into the app (if file exists)
      2) Rewrite Excel with one tab per category (adding missing category tabs)
    """
    from database import save_setting

    path = resolve_inventory_excel_path(path)
    save_setting("inventory_excel_path", str(path))

    if not path.exists():
        out = export_inventory_excel(path)
        out.created_file = True
        return out

    pull = pull_inventory_excel(path)
    out = export_inventory_excel(path)
    out.added = pull.added
    out.updated = pull.updated
    out.errors = pull.errors
    return out


def try_auto_export_inventory_excel() -> None:
    """Best-effort rewrite of the configured inventory Excel after stock changes."""
    try:
        path = resolve_inventory_excel_path()
        if not path.exists() and not (path.parent.exists()):
            return
        # Always keep the configured workbook current when it exists,
        # or create it on first sale if a path was saved.
        from database import get_setting

        configured = (get_setting("inventory_excel_path") or "").strip()
        if not configured and not path.exists():
            return
        export_inventory_excel(path)
    except Exception:
        # Never block a sale if Excel is locked / missing openpyxl / etc.
        pass
