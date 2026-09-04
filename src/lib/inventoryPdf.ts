import { jsPDF } from "jspdf";
import { formatCurrency } from "./money";
import type { AppSettings, Product } from "./types";

/** Group in-stock products by category for the store checklist. */
export function groupInStockByCategory(products: Product[]): { category: string; items: Product[] }[] {
  const inStock = products.filter((p) => p.qty > 0);
  const map = new Map<string, Product[]>();
  for (const p of inStock) {
    const key = (p.category || "").trim() || "Uncategorized";
    const list = map.get(key) || [];
    list.push(p);
    map.set(key, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) => a.name.localeCompare(b.name) || a.sku.localeCompare(b.sku));
  }
  const categories = [...map.keys()].sort((a, b) => {
    if (a === "Uncategorized") return 1;
    if (b === "Uncategorized") return -1;
    return a.localeCompare(b);
  });
  return categories.map((category) => ({ category, items: map.get(category)! }));
}

/**
 * Printable in-store inventory checklist — in-stock only, sorted by category.
 */
export function buildInventoryChecklistPdf(
  products: Product[],
  settings: AppSettings,
): jsPDF {
  const groups = groupInStockByCategory(products);
  const doc = new jsPDF({ unit: "mm", format: "letter" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const marginX = 14;
  const marginTop = 16;
  const marginBottom = 16;
  const usableW = pageW - marginX * 2;

  let y = marginTop;
  const biz = (settings.business_name || "My Business").trim();
  const today = new Date();
  const dateLabel = today.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  const ensureSpace = (need: number) => {
    if (y + need > pageH - marginBottom) {
      doc.addPage();
      y = marginTop;
    }
  };

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(biz, marginX, y);
  y += 7;
  doc.setFontSize(12);
  doc.text("Inventory checklist — in stock", marginX, y);
  y += 5;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(80);
  doc.text(`Printed ${dateLabel} · qty greater than 0 · sorted by category`, marginX, y);
  doc.setTextColor(0);
  y += 8;

  const colSku = marginX;
  const colName = marginX + 28;
  const colQty = marginX + usableW - 38;
  const colPrice = marginX + usableW - 8;
  const colCheck = marginX + usableW;

  if (!groups.length) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.text("No in-stock products.", marginX, y);
    return doc;
  }

  for (const group of groups) {
    ensureSpace(16);
    doc.setFillColor(245, 245, 245);
    doc.rect(marginX, y - 4, usableW, 7, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text(group.category, marginX + 1, y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.text(`${group.items.length} item${group.items.length === 1 ? "" : "s"}`, colPrice, y, {
      align: "right",
    });
    y += 7;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(100);
    doc.text("SKU", colSku, y);
    doc.text("Name / details", colName, y);
    doc.text("Qty", colQty, y, { align: "right" });
    doc.text("Price", colPrice, y, { align: "right" });
    doc.text("✓", colCheck, y, { align: "right" });
    doc.setTextColor(0);
    y += 4;
    doc.setDrawColor(200);
    doc.line(marginX, y, marginX + usableW, y);
    y += 4;

    for (const item of group.items) {
      ensureSpace(10);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      const sku = (item.sku || "—").slice(0, 14);
      doc.text(sku, colSku, y);
      const nameLine = item.name.slice(0, 42);
      doc.text(nameLine, colName, y);
      doc.text(String(item.qty), colQty, y, { align: "right" });
      doc.text(formatCurrency(item.price), colPrice, y, { align: "right" });
      // Checkbox for store count
      doc.setDrawColor(120);
      doc.rect(colCheck - 4, y - 3.2, 3.5, 3.5);
      y += 4.5;
      if (item.serial_number?.trim()) {
        ensureSpace(6);
        doc.setFontSize(8);
        doc.setTextColor(110);
        doc.text(item.serial_number.trim().slice(0, 70), colName, y);
        doc.setTextColor(0);
        y += 4;
      }
      y += 1.5;
    }
    y += 4;
  }

  ensureSpace(10);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(120);
  const totalItems = groups.reduce((n, g) => n + g.items.length, 0);
  const totalUnits = groups.reduce(
    (n, g) => n + g.items.reduce((s, p) => s + p.qty, 0),
    0,
  );
  doc.text(
    `${totalItems} products · ${totalUnits} units in stock`,
    marginX,
    y,
  );

  return doc;
}

export function downloadInventoryChecklistPdf(
  products: Product[],
  settings: AppSettings,
): void {
  const doc = buildInventoryChecklistPdf(products, settings);
  const stamp = new Date().toISOString().slice(0, 10);
  doc.save(`inventory-checklist-${stamp}.pdf`);
}

export function openInventoryChecklistPrint(
  products: Product[],
  settings: AppSettings,
): void {
  const doc = buildInventoryChecklistPdf(products, settings);
  const blob = doc.output("blob");
  const url = URL.createObjectURL(blob);
  const iframe = document.createElement("iframe");
  iframe.setAttribute("title", "Print inventory checklist");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  document.body.appendChild(iframe);
  iframe.onload = () => {
    try {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
    } finally {
      window.setTimeout(() => {
        iframe.remove();
        URL.revokeObjectURL(url);
      }, 60_000);
    }
  };
  iframe.src = url;
}
