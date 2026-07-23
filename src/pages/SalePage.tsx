import { useEffect, useMemo, useState } from "react";
import {
  generateInvoiceNumber,
  getAllSettings,
  saveInvoice,
  searchProducts,
} from "../db/queries";
import { getDatabase, schedulePersist } from "../db/client";
import { computeInvoiceTotals, formatCurrency, parseCurrency } from "../lib/money";
import { downloadReceiptPdf, openReceiptPrintDialog } from "../lib/receiptPdf";
import type {
  DiscountTiming,
  DiscountType,
  Invoice,
  InvoiceItem,
  PaymentMethod,
  Product,
} from "../lib/types";
import { useToast } from "../components/Toast";
import { Button, Dialog, Field, inputClass, inputStyle } from "../components/ui";
import { EmptyState } from "../components/EmptyState";

interface LineDraft extends InvoiceItem {
  key: string;
}

export function SalePage() {
  const toast = useToast();
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [search, setSearch] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSku, setSelectedSku] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [notes, setNotes] = useState("");
  const [discountType, setDiscountType] = useState<DiscountType>("percent");
  const [discountValue, setDiscountValue] = useState("0");
  const [discountTiming, setDiscountTiming] = useState<DiscountTiming>("before_tax");
  const [taxRate, setTaxRate] = useState(0.13);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [payment, setPayment] = useState<PaymentMethod>("Cash");
  const [manualDesc, setManualDesc] = useState("");
  const [manualPrice, setManualPrice] = useState("");
  const [manualQty, setManualQty] = useState("1");
  const [manualDetails, setManualDetails] = useState("");

  useEffect(() => {
    const db = getDatabase();
    const settings = getAllSettings(db);
    setTaxRate(Number(settings.tax_rate) || 0.13);
    setDiscountTiming((settings.discount_timing as DiscountTiming) || "before_tax");
  }, []);

  useEffect(() => {
    const db = getDatabase();
    setProducts(searchProducts(db, search));
  }, [search]);

  const totals = useMemo(
    () =>
      computeInvoiceTotals(
        lines,
        taxRate,
        discountType,
        Number(discountValue) || 0,
        discountTiming,
      ),
    [lines, taxRate, discountType, discountValue, discountTiming],
  );

  const selectedProduct = products.find((p) => {
    const label = `${p.sku} — ${p.name}`;
    return label === selectedSku || p.sku === selectedSku;
  });

  function addProductLine(product: Product, qty = 1) {
    setLines((prev) => {
      const existing = prev.find((l) => l.product_id === product.id);
      if (existing) {
        return prev.map((l) =>
          l.key === existing.key
            ? {
                ...l,
                qty: l.qty + qty,
                line_total: (l.qty + qty) * l.unit_price,
              }
            : l,
        );
      }
      return [
        ...prev,
        {
          key: crypto.randomUUID(),
          product_id: product.id,
          description: product.name,
          serial_number: product.serial_number,
          qty,
          unit_price: product.price,
          line_total: product.price * qty,
        },
      ];
    });
  }

  function addFromSearch() {
    if (!selectedProduct) {
      toast.push("Choose a product from the list first", "error");
      return;
    }
    addProductLine(selectedProduct, 1);
    setSearch("");
    setSelectedSku("");
  }

  function addManual() {
    const price = parseCurrency(manualPrice);
    const qty = Math.max(1, Number.parseInt(manualQty, 10) || 1);
    if (!manualDesc.trim()) {
      toast.push("Enter a description for the custom line", "error");
      return;
    }
    setLines((prev) => [
      ...prev,
      {
        key: crypto.randomUUID(),
        product_id: null,
        description: manualDesc.trim(),
        serial_number: manualDetails.trim(),
        qty,
        unit_price: price,
        line_total: price * qty,
      },
    ]);
    setManualDesc("");
    setManualPrice("");
    setManualQty("1");
    setManualDetails("");
  }

  function updateQty(key: string, qty: number) {
    const next = Math.max(1, qty);
    setLines((prev) =>
      prev.map((l) =>
        l.key === key ? { ...l, qty: next, line_total: next * l.unit_price } : l,
      ),
    );
  }

  function removeLine(key: string) {
    setLines((prev) => prev.filter((l) => l.key !== key));
  }

  function beginComplete() {
    if (!lines.length) {
      toast.push("Add at least one item before completing the sale", "error");
      return;
    }
    setPaymentOpen(true);
  }

  function confirmPayment(method: PaymentMethod) {
    setPayment(method);
    setPaymentOpen(false);
    setConfirmOpen(true);
  }

  function finalize(print: boolean) {
    const db = getDatabase();
    const settings = getAllSettings(db);
    const invoice: Invoice = {
      id: null,
      invoice_number: generateInvoiceNumber(db),
      customer_name: customerName.trim(),
      customer_phone: customerPhone.trim(),
      customer_email: customerEmail.trim(),
      subtotal: totals.subtotal,
      tax_rate: taxRate,
      tax_amount: totals.tax_amount,
      total: totals.total,
      payment_method: payment,
      notes: notes.trim(),
      created_at: new Date().toISOString().replace("T", " ").slice(0, 19),
      items: lines,
      discount_type: discountType,
      discount_value: Number(discountValue) || 0,
      discount_amount: totals.discount_amount,
      discount_timing: discountTiming,
    };
    saveInvoice(db, invoice, lines);
    schedulePersist();
    if (print) {
      openReceiptPrintDialog(invoice, settings);
    } else {
      downloadReceiptPdf(invoice, settings);
    }
    toast.push(`Sale ${invoice.invoice_number} saved`, "success");
    setLines([]);
    setCustomerName("");
    setCustomerPhone("");
    setCustomerEmail("");
    setNotes("");
    setDiscountValue("0");
    setConfirmOpen(false);
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "F10") {
        e.preventDefault();
        if (!lines.length) return;
        setPayment("Cash");
        finalize(false);
      }
      if (e.key === "F11") {
        e.preventDefault();
        if (!lines.length) return;
        const db = getDatabase();
        const settings = getAllSettings(db);
        const preview: Invoice = {
          id: null,
          invoice_number: "PREVIEW",
          customer_name: customerName,
          customer_phone: customerPhone,
          customer_email: customerEmail,
          subtotal: totals.subtotal,
          tax_rate: taxRate,
          tax_amount: totals.tax_amount,
          total: totals.total,
          payment_method: payment,
          notes,
          created_at: new Date().toLocaleString(),
          items: lines,
          discount_type: discountType,
          discount_value: Number(discountValue) || 0,
          discount_amount: totals.discount_amount,
          discount_timing: discountTiming,
        };
        openReceiptPrintDialog(preview, settings);
      }
      if (e.key === "F12") {
        e.preventDefault();
        if (confirmOpen) {
          finalize(true);
          return;
        }
        if (paymentOpen) return;
        beginComplete();
      }
      if (paymentOpen && e.key === "F7") {
        e.preventDefault();
        confirmPayment("Cash");
      }
      if (paymentOpen && e.key === "F8") {
        e.preventDefault();
        confirmPayment("Card");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines, paymentOpen, confirmOpen, totals, customerName, customerPhone, customerEmail, notes, payment, discountType, discountValue, discountTiming, taxRate]);

  return (
    <div className="mx-auto grid max-w-[1440px] gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
      <section className="min-w-0">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Name">
            <input
              className={inputClass}
              style={inputStyle()}
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="Customer name"
            />
          </Field>
          <Field label="Phone">
            <input
              className={inputClass}
              style={inputStyle()}
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              placeholder="(416) 555-0100"
            />
          </Field>
          <Field label="Email">
            <input
              className={inputClass}
              style={inputStyle()}
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              placeholder="name@email.com"
            />
          </Field>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-[140px_minmax(0,1fr)_auto]">
          <Field label="Search">
            <input
              className={inputClass}
              style={inputStyle()}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="SKU or name"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (products[0]) {
                    setSelectedSku(`${products[0].sku} — ${products[0].name}`);
                    addProductLine(products[0], 1);
                    setSearch("");
                  }
                }
              }}
            />
          </Field>
          <Field label="Product">
            <select
              className={inputClass}
              style={inputStyle()}
              value={selectedSku}
              onChange={(e) => setSelectedSku(e.target.value)}
            >
              <option value="">Choose a product</option>
              {products.map((p) => (
                <option key={p.id ?? p.sku} value={`${p.sku} — ${p.name}`}>
                  {p.sku} — {p.name} — stock {p.qty} — {formatCurrency(p.price)}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex items-end">
            <Button variant="primary" onClick={addFromSearch}>
              Add
            </Button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <Field label="Custom item">
            <input
              className={inputClass}
              style={inputStyle()}
              value={manualDesc}
              onChange={(e) => setManualDesc(e.target.value)}
              placeholder="Description"
            />
          </Field>
          <Field label="Details">
            <input
              className={inputClass}
              style={inputStyle()}
              value={manualDetails}
              onChange={(e) => setManualDetails(e.target.value)}
              placeholder="Optional"
            />
          </Field>
          <Field label="Qty">
            <input
              className={`${inputClass} tabular`}
              style={inputStyle()}
              value={manualQty}
              onChange={(e) => setManualQty(e.target.value)}
            />
          </Field>
          <div className="grid grid-cols-[1fr_auto] items-end gap-2">
            <Field label="Price">
              <input
                className={`${inputClass} tabular`}
                style={inputStyle()}
                value={manualPrice}
                onChange={(e) => setManualPrice(e.target.value)}
                placeholder="0.00"
              />
            </Field>
            <Button onClick={addManual}>Add</Button>
          </div>
        </div>

        <div className="mt-8">
          <div
            className="grid grid-cols-[minmax(0,1fr)_72px_100px_100px_44px] gap-2 border-b pb-2 text-sm text-[var(--text-secondary)]"
            style={{ borderColor: "var(--border)" }}
          >
            <span>Item</span>
            <span>Qty</span>
            <span className="text-right">Price</span>
            <span className="text-right">Total</span>
            <span />
          </div>
          {!lines.length ? (
            <EmptyState
              title="Ready for the next sale"
              body="Search a product or add a custom line. Complete sale when the cart looks right."
            />
          ) : (
            <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
              {lines.map((line) => (
                <li
                  key={line.key}
                  className="grid grid-cols-[minmax(0,1fr)_72px_100px_100px_44px] items-center gap-2 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{line.description}</p>
                    {line.serial_number ? (
                      <p className="truncate text-sm text-[var(--text-tertiary)]">
                        {line.serial_number}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className="focus-ring h-8 w-8 rounded-md border text-sm"
                      style={{ borderColor: "var(--border)" }}
                      onClick={() => updateQty(line.key, line.qty - 1)}
                    >
                      −
                    </button>
                    <span className="tabular w-6 text-center text-sm">{line.qty}</span>
                    <button
                      type="button"
                      className="focus-ring h-8 w-8 rounded-md border text-sm"
                      style={{ borderColor: "var(--border)" }}
                      onClick={() => updateQty(line.key, line.qty + 1)}
                    >
                      +
                    </button>
                  </div>
                  <span className="tabular text-right text-sm">
                    {formatCurrency(line.unit_price)}
                  </span>
                  <span className="tabular text-right font-medium">
                    {formatCurrency(line.line_total)}
                  </span>
                  <button
                    type="button"
                    className="focus-ring text-sm text-[var(--danger)]"
                    onClick={() => removeLine(line.key)}
                    aria-label="Remove line"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <aside className="lg:sticky lg:top-36 lg:self-start">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold tracking-tight">Totals</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--text-secondary)]">Subtotal</dt>
              <dd className="tabular font-medium">{formatCurrency(totals.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--text-secondary)]">Discount</dt>
              <dd className="tabular">−{formatCurrency(totals.discount_amount)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--text-secondary)]">Tax</dt>
              <dd className="tabular">{formatCurrency(totals.tax_amount)}</dd>
            </div>
            <div className="flex justify-between border-t pt-2 text-base" style={{ borderColor: "var(--border)" }}>
              <dt className="font-semibold">Total</dt>
              <dd className="tabular font-semibold">{formatCurrency(totals.total)}</dd>
            </div>
          </dl>

          <Field label="Discount">
            <div className="grid grid-cols-[1fr_100px] gap-2">
              <input
                className={`${inputClass} tabular`}
                style={inputStyle()}
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
              />
              <select
                className={inputClass}
                style={inputStyle()}
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value as DiscountType)}
              >
                <option value="percent">%</option>
                <option value="fixed">$</option>
              </select>
            </div>
          </Field>
          <Field label="Apply discount">
            <select
              className={inputClass}
              style={inputStyle()}
              value={discountTiming}
              onChange={(e) => setDiscountTiming(e.target.value as DiscountTiming)}
            >
              <option value="before_tax">Before tax</option>
              <option value="after_tax">After tax</option>
            </select>
          </Field>
          <Field label="Notes">
            <textarea
              className={`${inputClass} min-h-20 resize-y`}
              style={inputStyle()}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional note on the receipt"
            />
          </Field>

          <div className="flex flex-col gap-2 pt-2">
            <Button variant="primary" className="w-full py-3" onClick={beginComplete}>
              Complete sale · F12
            </Button>
            <Button
              className="w-full"
              onClick={() => {
                if (!lines.length) {
                  toast.push("Nothing to preview yet", "error");
                  return;
                }
                const db = getDatabase();
                openReceiptPrintDialog(
                  {
                    id: null,
                    invoice_number: "PREVIEW",
                    customer_name: customerName,
                    customer_phone: customerPhone,
                    customer_email: customerEmail,
                    subtotal: totals.subtotal,
                    tax_rate: taxRate,
                    tax_amount: totals.tax_amount,
                    total: totals.total,
                    payment_method: payment,
                    notes,
                    created_at: new Date().toLocaleString(),
                    items: lines,
                    discount_type: discountType,
                    discount_value: Number(discountValue) || 0,
                    discount_amount: totals.discount_amount,
                    discount_timing: discountTiming,
                  },
                  getAllSettings(db),
                );
              }}
            >
              Preview receipt · F11
            </Button>
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => {
                setLines([]);
                setNotes("");
                setDiscountValue("0");
              }}
            >
              Clear sale
            </Button>
          </div>
        </div>
      </aside>

      <Dialog open={paymentOpen} title="How did they pay?" onClose={() => setPaymentOpen(false)}>
        <p className="text-sm text-[var(--text-secondary)]">
          Choose a payment method. F7 Cash · F8 Card
        </p>
        <div className="mt-4 grid gap-2">
          {(["Cash", "Card", "Other"] as PaymentMethod[]).map((m) => (
            <Button key={m} variant={m === "Cash" ? "primary" : "secondary"} onClick={() => confirmPayment(m)}>
              {m}
              {m === "Cash" ? " · F7" : m === "Card" ? " · F8" : ""}
            </Button>
          ))}
        </div>
      </Dialog>

      <Dialog open={confirmOpen} title="Confirm sale" onClose={() => setConfirmOpen(false)}>
        <p className="text-base text-[var(--text-secondary)]">
          Charge <span className="tabular font-semibold text-[var(--text)]">{formatCurrency(totals.total)}</span> via{" "}
          {payment}?
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Button variant="primary" onClick={() => finalize(true)}>
            Save and print · F12
          </Button>
          <Button onClick={() => finalize(false)}>Save PDF only</Button>
          <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
