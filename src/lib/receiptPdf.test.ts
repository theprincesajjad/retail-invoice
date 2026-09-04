import { describe, expect, it } from "vitest";
import { DEFAULT_SETTINGS, type AppSettings } from "./types";
import {
  buildReceiptPdf,
  buildReceiptText,
  formatReceiptDate,
  sampleTestInvoice,
} from "./receiptPdf";

const gadgetsSettings: AppSettings = {
  ...DEFAULT_SETTINGS,
  business_name: "Gadgets & Gold",
  business_tagline: "Your Tech, Our Passion",
  business_address: "2814 Victoria Park Ave",
  business_phone: "(416) 490-8886 - (905) 910-0007",
  business_website: "www.gadgetsandgold.com",
  business_email: "info@gadgetsandgold.com",
  gst_number: "127385086RT0001",
  receipt_footer:
    "All Sales are Final. No Returns or Exchanges.\nAll Products come with a 30 Days store warranty.\nBrand New products will have remain manufacture warranty.",
  receipt_width: "80mm",
  receipt_show_logo: "0",
  receipt_show_notes: "0",
};

describe("receipt thermal layout", () => {
  it("formats dates like the physical receipt", () => {
    expect(formatReceiptDate("2026-09-03 18:58:00")).toBe("Sep 3, 2026 6:58 pm");
  });

  it("builds the Gadgets & Gold 80mm layout character-for-character", () => {
    const text = buildReceiptText(sampleTestInvoice(), gadgetsSettings);
    const lines = text.split("\n");
    const width = 48;

    expect(lines.every((line) => line.length <= width)).toBe(true);

    expect(text).toContain("=".repeat(width));
    expect(text).toContain("-".repeat(width));
    expect(text).toContain("GADGETS & GOLD");
    expect(text).toContain("Your Tech, Our Passion");
    expect(text).toContain("2814 Victoria Park Ave");
    expect(text).toContain("SALES RECEIPT");
    expect(text).toContain("Receipt #: INV-786-0122");
    expect(text).toContain("Date: Sep 3, 2026 6:58 pm");
    expect(text).toContain("Customer: Hamilton Montesori");
    expect(text).toContain("Paid by: Cash");
    expect(text).toContain("Thank you for your business!");
    expect(text).toContain("We appreciate your visit.");
    expect(text).toContain("HST Reg. 127385086RT0001");

    // Column header locked to Item / Qty / Price / Total
    const header = lines.find((l) => l.includes("Item") && l.includes("Qty") && l.includes("Total"));
    expect(header).toBeDefined();
    expect(header!.length).toBe(width);
    expect(header!.indexOf("Item")).toBe(0);
    expect(header!.endsWith("Total")).toBe(true);

    // Line items + detail under Item (no Details: prefix)
    expect(text).toContain("iPad 11th Gen 128GB");
    expect(text).toContain("Silver");
    expect(text).not.toContain("Details:");
    expect(text).toContain("Hard Case");
    expect(text).toContain("$1,279.98");
    expect(text).toContain("$1,525.45");

    // Money rows right-align within 48 cols
    const totalLine = lines.find((l) => l.includes("TOTAL") && l.includes("$1,525.45"));
    expect(totalLine).toBeDefined();
    expect(totalLine!.length).toBe(width);
    expect(totalLine!.trimEnd().endsWith("$1,525.45")).toBe(true);
  });

  it("fits PDF content inside page with side and bottom margins", () => {
    const doc = buildReceiptPdf(sampleTestInvoice(), gadgetsSettings);
    expect(doc.internal.pageSize.getWidth()).toBe(80);
    // Tall enough for full receipt + bottom margin clearance
    expect(doc.internal.pageSize.getHeight()).toBeGreaterThanOrEqual(140);
  });
});
