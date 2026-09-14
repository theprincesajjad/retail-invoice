"""Two-way inventory Excel sync (local working inventory list).

Columns:
  SKU, Status, Product Description, Details, qty, Category, price, date added, date sold
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models import Product
from product_categories import category_for_sku
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


def _category_sort_key(category: str) -> tuple:
    cat = (category or "").strip()
    if not cat:
        return (1, "")  # blank / uncategorized last
    return (0, cat.casefold())


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


def organize_products_for_excel(products: list[Product]) -> list[Product | None]:
    """
    Sort by Category (A→Z), then SKU low→high within each category.
    Insert None placeholders between categories (blank Excel rows for new items).
    """
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
            # Blank gap so new products can be typed between category blocks
            rows.extend([None, None, None])
        rows.append(p)
        prev_cat = cat
    return rows


def write_inventory_excel(path: Path | str, products: list[Product]) -> Path:
    """Rewrite the inventory workbook from current products."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    for col, header in enumerate(SYNC_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)

    for item in organize_products_for_excel(products):
        if item is None:
            ws.append([None] * len(SYNC_HEADERS))
            continue
        p = item
        status = product_status(p)
        sold = (getattr(p, "sold_date", "") or "") if status == STATUS_SOLD else ""
        ws.append([
            p.sku or "",
            status,
            p.name or "",
            p.serial_number or "",
            int(p.qty or 0),
            p.category or "",
            float(p.price or 0),
            getattr(p, "import_date", "") or "",
            sold,
        ])

    widths = {
        "A": 14, "B": 12, "C": 32, "D": 28, "E": 8,
        "F": 14, "G": 10, "H": 14, "I": 14,
    }
    for letter, width in widths.items():
        ws.column_dimensions[letter].width = width

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


def read_sync_rows(path: Path | str) -> list[dict]:
    from openpyxl import load_workbook

    path = Path(path)
    if not path.exists():
        raise ValueError(f"File not found: {path}")

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []

    headers = ["" if c is None else str(c) for c in rows[0]]
    mapping = _map_headers(headers)
    if "Product Description" not in mapping and "SKU" not in mapping:
        raise ValueError(
            "Missing required column: Product Description or SKU.\n"
            f"Expected headings: {', '.join(SYNC_HEADERS)}"
        )

    out: list[dict] = []
    for row_num, row in enumerate(rows[1:], start=2):
        data = list(row) if row else []
        if not data or all(c is None or str(c).strip() == "" for c in data):
            continue
        name = _cell(data, mapping.get("Product Description"))
        sku = _cell(data, mapping.get("SKU"))
        if not name and not sku:
            continue
        out.append({
            "row": row_num,
            "sku": sku,
            "status": _cell(data, mapping.get("Status")),
            "name": name or "Untitled product",
            "serial_number": _cell(data, mapping.get("Details")),
            "qty": _cell(data, mapping.get("qty")),
            "category": _cell(data, mapping.get("Category")),
            "price": _cell(data, mapping.get("price")),
            "import_date": _cell(data, mapping.get("date added")),
            "sold_date": _cell(data, mapping.get("date sold")),
        })
    return out


def _find_by_sku(sku: str) -> Product | None:
    from database import search_products

    sku = (sku or "").strip()
    if not sku:
        return None
    matches = [
        p for p in search_products(sku)
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
            result.errors.append(f"Row {row['row']}: {e}")
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
      1) Pull new/edited rows from Excel into the app (if file exists)
      2) Rewrite Excel from the full current inventory
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
