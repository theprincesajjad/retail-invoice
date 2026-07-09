import logging
import os
import platform

from database import get_all_settings
from models import Invoice, InvoiceItem
from utils import format_currency
from config import DATA_DIR, ASSETS_DIR

# ESC/POS control bytes
ESC_INIT = b"\x1b\x40"
ESC_BOLD_ON = b"\x1b\x45\x01"
ESC_BOLD_OFF = b"\x1b\x45\x00"
ESC_ALIGN_LEFT = b"\x1b\x61\x00"
ESC_ALIGN_CENTER = b"\x1b\x61\x01"
ESC_ALIGN_RIGHT = b"\x1b\x61\x02"
ESC_CUT = b"\x1d\x56\x00"
ESC_FEED = b"\n"


def get_printer_width_chars(width_setting: str) -> int:
    return 32 if width_setting == "58mm" else 48


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
    """Match saved printer name to an installed Windows printer."""
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

    # Epson TM-T20 is often listed with extra suffixes in Windows.
    for name in installed:
        lower = name.lower()
        if "tm-t20" in lower or "tm t20" in lower:
            return name
        if req_lower in lower or lower in req_lower:
            return name

    return requested


def _get_raw_datatype(printer_name: str) -> str:
    """Windows 11 v4 drivers often need XPS_PASS instead of RAW."""
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
            if driver.get("Name") == driver_name:
                if driver.get("Version", 0) == 4:
                    return "XPS_PASS"
                break
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


def _resolve_logo_path(settings: dict) -> str:
    logo_path = settings.get("logo_path", "")
    if logo_path and os.path.exists(logo_path):
        return logo_path

    if not logo_path:
        logo_path = ""

    base = os.path.basename(logo_path) if logo_path else ""
    for candidate in (
        DATA_DIR / "logo.png",
        DATA_DIR / "logo.jpg",
        DATA_DIR / "logo.bmp",
        DATA_DIR / base if base else DATA_DIR / "logo.png",
        ASSETS_DIR / "logo.png",
        ASSETS_DIR / base if base else ASSETS_DIR / "logo.png",
    ):
        try:
            if candidate and os.path.exists(candidate):
                return str(candidate)
        except Exception:
            pass
    return ""


def build_receipt_plaintext(invoice: Invoice, items: list[InvoiceItem], settings: dict) -> str:
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    rule = "-" * width
    lines: list[str] = []

    def center(text: str) -> str:
        text = text.strip()
        if len(text) >= width:
            return text[:width]
        pad = (width - len(text)) // 2
        return " " * pad + text

    lines.append(center(settings.get("business_name", "My Business")))
    lines.append(center(settings.get("business_address", "")))
    lines.append(center(f"Tel: {settings.get('business_phone', '')}"))
    lines.append(center(f"GST/HST#: {settings.get('gst_number', '')}"))
    lines.append(rule)
    lines.append(f"Invoice: {invoice.invoice_number}")
    lines.append(f"Date: {invoice.created_at if invoice.created_at else 'Just now'}")
    if invoice.customer_name:
        lines.append(f"Customer: {invoice.customer_name}")
    if invoice.customer_phone:
        lines.append(f"Phone: {invoice.customer_phone}")
    lines.append(rule)

    for item in items:
        line_total_str = format_currency(item.line_total)
        desc_str = item.description
        if item.qty > 1:
            desc_str = f"{item.qty}x {desc_str}"
        max_desc_len = width - len(line_total_str) - 1
        if len(desc_str) > max_desc_len:
            desc_str = desc_str[: max_desc_len - 3] + "..."
        spaces = width - len(desc_str) - len(line_total_str)
        lines.append(f"{desc_str}{' ' * spaces}{line_total_str}")
        if item.serial_number:
            lines.append(f"  S/N: {item.serial_number}")

    lines.append(rule)
    subtotal_str = format_currency(invoice.subtotal)
    tax_str = format_currency(invoice.tax_amount)
    total_str = format_currency(invoice.total)
    tax_rate_pct = int(invoice.tax_rate * 100)

    lines.append(f"{'Subtotal:':<{width - 10}}{subtotal_str:>10}")
    if getattr(invoice, "discount_amount", 0) and invoice.discount_amount > 0:
        disc_str = format_currency(invoice.discount_amount)
        if invoice.discount_type == "percent":
            lines.append(f"{'Discount (' + str(invoice.discount_value).rstrip('0').rstrip('.') + '%):':<{width - 10}}{disc_str:>10}")
        else:
            lines.append(f"{'Discount:':<{width - 10}}{disc_str:>10}")
    lines.append(f"{f'HST ({tax_rate_pct}%):':<{width - 10}}{tax_str:>10}")
    lines.append(f"{'TOTAL:':<{width - 10}}{total_str:>10}")
    lines.append(f"{'Payment:':<{width - 10}}{invoice.payment_method:>10}")
    lines.append(rule)
    lines.append(center("Thank you!"))
    lines.append(center("Please come again"))
    lines.append("")
    return "\n".join(lines)


def _build_escpos_bytes(invoice: Invoice, items: list[InvoiceItem], settings: dict) -> bytes:
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))
    business = settings.get("business_name", "My Business")
    chunks: list[bytes] = [ESC_INIT]

    chunks.extend([ESC_ALIGN_CENTER, ESC_BOLD_ON, _encode_text(business + "\n"), ESC_BOLD_OFF])
    chunks.append(_encode_text(settings.get("business_address", "") + "\n"))
    chunks.append(_encode_text("Tel: " + settings.get("business_phone", "") + "\n"))
    chunks.append(_encode_text("GST/HST#: " + settings.get("gst_number", "") + "\n"))
    chunks.append(_encode_text("-" * width + "\n"))

    chunks.append(ESC_ALIGN_LEFT)
    chunks.append(_encode_text(f"Invoice: {invoice.invoice_number}\n"))
    chunks.append(_encode_text(f"Date: {invoice.created_at if invoice.created_at else 'Just now'}\n"))
    if invoice.customer_name:
        chunks.append(_encode_text(f"Customer: {invoice.customer_name}\n"))
    if invoice.customer_phone:
        chunks.append(_encode_text(f"Phone: {invoice.customer_phone}\n"))
    chunks.append(_encode_text("-" * width + "\n"))

    for item in items:
        line_total_str = format_currency(item.line_total)
        desc_str = item.description
        if item.qty > 1:
            desc_str = f"{item.qty}x {desc_str}"
        max_desc_len = width - len(line_total_str) - 1
        if len(desc_str) > max_desc_len:
            desc_str = desc_str[: max_desc_len - 3] + "..."
        spaces = width - len(desc_str) - len(line_total_str)
        chunks.append(_encode_text(f"{desc_str}{' ' * spaces}{line_total_str}\n"))
        if item.serial_number:
            chunks.append(_encode_text(f"  S/N: {item.serial_number}\n"))

    chunks.append(_encode_text("-" * width + "\n"))
    subtotal_str = format_currency(invoice.subtotal)
    tax_str = format_currency(invoice.tax_amount)
    total_str = format_currency(invoice.total)
    tax_rate_pct = int(invoice.tax_rate * 100)

    chunks.append(ESC_ALIGN_RIGHT)
    chunks.append(_encode_text(f"Subtotal: {subtotal_str:>10}\n"))
    if getattr(invoice, "discount_amount", 0) and invoice.discount_amount > 0:
        disc_str = format_currency(invoice.discount_amount)
        if invoice.discount_type == "percent":
            chunks.append(_encode_text(f"Discount ({invoice.discount_value:g}%): {disc_str:>10}\n"))
        else:
            chunks.append(_encode_text(f"Discount: {disc_str:>10}\n"))
    chunks.append(_encode_text(f"HST ({tax_rate_pct}%): {tax_str:>10}\n"))
    chunks.extend([ESC_BOLD_ON, _encode_text(f"TOTAL: {total_str:>10}\n"), ESC_BOLD_OFF])
    chunks.append(_encode_text(f"Payment: {invoice.payment_method:>10}\n"))
    chunks.append(_encode_text("-" * width + "\n"))

    chunks.extend([ESC_ALIGN_CENTER, _encode_text("Thank you!\nPlease come again\n\n\n")])
    chunks.extend([ESC_CUT, b"\n"])
    return b"".join(chunks)


def _print_bytes_win32(printer_name: str, data: bytes, datatype: str) -> tuple[bool, str]:
    import win32print  # type: ignore

    handle = win32print.OpenPrinter(printer_name)
    try:
        doc_name = "Retail Invoice Receipt"
        job = win32print.StartDocPrinter(handle, 1, (doc_name, None, datatype))
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
    width = get_printer_width_chars(settings.get("receipt_width", "80mm"))

    logo_path = _resolve_logo_path(settings)
    if logo_path:
        try:
            printer.image(logo_path)
        except Exception as e:
            logging.warning(f"Logo skipped: {e}")

    printer.text(build_receipt_plaintext(invoice, items, settings) + "\n")
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

    # 1) Raw ESC/POS via win32print (best for TM-T20 thermal printers)
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

    # 2) python-escpos Win32Raw wrapper
    try:
        return _print_with_escpos(printer_name, invoice, items, settings)
    except Exception as e:
        errors.append(f"escpos: {e}")
        logging.error(f"escpos print failed: {e}")

    # 3) Plain text through Windows driver
    try:
        text = build_receipt_plaintext(invoice, items, settings) + "\n\n\n"
        ok, msg = _print_bytes_win32(printer_name, _encode_text(text), "TEXT")
        if ok:
            return True, msg
        errors.append(f"TEXT: {msg}")
    except Exception as e:
        errors.append(f"TEXT: {e}")
        logging.error(f"TEXT print failed: {e}")

    detail = errors[0] if errors else "Unknown print error"
    return False, f"Could not print to '{printer_name}'. {detail}"
