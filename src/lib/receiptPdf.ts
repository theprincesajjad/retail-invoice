import { jsPDF } from "jspdf";
import { formatCurrency } from "./money";
import type { AppSettings, Invoice } from "./types";

function show(settings: AppSettings, key: keyof AppSettings): boolean {
  return settings[key] === "1";
}

export function buildReceiptPdf(invoice: Invoice, settings: AppSettings): jsPDF {
  const doc = new jsPDF({ unit: "mm", format: [80, 220] });
  let y = 8;
  const left = 4;
  const width = 72;
  const line = (text: string, opts?: { bold?: boolean; size?: number; center?: boolean }) => {
    const size = opts?.size ?? 9;
    doc.setFont("helvetica", opts?.bold ? "bold" : "normal");
    doc.setFontSize(size);
    if (opts?.center) {
      doc.text(text, 40, y, { align: "center", maxWidth: width });
    } else {
      doc.text(text, left, y, { maxWidth: width });
    }
    y += size * 0.45 + 2;
  };

  if (show(settings, "receipt_show_logo") && settings.logo_data) {
    try {
      const format = settings.logo_data.includes("image/png") ? "PNG" : "JPEG";
      doc.addImage(settings.logo_data, format, 28, y, 24, 24);
      y += 28;
    } catch {
      // Ignore bad logo data and continue with text header
    }
  }

  if (show(settings, "receipt_show_business_name")) {
    line(settings.business_name || "My Business", { bold: true, size: 12, center: true });
  }
  if (show(settings, "receipt_show_tagline") && settings.business_tagline) {
    line(settings.business_tagline, { size: 8, center: true });
  }
  if (show(settings, "receipt_show_address") && settings.business_address) {
    line(settings.business_address, { size: 8, center: true });
  }
  if (show(settings, "receipt_show_phone") && settings.business_phone) {
    line(settings.business_phone, { size: 8, center: true });
  }
  if (show(settings, "receipt_show_email") && settings.business_email) {
    line(settings.business_email, { size: 8, center: true });
  }
  if (show(settings, "receipt_show_website") && settings.business_website) {
    line(settings.business_website, { size: 8, center: true });
  }
  if (show(settings, "receipt_show_gst") && settings.gst_number) {
    line(`Tax ID ${settings.gst_number}`, { size: 8, center: true });
  }

  y += 2;
  line(`Invoice ${invoice.invoice_number}`, { bold: true });
  line(invoice.created_at || new Date().toLocaleString(), { size: 8 });

  if (show(settings, "receipt_show_customer") && (invoice.customer_name || invoice.customer_phone)) {
    line(
      [invoice.customer_name, invoice.customer_phone].filter(Boolean).join(" · "),
      { size: 8 },
    );
  }

  y += 1;
  doc.setDrawColor(180);
  doc.line(left, y, left + width, y);
  y += 4;

  for (const item of invoice.items) {
    line(`${item.qty} × ${item.description}`, { bold: true, size: 9 });
    if (show(settings, "receipt_show_details") && item.serial_number) {
      line(item.serial_number, { size: 8 });
    }
    line(formatCurrency(item.line_total), { size: 9 });
    y += 1;
  }

  doc.line(left, y, left + width, y);
  y += 4;
  line(`Subtotal  ${formatCurrency(invoice.subtotal)}`);
  if (invoice.discount_amount > 0) {
    line(`Discount  −${formatCurrency(invoice.discount_amount)}`);
  }
  line(`Tax  ${formatCurrency(invoice.tax_amount)}`);
  line(`Total  ${formatCurrency(invoice.total)}`, { bold: true, size: 11 });
  line(`Paid by ${invoice.payment_method}`, { size: 8 });

  if (show(settings, "receipt_show_notes") && invoice.notes) {
    y += 2;
    line(invoice.notes, { size: 8 });
  }
  if (show(settings, "receipt_show_thanks")) {
    y += 2;
    line("Thank you", { center: true, size: 9 });
  }
  if (show(settings, "receipt_show_footer") && settings.receipt_footer) {
    line(settings.receipt_footer, { center: true, size: 7 });
  }

  const pageHeight = Math.max(200, y + 10);
  doc.internal.pageSize.height = pageHeight;
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
  return {
    id: null,
    invoice_number: "TEST-PRINT",
    customer_name: "Test print",
    customer_phone: "",
    customer_email: "",
    subtotal: 10,
    tax_rate: 0.13,
    tax_amount: 1.3,
    total: 11.3,
    payment_method: "Cash",
    notes: "Printer connection test",
    created_at: new Date().toLocaleString(),
    items: [
      {
        product_id: null,
        description: "Test item",
        serial_number: "",
        qty: 1,
        unit_price: 10,
        line_total: 10,
      },
    ],
    discount_type: "",
    discount_value: 0,
    discount_amount: 0,
    discount_timing: "before_tax",
  };
}
