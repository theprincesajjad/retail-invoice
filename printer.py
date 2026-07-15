import logging
import platform

from database import get_all_settings
from models import Invoice, InvoiceItem
from receipt_builder import (
    build_logo_escpos_bytes,
    build_receipt_text,
    prepare_logo_image,
    resolve_logo_path,
    sample_receipt_invoice,
)

# ESC/POS control bytes
ESC_INIT = b"\x1b\x40"
ESC_BOLD_ON = b"\x1b\x45\x01"
ESC_BOLD_OFF = b"\x1b\x45\x00"
ESC_ALIGN_LEFT = b"\x1b\x61\x00"
ESC_ALIGN_CENTER = b"\x1b\x61\x01"
ESC_DOUBLE_HEIGHT = b"\x1d\x21\x10"
ESC_CHAR_NORMAL = b"\x1d\x21\x00"
ESC_LINE_SPACING_DEFAULT = b"\x1b\x32"
ESC_LINE_SPACING_30 = b"\x1b\x33\x1e"  # compact
ESC_LINE_SPACING_42 = b"\x1b\x33\x2a"  # normal
ESC_LINE_SPACING_54 = b"\x1b\x33\x36"  # roomy
ESC_FEED_LINES = b"\x1b\x64\x06"
ESC_CUT = b"\x1d\x56\x00"

LOGO_PRINT_WIDTH = 512


def _line_spacing(settings: dict) -> bytes:
    spacing = settings.get("receipt_header_spacing", "normal")
    if spacing == "compact":
        return ESC_LINE_SPACING_30
    if spacing == "roomy":
        return ESC_LINE_SPACING_54
    return ESC_LINE_SPACING_42


def _large_titles(settings: dict) -> bool:
    return settings.get("receipt_font_size", "normal") == "large"


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


def _header_skip_set(settings: dict) -> set[str]:
    business = settings.get("business_name", "My Business").strip().upper()
    return {
        business,
        settings.get("business_tagline", "").strip(),
        settings.get("business_address", "").strip(),
        settings.get("business_website", "").strip(),
        settings.get("business_phone", "").strip(),
        settings.get("business_email", "").strip(),
        "SALES RECEIPT",
        "Tax Receipt",
    }


def _clean_body(invoice: Invoice, items: list[InvoiceItem], settings: dict) -> str:
    body = build_receipt_text(invoice, items, settings)
    skip = _header_skip_set(settings)
    cleaned_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped in skip:
            continue
        if not stripped and cleaned_lines and not cleaned_lines[-1].strip():
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).lstrip("\n")


def _build_escpos_bytes(invoice: Invoice, items: list[InvoiceItem], settings: dict) -> bytes:
    large = _large_titles(settings)
    chunks: list[bytes] = [
        ESC_INIT,
        _line_spacing(settings),
    ]

    logo_path = resolve_logo_path(settings)
    if logo_path:
        try:
            chunks.append(build_logo_escpos_bytes(logo_path, max_width=LOGO_PRINT_WIDTH))
        except Exception as e:
            logging.warning(f"Logo skipped: {e}")

    # Print body at NORMAL character size so columns stay aligned.
    # Optional double-height only for store name + title.
    body = build_receipt_text(invoice, items, settings)
    chunks.extend([ESC_ALIGN_LEFT, ESC_CHAR_NORMAL, _encode_text(body)])

    # When large titles are preferred, reprint is handled in escpos path;
    # raw path keeps monospace integrity with normal size for the whole receipt.
    _ = large

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
    printer._raw(ESC_INIT + _line_spacing(settings))
    large = _large_titles(settings)

    logo_path = resolve_logo_path(settings)
    if logo_path:
        try:
            printer.set(align="center")
            logo_img = prepare_logo_image(logo_path, max_width=LOGO_PRINT_WIDTH)
            printer.image(logo_img)
            printer.text("\n")
        except Exception as e:
            logging.warning(f"Logo skipped: {e}")

    # Prefer printing the designed monospace layout at normal size so Item/Qty/Price/Total
    # columns never wrap. Large mode only enlarges the store name and SALES RECEIPT title.
    if large:
        business = settings.get("business_name", "My Business").strip().upper()
        if business and str(settings.get("receipt_show_business_name", "1")) not in ("0", "false", ""):
            printer.set(align="center", bold=True, height=2, width=1)
            printer.text(business + "\n")
            printer.set(bold=False, height=1, width=1)

        tagline = settings.get("business_tagline", "").strip()
        if tagline and str(settings.get("receipt_show_tagline", "1")) not in ("0", "false", ""):
            printer.set(align="center")
            printer.text(tagline + "\n")

        for field, key in (
            ("business_address", "receipt_show_address"),
            ("business_phone", "receipt_show_phone"),
            ("business_website", "receipt_show_website"),
            ("business_email", "receipt_show_email"),
        ):
            if str(settings.get(key, "1")) in ("0", "false", ""):
                continue
            value = settings.get(field, "").strip()
            if value:
                printer.set(align="center")
                printer.text(value + "\n")

        printer.text("\n")
        printer.set(align="center", bold=True, height=2, width=1)
        printer.text("SALES RECEIPT\n")
        printer.set(bold=False, height=1, width=1)
        printer.text("\n")

        printer.set(align="left", height=1, width=1)
        printer.text(_clean_body(invoice, items, settings) + "\n")
    else:
        printer.set(align="left", height=1, width=1)
        printer.text(build_receipt_text(invoice, items, settings) + "\n")

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

    try:
        return _print_with_escpos(printer_name, invoice, items, settings)
    except Exception as e:
        errors.append(f"escpos: {e}")
        logging.error(f"escpos print failed: {e}")

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
    settings = get_all_settings()
    invoice, items = sample_receipt_invoice(settings)
    return print_receipt(invoice, items)


def print_text_document(title: str, body: str) -> tuple[bool, str]:
    """Print a plain monospace document (inventory list, etc.) to the receipt printer."""
    settings = get_all_settings()
    requested = settings.get("printer_name", "").strip()
    printer_name = resolve_printer_name(requested)

    if not printer_name:
        return False, "No printer selected. Open Setup and choose your Epson TM-T20."

    if platform.system() != "Windows":
        return False, "Printing is only supported on Windows."

    installed = _list_windows_printers()
    if installed and printer_name not in installed:
        return False, f"Printer not found: {printer_name}"

    text = (body or "").rstrip() + "\n\n\n"
    data = ESC_INIT + _line_spacing(settings) + ESC_ALIGN_LEFT + ESC_CHAR_NORMAL
    data += _encode_text(text)
    data += ESC_FEED_LINES + ESC_CUT

    errors: list[str] = []
    try:
        from escpos.printer import Win32Raw

        printer = Win32Raw(printer_name)
        printer._raw(ESC_INIT + _line_spacing(settings))
        printer.set(align="left", height=1, width=1)
        printer.text(text)
        try:
            printer.cut()
        except Exception as e:
            logging.warning(f"Cut command skipped: {e}")
        printer.close()
        return True, f"Printed {title}"
    except Exception as e:
        errors.append(f"escpos: {e}")
        logging.error(f"escpos inventory print failed: {e}")

    try:
        datatype = _get_raw_datatype(printer_name)
        ok, msg = _print_bytes_win32(printer_name, data, datatype)
        if ok:
            return True, f"Printed {title}"
        errors.append(f"RAW ({datatype}): {msg}")
    except Exception as e:
        errors.append(f"RAW: {e}")

    try:
        ok, msg = _print_bytes_win32(printer_name, _encode_text(text), "TEXT")
        if ok:
            return True, f"Printed {title}"
        errors.append(f"TEXT: {msg}")
    except Exception as e:
        errors.append(f"TEXT: {e}")

    detail = errors[0] if errors else "Unknown print error"
    return False, f"Could not print to '{printer_name}'. {detail}"


def print_inventory_list() -> tuple[bool, str]:
    from inventory_list import build_inventory_list_text

    return print_text_document("Inventory list", build_inventory_list_text())
