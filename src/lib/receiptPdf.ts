import { jsPDF } from "jspdf";
import { formatCurrency } from "./money";
import type { AppSettings, Invoice, InvoiceItem } from "./types";

/** Fixed-width thermal layout — matches the legacy CustomTkinter / physical receipt. */
const CHARS_80MM = 48;
const CHARS_58MM = 32;

/** Side / top / bottom margins in mm — keep content clear of paper edges. */
const MARGIN_X_MM = 5;
const MARGIN_TOP_MM = 5;
const MARGIN_BOTTOM_MM = 12;

function on(settings: AppSettings, key: keyof AppSettings, defaultOn = true): boolean {
  const raw = settings[key];
  if (raw === undefined || raw === null || raw === "") return defaultOn;
  return !["0", "false", "False", "no"].includes(String(raw).trim());
}

function printerWidthChars(settings: AppSettings): number {
  return settings.receipt_width === "58mm" ? CHARS_58MM : CHARS_80MM;
}

function center(text: string, width: number): string {
  const t = (text || "").trim();
  if (!t) return "";
  if (t.length >= width) return t.slice(0, width);
  const pad = Math.floor((width - t.length) / 2);
  return `${" ".repeat(pad)}${t}`;
}

function inline(label: string, value: string, width: number): string {
  const text = `${label}: ${value || ""}`.trim();
  return text.length <= width ? text : text.slice(0, width);
}

function doubleRule(width: number): string {
  return "=".repeat(width);
}

function singleRule(width: number): string {
  return "-".repeat(width);
}

/** Match physical receipt: "Sep 3, 2026 6:58 pm" */
export function formatReceiptDate(createdAt: string | null | undefined): string {
  if (!createdAt) return "Just now";
  const normalized = createdAt.includes("T")
    ? createdAt.replace("T", " ").slice(0, 19)
    : createdAt.slice(0, 19);
  const dt = new Date(normalized.replace(" ", "T"));
  if (Number.isNaN(dt.getTime())) return createdAt;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let hours = dt.getHours();
  const mins = String(dt.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "pm" : "am";
  hours = hours % 12 || 12;
  const day = dt.getDate();
  return `${months[dt.getMonth()]} ${day}, ${dt.getFullYear()} ${hours}:${mins} ${ampm}`;
}

function itemColumns(width: number): [number, number, number, number] {
  const gaps = 3;
  let wQty = width <= 32 ? 3 : 4;
  let wUnit = width <= 32 ? 7 : 10;
  let wTotal = width <= 32 ? 7 : 10;
  let wDesc = width - gaps - wQty - wUnit - wTotal;
  if (wDesc < 8) {
    let deficit = 8 - wDesc;
    const takeUnit = Math.min(deficit, Math.max(0, wUnit - 6));
    wUnit -= takeUnit;
    deficit -= takeUnit;
    wTotal -= Math.min(deficit, Math.max(0, wTotal - 6));
    wDesc = width - gaps - wQty - wUnit - wTotal;
  }
  return [wDesc, wQty, wUnit, wTotal];
}

function wrapText(text: string, width: number): string[] {
  const w = Math.max(1, width);
  const raw = (text || "").trim();
  if (!raw) return [""];
  if (raw.length <= w) return [raw];
  const words = raw.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (let word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= w) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      while (word.length > w) {
        lines.push(word.slice(0, w));
        word = word.slice(w);
      }
      current = word;
    }
  }
  if (current) lines.push(current);
  return (lines.length ? lines : [""]).map((line) => line.slice(0, w));
}

function formatItemLine(
  desc: string,
  qty: string,
  price: string,
  total: string,
  wDesc: number,
  wQty: number,
  wUnit: number,
  wTotal: number,
): string {
  return (
    `${desc.slice(0, wDesc).padEnd(wDesc)} ` +
    `${qty.slice(0, wQty).padStart(wQty)} ` +
    `${price.slice(0, wUnit).padStart(wUnit)} ` +
    `${total.slice(0, wTotal).padStart(wTotal)}`
  );
}

function formatItemCont(
  desc: string,
  wDesc: number,
  wQty: number,
  wUnit: number,
  wTotal: number,
): string {
  return (
    `${desc.slice(0, wDesc).padEnd(wDesc)} ` +
    `${" ".repeat(wQty)} ` +
    `${" ".repeat(wUnit)} ` +
    `${" ".repeat(wTotal)}`
  );
}

function moneyRow(label: string, amount: number, width: number): string {
  const value = formatCurrency(amount);
  const room = Math.max(0, width - value.length - 1);
  const left = label.length > room ? label.slice(0, room) : label.padStart(room);
  return `${left} ${value}`;
}

/**
 * Exact character layout from the legacy thermal builder (48 chars @ 80mm).
 * Logo is drawn separately above this text block in the PDF.
 * Detail/serial lines match the physical receipt (no "Details:" prefix).
 */
export function buildReceiptText(invoice: Invoice, settings: AppSettings): string {
  const width = printerWidthChars(settings);
  const double = doubleRule(width);
  const single = singleRule(width);
  const blank = "";
  const spacing = settings.receipt_header_spacing || "normal";
  const extraBlankAfterContact = spacing === "roomy";
  const [wDesc, wQty, wUnit, wTotal] = itemColumns(width);
  const header = formatItemLine("Item", "Qty", "Price", "Total", wDesc, wQty, wUnit, wTotal);

  const lines: string[] = [];
  lines.push(blank);
  lines.push(double);
  lines.push(blank);

  if (on(settings, "receipt_show_business_name")) {
    const biz = (settings.business_name || "My Business").trim();
    if (biz) lines.push(center(biz.toUpperCase(), width));
  }
  if (on(settings, "receipt_show_tagline")) {
    const tagline = (settings.business_tagline || "").trim();
    if (tagline) lines.push(center(tagline, width));
  }
  lines.push(blank);

  const contactFields: (keyof AppSettings)[] = [];
  if (on(settings, "receipt_show_address")) contactFields.push("business_address");
  if (on(settings, "receipt_show_phone")) contactFields.push("business_phone");
  if (on(settings, "receipt_show_website")) contactFields.push("business_website");
  if (on(settings, "receipt_show_email")) contactFields.push("business_email");

  for (const field of contactFields) {
    const value = String(settings[field] || "").trim();
    if (value) {
      lines.push(center(value, width));
      if (extraBlankAfterContact) lines.push(blank);
    }
  }
  if (contactFields.length && !extraBlankAfterContact) lines.push(blank);

  lines.push(center("SALES RECEIPT", width));
  lines.push(blank);
  lines.push(double);
  lines.push(blank);

  lines.push(inline("Receipt #", invoice.invoice_number, width));
  lines.push(inline("Date", formatReceiptDate(invoice.created_at), width));

  if (on(settings, "receipt_show_customer")) {
    if (invoice.customer_name) lines.push(inline("Customer", invoice.customer_name, width));
    if (invoice.customer_phone) lines.push(inline("Phone", invoice.customer_phone, width));
    if (invoice.customer_email) lines.push(inline("Email", invoice.customer_email, width));
  }

  lines.push(blank);
  lines.push(single);
  lines.push(header);
  lines.push(single);

  for (const item of invoice.items) {
    const descLines = wrapText(item.description, wDesc);
    const unit = formatCurrency(item.unit_price);
    const total = formatCurrency(item.line_total);
    const qtyS = String(item.qty);
    lines.push(formatItemLine(descLines[0], qtyS, unit, total, wDesc, wQty, wUnit, wTotal));
    for (const extra of descLines.slice(1)) {
      lines.push(formatItemCont(extra, wDesc, wQty, wUnit, wTotal));
    }
    // Physical receipt: serial/color wraps under Item only (no "Details:" prefix)
    if (item.serial_number && on(settings, "receipt_show_details")) {
      for (const detailLine of wrapText(item.serial_number, wDesc)) {
        lines.push(formatItemCont(detailLine, wDesc, wQty, wUnit, wTotal));
      }
    }
    lines.push(blank);
  }

  lines.push(single);
  lines.push(blank);

  const taxPct = Math.round(invoice.tax_rate * 100);
  const timing = invoice.discount_timing || "before_tax";
  const hasDiscount = (invoice.discount_amount || 0) > 0;

  const pushDiscount = () => {
    const when = timing === "after_tax" ? "after tax" : "before tax";
    if (invoice.discount_type === "percent") {
      lines.push(
        moneyRow(`Discount (${invoice.discount_value}% ${when})`, invoice.discount_amount, width),
      );
    } else {
      lines.push(moneyRow(`Discount (${when})`, invoice.discount_amount, width));
    }
  };

  lines.push(moneyRow("Subtotal", invoice.subtotal, width));
  if (hasDiscount && timing !== "after_tax") pushDiscount();
  lines.push(moneyRow(`Tax (${taxPct}%)`, invoice.tax_amount, width));
  if (hasDiscount && timing === "after_tax") pushDiscount();
  lines.push(blank);
  lines.push(moneyRow("TOTAL", invoice.total, width));
  lines.push(blank);
  lines.push(inline("Paid by", String(invoice.payment_method || ""), width));

  const notes = (invoice.notes || "").trim();
  if (notes && on(settings, "receipt_show_notes")) {
    lines.push(blank);
    lines.push("Notes:");
    for (const noteLine of wrapText(notes, width)) lines.push(noteLine);
  }

  lines.push(blank);
  lines.push(double);
  lines.push(blank);

  if (on(settings, "receipt_show_thanks")) {
    lines.push(center("Thank you for your business!", width));
    lines.push(center("We appreciate your visit.", width));
    lines.push(blank);
  }

  if (on(settings, "receipt_show_footer")) {
    const footer = (settings.receipt_footer || "").trim();
    if (footer) {
      for (const part of footer.split("\n")) {
        for (const wrapped of wrapText(part, width)) {
          lines.push(center(wrapped, width));
        }
      }
      lines.push(blank);
    }
  }

  if (on(settings, "receipt_show_gst")) {
    const gst = (settings.gst_number || "").trim();
    if (gst) lines.push(center(`HST Reg. ${gst}`, width));
  }

  lines.push(blank);
  lines.push(double);
  lines.push(blank);
  lines.push(blank);
  return lines.join("\n");
}

/** Pick Courier size so `chars` columns fit inside printable width (mm). */
function fitCourierSize(doc: jsPDF, chars: number, printableWidthMm: number): number {
  const probe = "0".repeat(chars);
  let lo = 5;
  let hi = 12;
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2;
    doc.setFont("courier", "normal");
    doc.setFontSize(mid);
    const w = doc.getTextWidth(probe);
    if (w > printableWidthMm) hi = mid;
    else lo = mid;
  }
  // Slightly under so drivers / rounding never clip the last column
  return Math.max(5, lo * 0.98);
}

/**
 * Render the monospace thermal layout as a narrow PDF.
 * Safe margins on all sides so thermal / system print does not clip edges.
 */
export function buildReceiptPdf(invoice: Invoice, settings: AppSettings): jsPDF {
  const chars = printerWidthChars(settings);
  const pageWidthMm = settings.receipt_width === "58mm" ? 58 : 80;
  const marginX = MARGIN_X_MM;
  const marginTop = MARGIN_TOP_MM;
  const marginBottom = MARGIN_BOTTOM_MM;
  const printableWidth = pageWidthMm - marginX * 2;

  const text = buildReceiptText(invoice, settings);
  const textLines = text.split("\n");

  const showLogo = on(settings, "receipt_show_logo") && !!settings.logo_data;
  const logoDrawH = showLogo ? 22 : 0;

  // Measure Courier on a probe doc first so page height includes full bottom margin
  const probe = new jsPDF({ unit: "mm", format: [pageWidthMm, 200], hotfixes: ["px_scaling"] });
  probe.setFont("courier", "normal");
  let fontSize = fitCourierSize(probe, chars, printableWidth);
  const sizePref = (settings.receipt_font_size || "normal").toLowerCase();
  if (sizePref === "compact") fontSize *= 0.92;
  if (sizePref === "large") fontSize *= 1.06;
  probe.setFontSize(fontSize);
  if (probe.getTextWidth("0".repeat(chars)) > printableWidth) {
    fontSize = fitCourierSize(probe, chars, printableWidth);
  }
  const lineHeight = Math.max(2.4, fontSize * 0.42);

  const contentHeight =
    marginTop + logoDrawH + textLines.length * lineHeight + marginBottom;
  const pageHeightMm = Math.max(140, Math.ceil(contentHeight + 6));

  const doc = new jsPDF({
    unit: "mm",
    format: [pageWidthMm, pageHeightMm],
    hotfixes: ["px_scaling"],
  });

  let y = marginTop;

  if (showLogo && settings.logo_data) {
    try {
      const format = settings.logo_data.includes("image/png")
        ? "PNG"
        : settings.logo_data.includes("image/webp")
          ? "WEBP"
          : "JPEG";
      const logoW = 20;
      const logoH = 20;
      const logoX = (pageWidthMm - logoW) / 2;
      doc.addImage(settings.logo_data, format, logoX, y, logoW, logoH);
      y += logoH + 2;
    } catch {
      // continue without logo
    }
  }

  doc.setTextColor(0, 0, 0);
  const charWidthMm = printableWidth / chars;

  for (const raw of textLines) {
    // Lock to exact thermal width so Qty/Price/Total columns stay aligned
    const line = (raw.length > chars ? raw.slice(0, chars) : raw).padEnd(chars);
    const trimmed = line.trimEnd();
    const isTotal = /^\s*TOTAL\b/.test(line);
    const isBizName =
      on(settings, "receipt_show_business_name") &&
      trimmed === (settings.business_name || "My Business").trim().toUpperCase().slice(0, chars);
    const isSalesTitle = trimmed === "SALES RECEIPT";

    const size = isTotal || isBizName ? fontSize + 0.4 : isSalesTitle ? fontSize + 0.2 : fontSize;
    doc.setFont("courier", isTotal || isBizName ? "bold" : "normal");
    doc.setFontSize(size);

    // Draw glyph-by-glyph at fixed advances — true monospace lock (matches thermal)
    const baseline = y + lineHeight * 0.78;
    for (let i = 0; i < chars; i++) {
      const ch = line[i];
      if (ch && ch !== " ") {
        doc.text(ch, marginX + i * charWidthMm, baseline, { baseline: "alphabetic" });
      }
    }
    y += lineHeight;
  }

  return doc;
}

export function downloadReceiptPdf(invoice: Invoice, settings: AppSettings): void {
  const doc = buildReceiptPdf(invoice, settings);
  doc.save(`${invoice.invoice_number}.pdf`);
}

/** Opens the system print dialog via a hidden iframe (more reliable than window.open). */
export function openReceiptPrintDialog(invoice: Invoice, settings: AppSettings): void {
  const doc = buildReceiptPdf(invoice, settings);
  const blob = doc.output("blob");
  const url = URL.createObjectURL(blob);
  const iframe = document.createElement("iframe");
  iframe.setAttribute("title", "Print receipt");
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

export function sampleTestInvoice(): Invoice {
  const items: InvoiceItem[] = [
    {
      product_id: null,
      description: "iPad 11th Gen 128GB",
      serial_number: "Silver",
      qty: 2,
      unit_price: 639.99,
      line_total: 1279.98,
    },
    {
      product_id: null,
      description: "Hard Case",
      serial_number: "",
      qty: 2,
      unit_price: 34.99,
      line_total: 69.98,
    },
  ];
  return {
    id: null,
    invoice_number: "INV-786-0122",
    customer_name: "Hamilton Montesori",
    customer_phone: "",
    customer_email: "",
    subtotal: 1349.96,
    tax_rate: 0.13,
    tax_amount: 175.49,
    total: 1525.45,
    payment_method: "Cash",
    notes: "",
    created_at: "2026-09-03 18:58:00",
    items,
    discount_type: "",
    discount_value: 0,
    discount_amount: 0,
    discount_timing: "before_tax",
  };
}
