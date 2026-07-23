import type { DiscountTiming, DiscountType, InvoiceItem, InvoiceTotals } from "./types";

export function formatCurrency(amount: number): string {
  if (!Number.isFinite(amount)) return "$0.00";
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function parseCurrency(amountStr: string): number {
  const clean = amountStr.replace(/\$/g, "").replace(/,/g, "").trim();
  if (!clean) return 0;
  const n = Number(clean);
  return Number.isFinite(n) ? n : 0;
}

export function computeInvoiceTotals(
  items: Pick<InvoiceItem, "line_total">[],
  taxRate: number,
  discountType: DiscountType | string = "",
  discountValue = 0,
  discountTiming: DiscountTiming | string = "before_tax",
): InvoiceTotals {
  const subtotal = items.reduce((sum, item) => sum + (item.line_total || 0), 0);
  let timing = (discountTiming || "before_tax").trim().toLowerCase();
  if (timing !== "before_tax" && timing !== "after_tax") {
    timing = "before_tax";
  }

  const discountOf = (base: number): number => {
    if (discountValue <= 0) return 0;
    if (discountType === "percent") {
      return Math.min(base, base * (discountValue / 100));
    }
    if (discountType === "fixed") {
      return Math.min(base, discountValue);
    }
    return 0;
  };

  if (timing === "after_tax") {
    const tax_amount = subtotal * taxRate;
    const preDiscount = subtotal + tax_amount;
    const discount_amount = discountOf(preDiscount);
    const total = Math.max(0, preDiscount - discount_amount);
    return { subtotal, discount_amount, tax_amount, total };
  }

  const discount_amount = discountOf(subtotal);
  const taxable = Math.max(0, subtotal - discount_amount);
  const tax_amount = taxable * taxRate;
  const total = taxable + tax_amount;
  return { subtotal, discount_amount, tax_amount, total };
}
