import * as XLSX from "xlsx";
import type { Product } from "../lib/types";
import { parseCurrency } from "../lib/money";

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

export function parseProductSpreadsheet(data: ArrayBuffer | string): Product[] {
  const workbook =
    typeof data === "string"
      ? XLSX.read(data, { type: "string" })
      : XLSX.read(data, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: "" });
  const products: Product[] = [];

  for (const row of rows) {
    const name = pick(row, ["product name", "name", "product"]);
    const sku = pick(row, ["sku", "code"]);
    const details = pick(row, ["details", "serial", "serial_number", "description"]);
    const qtyRaw = pick(row, ["qty", "quantity", "stock"]);
    const priceRaw = pick(row, ["price", "unit price"]);
    if (!name && !sku) continue;
    products.push({
      id: null,
      name: name || "Untitled product",
      serial_number: details,
      sku,
      price: parseCurrency(priceRaw),
      qty: Number.parseInt(qtyRaw || "0", 10) || 0,
      category: "",
    });
  }

  return products;
}

export function buildProductTemplateCsv(): string {
  return "SKU,Product Name,Details,Qty,Price\nABC-001,Sample Product,Black / Large,10,29.99\n";
}
