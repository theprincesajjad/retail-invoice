import { useEffect, useMemo, useState } from "react";
import { getAllSettings, searchInvoices } from "../db/queries";
import { getDatabase } from "../db/client";
import { formatCurrency } from "../lib/money";
import { downloadReceiptPdf, openReceiptPrintDialog } from "../lib/receiptPdf";
import type { Invoice } from "../lib/types";
import { EmptyState, SkeletonRows } from "../components/EmptyState";
import { useToast } from "../components/Toast";
import { Button, Field, inputClass, inputStyle } from "../components/ui";
import { invoke } from "@tauri-apps/api/core";

type Period = "today" | "week" | "month" | "quarter" | "year" | "all";

function rangeFor(period: Period): { start?: string; end?: string } {
  if (period === "all") return {};
  const now = new Date();
  const end = new Date(now);
  end.setHours(23, 59, 59, 999);
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  if (period === "week") start.setDate(start.getDate() - start.getDay());
  if (period === "month") start.setDate(1);
  if (period === "quarter") {
    const q = Math.floor(start.getMonth() / 3) * 3;
    start.setMonth(q, 1);
  }
  if (period === "year") start.setMonth(0, 1);
  const fmt = (d: Date) => d.toISOString().slice(0, 19).replace("T", " ");
  return { start: fmt(start), end: fmt(end) };
}

export function HistoryPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<Period>("today");
  const [query, setQuery] = useState("");
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  function refresh() {
    const db = getDatabase();
    const { start, end } = rangeFor(period);
    setInvoices(searchInvoices(db, query, start, end));
    setLoading(false);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, query]);

  const stats = useMemo(() => {
    const count = invoices.length;
    const revenue = invoices.reduce((s, i) => s + i.total, 0);
    const avg = count ? revenue / count : 0;
    return { count, revenue, avg };
  }, [invoices]);

  async function emailInvoice(invoice: Invoice) {
    const settings = getAllSettings(getDatabase());
    if (!invoice.customer_email) {
      toast.push("This sale has no customer email", "error");
      return;
    }
    if (!settings.smtp_email || !settings.smtp_password) {
      toast.push("Add SMTP details in Setup before emailing", "error");
      return;
    }
    try {
      await invoke("send_invoice_email", {
        host: settings.smtp_host,
        port: Number(settings.smtp_port) || 587,
        username: settings.smtp_email,
        password: settings.smtp_password,
        fromName: settings.smtp_from_name || settings.business_name,
        toEmail: invoice.customer_email,
        subject: `Receipt ${invoice.invoice_number} from ${settings.business_name}`,
        body: `Thank you for your purchase.\n\nInvoice: ${invoice.invoice_number}\nTotal: ${formatCurrency(invoice.total)}\n\nAll data for this business stays on the shop computer.`,
      });
      toast.push("Email sent", "success");
    } catch (err) {
      toast.push(
        typeof err === "string" ? err : "Email could not be sent. Check SMTP settings.",
        "error",
      );
    }
  }

  return (
    <div className="mx-auto max-w-[1440px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Sales history</h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Review, reprint, or email receipts from sales on this computer.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className={inputClass}
            style={{ ...inputStyle(), width: 160 }}
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
          >
            <option value="today">Today</option>
            <option value="week">This week</option>
            <option value="month">This month</option>
            <option value="quarter">This quarter</option>
            <option value="year">This year</option>
            <option value="all">All time</option>
          </select>
          <Button onClick={refresh}>Refresh · Alt+R</Button>
        </div>
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-3">
        <div>
          <p className="text-sm text-[var(--text-tertiary)]">Sales</p>
          <p className="tabular mt-1 text-3xl font-semibold tracking-tight">{stats.count}</p>
        </div>
        <div>
          <p className="text-sm text-[var(--text-tertiary)]">Revenue</p>
          <p className="tabular mt-1 text-3xl font-semibold tracking-tight">
            {formatCurrency(stats.revenue)}
          </p>
        </div>
        <div>
          <p className="text-sm text-[var(--text-tertiary)]">Average ticket</p>
          <p className="tabular mt-1 text-3xl font-semibold tracking-tight">
            {formatCurrency(stats.avg)}
          </p>
        </div>
      </div>

      <div className="mt-8">
        <Field label="Search">
          <input
            className={inputClass}
            style={inputStyle()}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Customer, phone, item, or invoice number"
          />
        </Field>
      </div>

      <div className="mt-6">
        {loading ? (
          <SkeletonRows />
        ) : !invoices.length ? (
          <EmptyState
            title="No sales in this period"
            body="Completed sales will show up here with reprint and email actions."
          />
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
            {invoices.map((inv) => (
              <li key={inv.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div className="min-w-0">
                  <p className="font-semibold tracking-tight">
                    {inv.invoice_number}{" "}
                    <span className="tabular font-medium text-[var(--text-secondary)]">
                      {formatCurrency(inv.total)}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    {[inv.customer_name || "Walk-in", inv.payment_method, inv.created_at]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => openReceiptPrintDialog(inv, getAllSettings(getDatabase()))}
                  >
                    Print
                  </Button>
                  <Button
                    onClick={() => downloadReceiptPdf(inv, getAllSettings(getDatabase()))}
                  >
                    PDF
                  </Button>
                  <Button variant="ghost" onClick={() => void emailInvoice(inv)}>
                    Email
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
