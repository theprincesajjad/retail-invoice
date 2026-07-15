import os
import sys
import sqlite3
import pathlib

# Handle PyInstaller frozen mode
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = pathlib.Path(sys.executable).parent.resolve()
else:
    BASE_DIR = pathlib.Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "invoices.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

DEFAULT_SETTINGS = {
    "business_name": "My Business",
    "business_tagline": "",
    "business_address": "123 Main St, City, ON",
    "business_website": "",
    "business_phone": "(416) 555-0123",
    "business_email": "",
    "gst_number": "123456789RT0001",
    "receipt_footer": "All Sales are Final. No Returns or Exchanges.",
    "tax_rate": "0.13",
    "discount_timing": "before_tax",
    "logo_path": str(ASSETS_DIR / "logo.png"),
    "printer_name": "",
    "receipt_width": "80mm",
    "receipt_font_size": "normal",
    "receipt_header_spacing": "normal",
    "receipt_show_logo": "1",
    "receipt_show_business_name": "1",
    "receipt_show_tagline": "1",
    "receipt_show_address": "1",
    "receipt_show_phone": "1",
    "receipt_show_website": "1",
    "receipt_show_email": "1",
    "receipt_show_customer": "1",
    "receipt_show_details": "1",
    "receipt_show_notes": "1",
    "receipt_show_thanks": "1",
    "receipt_show_footer": "1",
    "receipt_show_gst": "1",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_email": "",
    "smtp_password": "",
    "smtp_from_name": "My Business",
    "setup_complete": "",
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
