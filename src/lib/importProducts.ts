import * as XLSX from "xlsx";
import type { Product } from "../lib/types";
import { parseCurrency } from "../lib/money";

/** Fixed store categories for the product pulldown. */
export const PRODUCT_CATEGORIES = [
  "Laptops",
  "Desktops",
  "Monitors",
  "Printers",
  "Cell Phones",
  "Tablets",
] as const;

export type ProductCategory = (typeof PRODUCT_CATEGORIES)[number];

/** SKU prefix → category batch rules (longer prefixes first). */
export const SKU_CATEGORY_RULES: { prefix: string; category: ProductCategory }[] = [
  { prefix: "110", category: "Cell Phones" },
  { prefix: "92", category: "Laptops" },
];

function normalizeHeader(h: string): string {
  return h.trim().toLowerCase().replace(/\s+/g, " ");
}

function pick(row: Record<string, unknown>, aliases: string[]): string {
  const map = new Map<string, unknown>();
  for (const [k, v] of Object.entries(row)) {
    map.set(normalizeHeader(k), v);
  }
  for (const alias of aliases) {
    const v = map.get(alias);
    if (v !== undefined && v !== null && String(v).trim() !== "") {
      return String(v).trim();
    }
  }
  return "";
}

function pickRaw(row: Record<string, unknown>, aliases: string[]): string {
  const map = new Map<string, unknown>();
  for (const [k, v] of Object.entries(row)) {
    map.set(normalizeHeader(k), v);
  }
  for (const alias of aliases) {
    if (!map.has(alias)) continue;
    const v = map.get(alias);
    if (v === undefined || v === null) return "";
    return String(v).trim();
  }
  return "";
}

/** Today's date stamp for CSV / DB: YYYY-MM-DD */
export function todayImportDateStamp(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export interface ParsedProductRow extends Product {
  /** Raw date stamp from CSV; blank means eligible to import. */
  import_date: string;
  /** True when the Date Stamp cell was blank — only these rows are imported. */
  importEligible: boolean;
}

export function parseProductSpreadsheet(data: ArrayBuffer | string): ParsedProductRow[] {
  // raw:true keeps SKUs like "92-2" as strings (SheetJS otherwise treats them as dates)
  const workbook =
    typeof data === "string"
      ? XLSX.read(data, { type: "string", raw: true })
      : XLSX.read(data, { type: "array", raw: true });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
    defval: "",
    raw: true,
  });
  const products: ParsedProductRow[] = [];

  for (const row of rows) {
    const name = pick(row, ["product name", "name", "product"]);
    const sku = pick(row, ["sku", "code"]);
    const details = pick(row, ["details", "serial", "serial_number", "description"]);
    const qtyRaw = pick(row, ["qty", "quantity", "stock"]);
    const priceRaw = pick(row, ["price", "unit price"]);
    const category = pick(row, ["category", "cat", "type"]);
    const dateStamp = pickRaw(row, [
      "date stamp",
      "datestamp",
      "import date",
      "date",
      "counted",
      "count date",
    ]);
    if (!name && !sku) continue;
    products.push({
      id: null,
      name: name || "Untitled product",
      serial_number: details,
      sku,
      price: parseCurrency(priceRaw),
      qty: Number.parseInt(qtyRaw || "0", 10) || 0,
      category,
      import_date: dateStamp,
      importEligible: dateStamp === "",
    });
  }

  return products;
}

/** Only rows with a blank Date Stamp column are imported. */
export function filterImportableRows(rows: ParsedProductRow[]): ParsedProductRow[] {
  return rows.filter((r) => r.importEligible);
}

export function stampImportRows(
  rows: ParsedProductRow[],
  stamp = todayImportDateStamp(),
): ParsedProductRow[] {
  return rows.map((row) => ({
    ...row,
    import_date: stamp,
  }));
}

export function buildProductTemplateCsv(): string {
  return (
    "SKU,Product Name,Details,Qty,Price,Category,Date Stamp\n" +
    "ABC-001,Sample Product,Black / Large,10,29.99,Laptops,\n"
  );
}

export function buildProductsExportCsv(products: Product[]): string {
  const header = ["SKU", "Product Name", "Details", "Qty", "Price", "Category", "Date Stamp"];
  const lines = [header.join(",")];
  for (const p of products) {
    const cells = [
      p.sku,
      p.name,
      p.serial_number,
      String(p.qty),
      String(p.price),
      p.category || "",
      p.import_date || "",
    ].map(csvEscape);
    lines.push(cells.join(","));
  }
  return `${lines.join("\n")}\n`;
}

function csvEscape(value: string): string {
  const s = value ?? "";
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function downloadTextFile(filename: string, contents: string, mime = "text/csv;charset=utf-8"): void {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
