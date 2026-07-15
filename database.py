import sqlite3
from config import get_db_connection, DEFAULT_SETTINGS
from models import Product, Invoice, InvoiceItem


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                serial_number TEXT,
                sku TEXT,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Invoices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                subtotal REAL NOT NULL,
                tax_rate REAL NOT NULL,
                tax_amount REAL NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Invoice Items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT NOT NULL,
                serial_number TEXT,
                qty INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Pre-populate settings if empty
        cursor.execute('SELECT COUNT(*) FROM settings')
        if cursor.fetchone()[0] == 0:
            for key, value in DEFAULT_SETTINGS.items():
                cursor.execute('INSERT INTO settings (key, value) VALUES (?, ?)', (key, value))
        else:
            for key, value in DEFAULT_SETTINGS.items():
                cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
        conn.commit()
        _migrate_schema(conn)


def _migrate_schema(conn):
    cursor = conn.cursor()
    for sql in (
        "ALTER TABLE invoices ADD COLUMN discount_type TEXT DEFAULT ''",
        "ALTER TABLE invoices ADD COLUMN discount_value REAL DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN discount_amount REAL DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN discount_timing TEXT DEFAULT 'before_tax'",
        "ALTER TABLE invoices ADD COLUMN customer_email TEXT DEFAULT ''",
    ):
        try:
            cursor.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass

def get_setting(key, default=""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

def save_setting(key, value):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) 
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        ''', (key, value))
        conn.commit()

def get_all_settings():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        stored = {row['key']: row['value'] for row in cursor.fetchall()}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored)
    return merged

# Product CRUD
def add_product(product: Product):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, serial_number, sku, price, qty, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (product.name, product.serial_number, product.sku, product.price, product.qty, product.category))
        conn.commit()
        return cursor.lastrowid

def update_product(product: Product):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=?, serial_number=?, sku=?, price=?, qty=?, category=?
            WHERE id=?
        ''', (product.name, product.serial_number, product.sku, product.price, product.qty, product.category, product.id))
        conn.commit()

def delete_product(product_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()

def search_products(query=""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        search_query = f"%{query}%"
        cursor.execute('''
            SELECT * FROM products 
            WHERE name LIKE ? OR serial_number LIKE ? OR sku LIKE ? OR category LIKE ?
            ORDER BY name
        ''', (search_query, search_query, search_query, search_query))
        rows = cursor.fetchall()
        return [Product(**dict(row)) for row in rows]

# Invoice CRUD
INVOICE_NUMBER_PREFIX = "INV-786"


def generate_invoice_number():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1",
            (f"{INVOICE_NUMBER_PREFIX}-%",),
        )
        row = cursor.fetchone()
        if row:
            last_num = int(row["invoice_number"].split("-")[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        return f"{INVOICE_NUMBER_PREFIX}-{new_num:04d}"

def save_invoice(invoice: Invoice, items: list[InvoiceItem]):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO invoices (
                invoice_number, customer_name, customer_phone, customer_email,
                subtotal, tax_rate, tax_amount, total,
                payment_method, notes, discount_type, discount_value, discount_amount,
                discount_timing
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice.invoice_number, invoice.customer_name, invoice.customer_phone,
            getattr(invoice, "customer_email", "") or "",
            invoice.subtotal, invoice.tax_rate, invoice.tax_amount, invoice.total,
            invoice.payment_method, invoice.notes,
            invoice.discount_type or "", invoice.discount_value or 0.0, invoice.discount_amount or 0.0,
            getattr(invoice, "discount_timing", None) or "before_tax",
        ))
        
        invoice_id = cursor.lastrowid
        
        # Save invoice items and update inventory
        for item in items:
            cursor.execute('''
                INSERT INTO invoice_items (invoice_id, product_id, description, serial_number, qty, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (invoice_id, item.product_id, item.description, item.serial_number, item.qty, item.unit_price, item.line_total))
            
            # Deduct from inventory if product_id is not null
            if item.product_id:
                cursor.execute('UPDATE products SET qty = qty - ? WHERE id = ?', (item.qty, item.product_id))
                
        conn.commit()
        return invoice_id

def get_invoices(start_date=None, end_date=None, search_query=""):
    return _fetch_invoices(start_date, end_date, search_query)


def search_invoices(search_query="", start_date=None, end_date=None):
    return _fetch_invoices(start_date, end_date, search_query)


def _fetch_invoices(start_date=None, end_date=None, search_query=""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT i.* FROM invoices i"
        params = []
        conditions = []

        if search_query.strip():
            query += " LEFT JOIN invoice_items ii ON ii.invoice_id = i.id"
            like = f"%{search_query.strip()}%"
            conditions.append(
                "(i.customer_name LIKE ? OR i.customer_phone LIKE ? OR ii.description LIKE ? OR ii.serial_number LIKE ?)"
            )
            params.extend([like, like, like, like])

        if start_date and end_date:
            conditions.append("i.created_at >= ? AND i.created_at <= ?")
            params.extend([start_date, end_date])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY i.created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        invoices = []
        for row in rows:
            data = dict(row)
            data.setdefault("discount_type", "")
            data.setdefault("discount_value", 0.0)
            data.setdefault("discount_amount", 0.0)
            data.setdefault("discount_timing", "before_tax")
            data.setdefault("customer_email", "")
            inv = Invoice(**data, items=[])
            cursor.execute('SELECT * FROM invoice_items WHERE invoice_id = ?', (inv.id,))
            item_rows = cursor.fetchall()
            inv.items = [InvoiceItem(**dict(i)) for i in item_rows]
            invoices.append(inv)
        return invoices
