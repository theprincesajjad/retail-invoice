import os
import logging
from database import get_all_settings, get_setting
from models import Invoice, InvoiceItem
from utils import format_currency

def get_printer_width_chars(width_setting):
    if width_setting == "58mm":
        return 32
    return 48  # 80mm default

def print_receipt(invoice: Invoice, items: list[InvoiceItem]):
    settings = get_all_settings()
    printer_name = settings.get("printer_name", "")
    
    if not printer_name:
        logging.warning("No printer configured. Skipping print.")
        return False
        
    try:
        from escpos.printer import Win32Raw
        p = Win32Raw(printer_name)
        
        # Logo printing
        logo_path = settings.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            try:
                p.image(logo_path)
            except Exception as e:
                logging.error(f"Failed to print logo: {e}")
                
        width_chars = get_printer_width_chars(settings.get("receipt_width", "80mm"))
        
        # Header
        p.set(align="center", bold=True, double_height=True, double_width=True)
        p.text(settings.get("business_name", "My Business") + "\n")
        p.set(align="center", bold=False, double_height=False, double_width=False)
        p.text(settings.get("business_address", "") + "\n")
        p.text("Tel: " + settings.get("business_phone", "") + "\n")
        p.text("GST/HST#: " + settings.get("gst_number", "") + "\n")
        p.text("-" * width_chars + "\n")
        
        # Invoice Info
        p.set(align="left")
        p.text(f"Invoice: {invoice.invoice_number}\n")
        p.text(f"Date: {invoice.created_at if invoice.created_at else 'Just now'}\n")
        if invoice.customer_name:
            p.text(f"Customer: {invoice.customer_name}\n")
        if invoice.customer_phone:
            p.text(f"Phone: {invoice.customer_phone}\n")
        p.text("-" * width_chars + "\n")
        
        # Items
        for item in items:
            # Format: Description (left)    Line Total (right)
            line_total_str = format_currency(item.line_total)
            desc_str = item.description
            
            # If Qty > 1, add it to description
            if item.qty > 1:
                desc_str = f"{item.qty}x {desc_str}"
            
            # Truncate description if too long to fit with total
            max_desc_len = width_chars - len(line_total_str) - 1
            if len(desc_str) > max_desc_len:
                desc_str = desc_str[:max_desc_len-3] + "..."
                
            spaces = width_chars - len(desc_str) - len(line_total_str)
            p.text(f"{desc_str}{' ' * spaces}{line_total_str}\n")
            
            # S/N on next line if present
            if item.serial_number:
                p.text(f"  S/N: {item.serial_number}\n")
                
        p.text("-" * width_chars + "\n")
        
        # Totals
        p.set(align="right")
        subtotal_str = format_currency(invoice.subtotal)
        tax_str = format_currency(invoice.tax_amount)
        total_str = format_currency(invoice.total)
        
        tax_rate_pct = int(invoice.tax_rate * 100)
        
        p.text(f"Subtotal: {subtotal_str:>10}\n")
        p.text(f"HST ({tax_rate_pct}%): {tax_str:>10}\n")
        p.set(bold=True)
        p.text(f"TOTAL: {total_str:>10}\n")
        p.set(bold=False)
        p.text(f"Payment: {invoice.payment_method:>10}\n")
        p.text("-" * width_chars + "\n")
        
        # Footer
        p.set(align="center")
        p.text("Thank you!\n")
        p.text("Please come again\n")
        p.text("-" * width_chars + "\n\n\n")
        
        p.cut()
        p.close()
        return True
        
    except Exception as e:
        logging.error(f"Printing failed: {e}")
        return False
