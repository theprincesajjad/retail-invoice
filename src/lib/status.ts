import type { AppSettings } from "./types";

export type LinkStatus = "ready" | "needs_setup" | "failed" | "untested";

export function emailStatus(settings: AppSettings): LinkStatus {
  if (settings.smtp_email?.trim() && settings.smtp_password?.trim()) return "ready";
  return "needs_setup";
}

export function printerStatus(settings: AppSettings): LinkStatus {
  const s = (settings.printer_status || "untested").toLowerCase();
  if (s === "ready" || s === "failed" || s === "untested") return s;
  return "untested";
}

export function statusLabel(kind: "printer" | "email", status: LinkStatus): string {
  if (kind === "printer") {
    if (status === "ready") return "Printer ready";
    if (status === "failed") return "Print test failed";
    return "Printer not tested";
  }
  if (status === "ready") return "Email connected";
  return "Email not set up";
}
