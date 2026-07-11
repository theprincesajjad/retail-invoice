import logging
import platform

from database import get_all_settings
from models import Invoice, InvoiceItem
from receipt_builder import (
    build_logo_escpos_bytes,
    build_receipt_text,
    prepare_logo_image,
    resolve_logo_path,
)

# ESC/POS control bytes
ESC_INIT = b"\x1b\x40"
ESC_BOLD_ON = b"\x1b\x45\x01"
ESC_BOLD_OFF = b"\x1b\x45\x00"
ESC_ALIGN_LEFT = b"\x1b\x61\x00"
ESC_ALIGN_CENTER = b"\x1b\x61\x01"
ESC_DOUBLE_HEIGHT = b"\x1d\x21\x10"  # taller body text
ESC_CHAR_NORMAL = b"\x1d\x21\x00"
ESC_LINE_SPACING_DEFAULT = b"\x1b\x32"
ESC_LINE_SPACING_54 = b"\x1b\x33\x36"  # 54 dots — roomier than default
ESC_FEED_LINES = b"\x1b\x64\x06"
ESC_CUT = b"\x1d\x56\x00"

LOGO_PRINT_WIDTH = 512


def _list_windows_printers() -> list[str]:
    if platform.system() != "Windows":
        return []
    try:
        import win32print  # type: ignore

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(flags) if p[2]]
    except Exception:
        return []


def resolve_printer_name(requested: str) -> str:
    requested = (requested or "").strip()
    if not requested:
        return ""

    installed = _list_windows_printers()
    if not installed:
        return requested

    if requested in installed:
        return requested

    req_lower = requested.lower()
    for name in installed:
        if name.lower() == req_lower:
            return name

    for name in installed:
        lower = name.lower()
        if "tm-t20" in lower or "tm t20" in lower:
            return name
        if req_lower in lower or lower in req_lower:
            return name

    return requested


def _get_raw_datatype(printer_name: str) -> str:
    if platform.system() != "Windows":
        return "RAW"
    try:
        import win32print  # type: ignore

        handle = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(handle, 2)
            driver_name = info.get("pDriverName", "")
        finally:
            win32print.ClosePrinter(handle)

        drivers = win32print.EnumPrinterDrivers(None, None, 2)
        for driver in drivers:
            if driver.get("Name") == driver_name and driver.get("Version", 0) == 4:
                return "XPS_PASS"
    except Exception as e:
        logging.debug(f"Driver version lookup failed: {e}")
    return "RAW"


def _encode_text(text: str) -> bytes:
    for encoding in ("cp437", "latin-1", "utf-8"):
        try:
            return text.encode(encoding)
        except UnicodeEncodeError:
            continue
    return text.encode("utf-8", errors="replace")


def _build_escpos_bytes(invoice: Invoice, items: list[InvoiceItem], settings: dict) -> bytes:
    chunks: list[bytes] = [
        ESC_INIT,
        ESC_LINE_SPACING_54,
    ]

    logo_path = resolve_logo_path(settings)
    if logo_path:
        try:
            chunks.append(build_logo_escpos_bytes(logo_path, max_width=LOGO_PRINT_WIDTH))
        except Exception as e:
            logging.warning(f"Logo skipped: {e}")

    business = settings.get("business_name", "My Business").strip().upper()
    chunks.extend([
        ESC_ALIGN_CENTER,
        ESC_DOUBLE_HEIGHT,
        ESC_BOLD_ON,
        _encode_text(business + "\n"),
        ESC_BOLD_OFF,
        ESC_CHAR_NORMAL,
    ])

    tagline = settings.get("business_tagline", "").strip()
    if tagline:
        chunks.append(_encode_text(tagline + "\n\n"))
    else:
        chunks.append(_encode_text("\n"))

    for field in ("business_address", "business_website", "business_phone", "business_email"):
        value = settings.get(field, "").strip()
        if value:
            chunks.append(_encode_text(value + "\n\n"))

    chunks.extend([ESC_BOLD_ON, ESC_DOUBLE_HEIGHT, _encode_text("SALES RECEIPT\n"), ESC_CHAR_NORMAL, ESC_BOLD_OFF, _encode_text("\n")])

    body = build_receipt_text(invoice, items, settings)
    # Skip duplicate header lines already printed above (logo + business block).
    skip_prefixes = (
        business,
        tagline,
        settings.get("business_address", "").strip(),
        settings.get("business_website", "").strip(),
        settings.get("business_phone", "").strip(),
        settings.get("business_email", "").strip(),
        "SALES RECEIPT",
        "Tax Receipt",
    )
    cleaned_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped in skip_prefixes:
            continue
        if not stripped and cleaned_lines and not cleaned_lines[-1].strip():
            continue
        cleaned_lines.append(line)
    cleaned_body = "\n".join(cleaned_lines).lstrip("\n")

    chunks.extend([ESC_ALIGN_LEFT, ESC_DOUBLE_HEIGHT, _encode_text(cleaned_body)])
    chunks.extend([
        ESC_CHAR_NORMAL,
        ESC_LINE_SPACING_DEFAULT,
        ESC_FEED_LINES,
        ESC_CUT,
    ])
    return b"".join(chunks)


def _print_bytes_win32(printer_name: str, data: bytes, datatype: str) -> tuple[bool, str]:
    import win32print  # type: ignore

    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("Retail Invoice Receipt", None, datatype))
        try:
            win32print.StartPagePrinter(handle)
            written = win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
            if not written:
                return False, "Printer accepted no data."
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
    return True, "Printed"


def _print_with_escpos(printer_name: str, invoice: Invoice, items: list[InvoiceItem], settings: dict) -> tuple[bool, str]:
    from escpos.printer import Win32Raw

    printer = Win32Raw(printer_name)
    printer._raw(ESC_INIT + ESC_LINE_SPACING_54)

    logo_path = resolve_logo_path(settings)
    if logo_path:
        try:
            printer.set(align="center")
            logo_img = prepare_logo_image(logo_path, max_width=LOGO_PRINT_WIDTH)
            printer.image(logo_img)
            printer.text("\n")
        except Exception as e:
            logging.warning(f"Logo skipped: {e}")

    business = settings.get("business_name", "My Business").strip().upper()
    printer.set(align="center", bold=True, height=2, width=1)
    printer.text(business + "\n")
    printer.set(bold=False, height=1, width=1)

    tagline = settings.get("business_tagline", "").strip()
    if tagline:
        printer.text(tagline + "\n")
    printer.text("\n")

    for field in ("business_address", "business_website", "business_phone", "business_email"):
        value = settings.get(field, "").strip()
        if value:
            printer.text(value + "\n\n")

    printer.set(bold=True, height=2, width=1)
    printer.text("SALES RECEIPT\n")
    printer.set(bold=False, height=1, width=1)
    printer.text("\n")

    printer.set(align="left", height=2, width=1)
    body = build_receipt_text(invoice, items, settings)
    skip = {
        business,
        tagline,
        settings.get("business_address", "").strip(),
        settings.get("business_website", "").strip(),
        settings.get("business_phone", "").strip(),
        settings.get("business_email", "").strip(),
        "SALES RECEIPT",
        "Tax Receipt",
    }
    lines = []
    for line in body.splitlines():
        if line.strip() in skip:
            continue
        lines.append(line)
    printer.text("\n".join(lines).lstrip("\n") + "\n")
    printer.set(height=1, width=1)

    try:
        printer.cut()
    except Exception as e:
        logging.warning(f"Cut command skipped: {e}")
    printer.close()
    return True, "Printed"


def print_receipt(invoice: Invoice, items: list[InvoiceItem]) -> tuple[bool, str]:
    settings = get_all_settings()
    requested = settings.get("printer_name", "").strip()
    printer_name = resolve_printer_name(requested)

    if not printer_name:
        return False, "No printer selected. Open Settings and choose your Epson TM-T20."

    if platform.system() != "Windows":
        return False, "Printing is only supported on Windows."

    installed = _list_windows_printers()
    if installed and printer_name not in installed:
        return False, f"Printer not found: {printer_name}"

    errors: list[str] = []

    # 1) escpos handles logos and formatting best on Epson TM-T20
    try:
        return _print_with_escpos(printer_name, invoice, items, settings)
    except Exception as e:
        errors.append(f"escpos: {e}")
        logging.error(f"escpos print failed: {e}")

    # 2) Raw ESC/POS with embedded logo raster
    try:
        datatype = _get_raw_datatype(printer_name)
        data = _build_escpos_bytes(invoice, items, settings)
        ok, msg = _print_bytes_win32(printer_name, data, datatype)
        if ok:
            return True, msg
        errors.append(f"RAW ({datatype}): {msg}")
    except Exception as e:
        errors.append(f"RAW: {e}")
        logging.error(f"RAW print failed: {e}")

    # 3) Plain text through Windows driver
    try:
        text = build_receipt_text(invoice, items, settings) + "\n\n\n"
        ok, msg = _print_bytes_win32(printer_name, _encode_text(text), "TEXT")
        if ok:
            return True, msg
        errors.append(f"TEXT: {msg}")
    except Exception as e:
        errors.append(f"TEXT: {e}")
        logging.error(f"TEXT print failed: {e}")

    detail = errors[0] if errors else "Unknown print error"
    return False, f"Could not print to '{printer_name}'. {detail}"


def print_test_receipt() -> tuple[bool, str]:
    """Print a sample receipt to verify printer setup."""
    from datetime import datetime
    from models import Invoice, InvoiceItem

    settings = get_all_settings()
    invoice = Invoice(
        id=None,
        invoice_number="TEST-0001",
        customer_name="Test Customer",
        customer_phone="(416) 555-0100",
        subtotal=29.99,
        tax_rate=float(settings.get("tax_rate", "0.13")),
        tax_amount=3.90,
        total=33.89,
        payment_method="Cash",
        notes="",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        items=[],
        discount_type="",
        discount_value=0,
        discount_amount=0,
    )
    items = [
        InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description="Sample Product", serial_number="",
            qty=1, unit_price=29.99, line_total=29.99,
        ),
    ]
    return print_receipt(invoice, items)
