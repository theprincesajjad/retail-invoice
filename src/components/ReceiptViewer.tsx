import { useEffect, useState } from "react";
import { buildReceiptPdf, openReceiptPrintDialog } from "../lib/receiptPdf";
import type { AppSettings, Invoice } from "../lib/types";
import { Button } from "./ui";

export function ReceiptViewer({
  open,
  invoice,
  settings,
  onClose,
}: {
  open: boolean;
  invoice: Invoice | null;
  settings: AppSettings;
  onClose: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !invoice) {
      setUrl(null);
      return;
    }
    const doc = buildReceiptPdf(invoice, settings);
    const blob = doc.output("blob");
    const next = URL.createObjectURL(blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [open, invoice, settings]);

  if (!open || !invoice) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Receipt ${invoice.invoice_number}`}
    >
      <button
        type="button"
        className="absolute inset-0"
        style={{ background: "var(--scrim)" }}
        aria-label="Close"
        onClick={onClose}
      />
      <div
        className="relative z-10 flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-xl border shadow-[var(--shadow)]"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          transformOrigin: "center",
          animation: "dialogIn 200ms cubic-bezier(0.23, 1, 0.32, 1)",
        }}
      >
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-lg font-semibold tracking-tight">{invoice.invoice_number}</h2>
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => openReceiptPrintDialog(invoice, settings)}
            >
              Print
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
        <div className="min-h-0 flex-1 bg-[var(--bg-deep)] p-3">
          {url ? (
            <iframe title="Receipt preview" src={url} className="h-[min(70dvh,640px)] w-full rounded-lg border-0 bg-white" />
          ) : (
            <p className="p-6 text-sm text-[var(--text-secondary)]">Loading receipt…</p>
          )}
        </div>
      </div>
    </div>
  );
}
