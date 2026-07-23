import type { SqlValue } from "sql.js";
import type { AppSettings, Invoice, InvoiceItem, Product } from "../lib/types";
import { DEFAULT_SETTINGS } from "../lib/types";

export type SqlJsDatabase = {
  run: (sql: string, params?: SqlValue[]) => void;
  exec: (sql: string) => { columns: string[]; values: SqlValue[][] }[];
  prepare: (sql: string) => {
    bind: (params: SqlValue[]) => void;
    step: () => boolean;
    getAsObject: () => Record<string, SqlValue>;
    free: () => void;
  };
  export: () => Uint8Array;
  close: () => void;
};

const INVOICE_NUMBER_PREFIX = "INV-786";

export function initSchema(db: SqlJsDatabase): void {
  db.run(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      serial_number TEXT,
      sku TEXT,
      price REAL NOT NULL,
      qty INTEGER NOT NULL,
      category TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS invoices (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      invoice_number TEXT UNIQUE NOT NULL,
      customer_name TEXT,
      customer_phone TEXT,
      customer_email TEXT DEFAULT '',
      subtotal REAL NOT NULL,
      tax_rate REAL NOT NULL,
      tax_amount REAL NOT NULL,
      total REAL NOT NULL,
      payment_method TEXT,
      notes TEXT,
      discount_type TEXT DEFAULT '',
      discount_value REAL DEFAULT 0,
      discount_amount REAL DEFAULT 0,
      discount_timing TEXT DEFAULT 'before_tax',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);
  db.run(`
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
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT
    );
  `);

  for (const [key, value] of Object.entries(DEFAULT_SETTINGS)) {
    db.run("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", [key, value]);
  }
}

function rowsToObjects(result: { columns: string[]; values: SqlValue[][] }[]): Record<string, SqlValue>[] {
  if (!result.length) return [];
  const { columns, values } = result[0];
  return values.map((row) => {
    const obj: Record<string, SqlValue> = {};
    columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}

function asString(v: SqlValue | undefined, fallback = ""): string {
  if (v === null || v === undefined) return fallback;
  return String(v);
}

function asNumber(v: SqlValue | undefined, fallback = 0): number {
  if (v === null || v === undefined) return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export function getSetting(db: SqlJsDatabase, key: string, fallback = ""): string {
  const stmt = db.prepare("SELECT value FROM settings WHERE key = ?");
  stmt.bind([key]);
  let value = fallback;
  if (stmt.step()) {
    value = asString(stmt.getAsObject().value, fallback);
  }
  stmt.free();
  return value;
}

export function saveSetting(db: SqlJsDatabase, key: string, value: string): void {
  db.run(
    `INSERT INTO settings (key, value) VALUES (?, ?)
     ON CONFLICT(key) DO UPDATE SET value=excluded.value`,
    [key, value],
  );
}

export function getAllSettings(db: SqlJsDatabase): AppSettings {
  const rows = rowsToObjects(db.exec("SELECT key, value FROM settings"));
  const merged: AppSettings = { ...DEFAULT_SETTINGS };
  for (const row of rows) {
    const key = asString(row.key);
    if (key) merged[key] = asString(row.value);
  }
  return merged;
}

export function saveSettings(db: SqlJsDatabase, settings: Partial<AppSettings>): void {
  for (const [key, value] of Object.entries(settings)) {
    if (value === undefined) continue;
    saveSetting(db, key, String(value));
  }
}

function mapProduct(row: Record<string, SqlValue>): Product {
  return {
    id: asNumber(row.id),
    name: asString(row.name),
    serial_number: asString(row.serial_number),
    sku: asString(row.sku),
    price: asNumber(row.price),
    qty: asNumber(row.qty),
    category: asString(row.category),
    created_at: asString(row.created_at),
  };
}

export function searchProducts(db: SqlJsDatabase, query = ""): Product[] {
  const like = `%${query}%`;
  const stmt = db.prepare(`
    SELECT * FROM products
    WHERE name LIKE ? OR serial_number LIKE ? OR sku LIKE ?
    ORDER BY name
  `);
  stmt.bind([like, like, like]);
  const products: Product[] = [];
  while (stmt.step()) {
    products.push(mapProduct(stmt.getAsObject()));
  }
  stmt.free();
  return products;
}

export function addProduct(db: SqlJsDatabase, product: Product): number {
  db.run(
    `INSERT INTO products (name, serial_number, sku, price, qty, category)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [
      product.name,
      product.serial_number,
      product.sku,
      product.price,
      product.qty,
      product.category,
    ],
  );
  const rows = rowsToObjects(db.exec("SELECT last_insert_rowid() AS id"));
  return asNumber(rows[0]?.id);
}

export function updateProduct(db: SqlJsDatabase, product: Product): void {
  db.run(
    `UPDATE products
     SET name=?, serial_number=?, sku=?, price=?, qty=?, category=?
     WHERE id=?`,
    [
      product.name,
      product.serial_number,
      product.sku,
      product.price,
      product.qty,
      product.category,
      product.id,
    ],
  );
}

export function deleteProduct(db: SqlJsDatabase, productId: number): void {
  db.run("DELETE FROM products WHERE id = ?", [productId]);
}

export function upsertProductBySku(db: SqlJsDatabase, product: Product): void {
  const stmt = db.prepare("SELECT id FROM products WHERE sku = ? AND sku != '' LIMIT 1");
  stmt.bind([product.sku]);
  let existingId: number | null = null;
  if (stmt.step()) {
    existingId = asNumber(stmt.getAsObject().id);
  }
  stmt.free();
  if (existingId) {
    updateProduct(db, { ...product, id: existingId });
  } else {
    addProduct(db, product);
  }
}

export function generateInvoiceNumber(db: SqlJsDatabase): string {
  const stmt = db.prepare(
    "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1",
  );
  stmt.bind([`${INVOICE_NUMBER_PREFIX}-%`]);
  let next = 1;
  if (stmt.step()) {
    const last = asString(stmt.getAsObject().invoice_number);
    const part = Number(last.split("-").pop());
    if (Number.isFinite(part)) next = part + 1;
  }
  stmt.free();
  return `${INVOICE_NUMBER_PREFIX}-${String(next).padStart(4, "0")}`;
}

export function saveInvoice(db: SqlJsDatabase, invoice: Invoice, items: InvoiceItem[]): number {
  db.run(
    `INSERT INTO invoices (
      invoice_number, customer_name, customer_phone, customer_email,
      subtotal, tax_rate, tax_amount, total, payment_method, notes,
      discount_type, discount_value, discount_amount, discount_timing
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      invoice.invoice_number,
      invoice.customer_name,
      invoice.customer_phone,
      invoice.customer_email || "",
      invoice.subtotal,
      invoice.tax_rate,
      invoice.tax_amount,
      invoice.total,
      invoice.payment_method,
      invoice.notes,
      invoice.discount_type || "",
      invoice.discount_value || 0,
      invoice.discount_amount || 0,
      invoice.discount_timing || "before_tax",
    ],
  );
  const idRows = rowsToObjects(db.exec("SELECT last_insert_rowid() AS id"));
  const invoiceId = asNumber(idRows[0]?.id);

  for (const item of items) {
    db.run(
      `INSERT INTO invoice_items (
        invoice_id, product_id, description, serial_number, qty, unit_price, line_total
      ) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        invoiceId,
        item.product_id,
        item.description,
        item.serial_number,
        item.qty,
        item.unit_price,
        item.line_total,
      ],
    );
    if (item.product_id) {
      db.run("UPDATE products SET qty = qty - ? WHERE id = ?", [item.qty, item.product_id]);
    }
  }
  return invoiceId;
}

function mapInvoice(row: Record<string, SqlValue>, items: InvoiceItem[]): Invoice {
  return {
    id: asNumber(row.id),
    invoice_number: asString(row.invoice_number),
    customer_name: asString(row.customer_name),
    customer_phone: asString(row.customer_phone),
    customer_email: asString(row.customer_email),
    subtotal: asNumber(row.subtotal),
    tax_rate: asNumber(row.tax_rate),
    tax_amount: asNumber(row.tax_amount),
    total: asNumber(row.total),
    payment_method: asString(row.payment_method),
    notes: asString(row.notes),
    created_at: asString(row.created_at),
    items,
    discount_type: asString(row.discount_type),
    discount_value: asNumber(row.discount_value),
    discount_amount: asNumber(row.discount_amount),
    discount_timing: asString(row.discount_timing, "before_tax"),
  };
}

function mapItem(row: Record<string, SqlValue>): InvoiceItem {
  return {
    id: asNumber(row.id),
    invoice_id: asNumber(row.invoice_id),
    product_id: row.product_id === null || row.product_id === undefined ? null : asNumber(row.product_id),
    description: asString(row.description),
    serial_number: asString(row.serial_number),
    qty: asNumber(row.qty),
    unit_price: asNumber(row.unit_price),
    line_total: asNumber(row.line_total),
  };
}

export function searchInvoices(
  db: SqlJsDatabase,
  searchQuery = "",
  startDate?: string,
  endDate?: string,
): Invoice[] {
  let sql = "SELECT DISTINCT i.* FROM invoices i";
  const params: SqlValue[] = [];
  const conditions: string[] = [];

  if (searchQuery.trim()) {
    sql += " LEFT JOIN invoice_items ii ON ii.invoice_id = i.id";
    const like = `%${searchQuery.trim()}%`;
    conditions.push(
      "(i.customer_name LIKE ? OR i.customer_phone LIKE ? OR ii.description LIKE ? OR ii.serial_number LIKE ? OR i.invoice_number LIKE ?)",
    );
    params.push(like, like, like, like, like);
  }
  if (startDate && endDate) {
    conditions.push("i.created_at >= ? AND i.created_at <= ?");
    params.push(startDate, endDate);
  }
  if (conditions.length) {
    sql += ` WHERE ${conditions.join(" AND ")}`;
  }
  sql += " ORDER BY i.created_at DESC";

  const stmt = db.prepare(sql);
  stmt.bind(params);
  const invoices: Invoice[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject();
    const id = asNumber(row.id);
    const itemStmt = db.prepare("SELECT * FROM invoice_items WHERE invoice_id = ?");
    itemStmt.bind([id]);
    const items: InvoiceItem[] = [];
    while (itemStmt.step()) {
      items.push(mapItem(itemStmt.getAsObject()));
    }
    itemStmt.free();
    invoices.push(mapInvoice(row, items));
  }
  stmt.free();
  return invoices;
}

/** Import rows from a legacy SQLite dump (same schema). */
export function importLegacyDatabase(target: SqlJsDatabase, source: SqlJsDatabase): { products: number; invoices: number } {
  initSchema(source);
  const products = rowsToObjects(source.exec("SELECT * FROM products"));
  let productCount = 0;
  for (const row of products) {
    const p = mapProduct(row);
    if (p.sku) {
      upsertProductBySku(target, { ...p, id: null });
    } else {
      addProduct(target, { ...p, id: null });
    }
    productCount += 1;
  }

  const settings = rowsToObjects(source.exec("SELECT key, value FROM settings"));
  for (const row of settings) {
    const key = asString(row.key);
    if (!key || key === "setup_complete") continue;
    saveSetting(target, key, asString(row.value));
  }

  const invoices = rowsToObjects(source.exec("SELECT * FROM invoices ORDER BY id"));
  let invoiceCount = 0;
  for (const row of invoices) {
    const id = asNumber(row.id);
    const itemStmt = source.prepare("SELECT * FROM invoice_items WHERE invoice_id = ?");
    itemStmt.bind([id]);
    const items: InvoiceItem[] = [];
    while (itemStmt.step()) {
      const item = mapItem(itemStmt.getAsObject());
      items.push({ ...item, product_id: null });
    }
    itemStmt.free();

    const inv = mapInvoice(row, items);
    const existing = target.prepare("SELECT id FROM invoices WHERE invoice_number = ?");
    existing.bind([inv.invoice_number]);
    const exists = existing.step();
    existing.free();
    if (exists) continue;

    // Insert without deducting inventory again
    target.run(
      `INSERT INTO invoices (
        invoice_number, customer_name, customer_phone, customer_email,
        subtotal, tax_rate, tax_amount, total, payment_method, notes,
        discount_type, discount_value, discount_amount, discount_timing, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        inv.invoice_number,
        inv.customer_name,
        inv.customer_phone,
        inv.customer_email,
        inv.subtotal,
        inv.tax_rate,
        inv.tax_amount,
        inv.total,
        inv.payment_method,
        inv.notes,
        inv.discount_type,
        inv.discount_value,
        inv.discount_amount,
        inv.discount_timing,
        inv.created_at,
      ],
    );
    const idRows = rowsToObjects(target.exec("SELECT last_insert_rowid() AS id"));
    const newId = asNumber(idRows[0]?.id);
    for (const item of items) {
      target.run(
        `INSERT INTO invoice_items (
          invoice_id, product_id, description, serial_number, qty, unit_price, line_total
        ) VALUES (?, NULL, ?, ?, ?, ?, ?)`,
        [newId, item.description, item.serial_number, item.qty, item.unit_price, item.line_total],
      );
    }
    invoiceCount += 1;
  }

  return { products: productCount, invoices: invoiceCount };
}
