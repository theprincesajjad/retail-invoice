import { describe, expect, it } from "vitest";
import {
  PRODUCT_CATEGORIES,
  SKU_CATEGORY_RULES,
  buildProductsExportCsv,
  filterImportableRows,
  parseProductSpreadsheet,
  stampImportRows,
  todayImportDateStamp,
} from "./importProducts";
import { groupInStockByCategory } from "./inventoryPdf";
import type { Product } from "./types";

describe("inventory CSV import/export", () => {
  it("exposes store categories and SKU rules", () => {
    expect(PRODUCT_CATEGORIES).toContain("Laptops");
    expect(PRODUCT_CATEGORIES).toContain("Cell Phones");
    expect(SKU_CATEGORY_RULES).toEqual([
      { prefix: "110", category: "Cell Phones" },
      { prefix: "92", category: "Laptops" },
    ]);
  });

  it("imports only rows with a blank Date Stamp, then stamps today", () => {
    // Quote SKUs so SheetJS does not treat 92-2 as a date
    const csv = [
      "SKU,Product Name,Details,Qty,Price,Category,Date Stamp",
      '"92-1",Old Laptop,,1,100,Laptops,2026-01-01',
      '"92-2",New Laptop,,2,200,Laptops,',
      '"110-1",Phone,,1,50,Cell Phones,',
    ].join("\n");
    const rows = parseProductSpreadsheet(csv);
    expect(rows).toHaveLength(3);
    const importable = filterImportableRows(rows);
    expect(importable.map((r) => r.sku)).toEqual(["92-2", "110-1"]);
    const stamped = stampImportRows(importable, "2026-09-04");
    expect(stamped.every((r) => r.import_date === "2026-09-04")).toBe(true);
  });

  it("exports CSV with category and date stamp columns", () => {
    const products: Product[] = [
      {
        id: 1,
        name: "Pad",
        serial_number: "Silver",
        sku: "110999",
        price: 10,
        qty: 2,
        category: "Cell Phones",
        import_date: "2026-09-04",
      },
    ];
    const csv = buildProductsExportCsv(products);
    expect(csv.split("\n")[0]).toBe(
      "SKU,Product Name,Details,Qty,Price,Category,Date Stamp",
    );
    expect(csv).toContain("110999");
    expect(csv).toContain("Cell Phones");
    expect(csv).toContain("2026-09-04");
  });

  it("formats today's stamp as YYYY-MM-DD", () => {
    expect(todayImportDateStamp(new Date("2026-09-04T12:00:00"))).toBe("2026-09-04");
  });
});

describe("inventory checklist grouping", () => {
  it("keeps only qty > 0 and sorts by category", () => {
    const products: Product[] = [
      {
        id: 1,
        name: "B Phone",
        serial_number: "",
        sku: "1102",
        price: 1,
        qty: 1,
        category: "Cell Phones",
      },
      {
        id: 2,
        name: "A Laptop",
        serial_number: "",
        sku: "9201",
        price: 1,
        qty: 3,
        category: "Laptops",
      },
      {
        id: 3,
        name: "Gone",
        serial_number: "",
        sku: "x",
        price: 1,
        qty: 0,
        category: "Laptops",
      },
    ];
    const groups = groupInStockByCategory(products);
    expect(groups.map((g) => g.category)).toEqual(["Cell Phones", "Laptops"]);
    expect(groups[1].items.map((p) => p.name)).toEqual(["A Laptop"]);
    expect(groups.flatMap((g) => g.items).some((p) => p.qty === 0)).toBe(false);
  });
});
