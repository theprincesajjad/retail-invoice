import { describe, expect, it } from "vitest";
import { computeInvoiceTotals, formatCurrency, parseCurrency } from "../lib/money";

describe("money helpers", () => {
  it("formats currency", () => {
    expect(formatCurrency(12.5)).toBe("$12.50");
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });

  it("parses currency strings", () => {
    expect(parseCurrency("$19.99")).toBe(19.99);
    expect(parseCurrency("1,200.00")).toBe(1200);
  });

  it("computes totals before tax", () => {
    const totals = computeInvoiceTotals(
      [{ line_total: 100 }],
      0.13,
      "percent",
      10,
      "before_tax",
    );
    expect(totals.subtotal).toBe(100);
    expect(totals.discount_amount).toBe(10);
    expect(totals.tax_amount).toBeCloseTo(11.7);
    expect(totals.total).toBeCloseTo(101.7);
  });

  it("computes totals after tax", () => {
    const totals = computeInvoiceTotals(
      [{ line_total: 100 }],
      0.1,
      "fixed",
      5,
      "after_tax",
    );
    expect(totals.tax_amount).toBeCloseTo(10);
    expect(totals.discount_amount).toBe(5);
    expect(totals.total).toBeCloseTo(105);
  });
});
