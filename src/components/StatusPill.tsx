import { useEffect, useId, useRef, useState } from "react";
import { CheckCircle, WarningCircle, Circle } from "@phosphor-icons/react";
import { getAllSettings } from "../db/queries";
import { getDatabase } from "../db/client";
import { emailStatus, printerStatus, statusLabel, type LinkStatus } from "../lib/status";
import type { AppTab } from "../lib/types";

function Dot({ status }: { status: LinkStatus }) {
  if (status === "ready") {
    return <CheckCircle size={14} weight="fill" className="text-[var(--accent)]" />;
  }
  if (status === "failed") {
    return <WarningCircle size={14} weight="fill" className="text-[var(--danger)]" />;
  }
  return <Circle size={14} className="text-[var(--text-tertiary)]" />;
}

export function StatusPill({ onGoSetup }: { onGoSetup: (tab: AppTab) => void }) {
  const [open, setOpen] = useState(false);
  const [printer, setPrinter] = useState<LinkStatus>("untested");
  const [email, setEmail] = useState<LinkStatus>("needs_setup");
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);

  function refresh() {
    const settings = getAllSettings(getDatabase());
    setPrinter(printerStatus(settings));
    setEmail(emailStatus(settings));
  }

  useEffect(() => {
    refresh();
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  useEffect(() => {
    if (!open) return;
    refresh();
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const overall: LinkStatus =
    printer === "failed" || email === "failed"
      ? "failed"
      : printer === "ready" && email === "ready"
        ? "ready"
        : "untested";

  const summary =
    overall === "ready"
      ? "All set · local"
      : overall === "failed"
        ? "Needs attention"
        : "Local · setup";

  return (
    <div ref={rootRef} className="relative ml-auto shrink-0">
      <button
        type="button"
        className="focus-ring flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition-[transform,opacity,background-color] duration-160 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97]"
        style={{
          borderColor: "var(--border)",
          background: open ? "var(--accent-soft)" : "var(--bg)",
          color: "var(--text-secondary)",
        }}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => {
          if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
            setOpen(true);
          }
        }}
      >
        <Dot status={overall} />
        <span>{summary}</span>
      </button>

      {open ? (
        <div
          id={panelId}
          role="dialog"
          aria-label="Connection status"
          className="absolute right-0 top-[calc(100%+8px)] z-30 w-72 origin-top-right rounded-xl border p-4 shadow-[var(--shadow)]"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            animation: "statusIn 180ms cubic-bezier(0.23, 1, 0.32, 1)",
          }}
          onMouseLeave={() => {
            if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
              setOpen(false);
            }
          }}
        >
          <p className="text-xs font-medium tracking-[0.08em] text-[var(--text-tertiary)] uppercase">
            On this computer
          </p>
          <ul className="mt-3 space-y-3">
            <li className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 text-sm">
                <Dot status={printer} />
                <span>{statusLabel("printer", printer)}</span>
              </div>
              <button
                type="button"
                className="focus-ring text-xs font-semibold text-[var(--accent)] transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97]"
                onClick={() => {
                  setOpen(false);
                  onGoSetup("setup");
                }}
              >
                Test
              </button>
            </li>
            <li className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 text-sm">
                <Dot status={email} />
                <span>{statusLabel("email", email)}</span>
              </div>
              <button
                type="button"
                className="focus-ring text-xs font-semibold text-[var(--accent)] transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97]"
                onClick={() => {
                  setOpen(false);
                  onGoSetup("setup");
                }}
              >
                Setup
              </button>
            </li>
          </ul>
          <p className="mt-3 text-xs text-[var(--text-tertiary)] text-pretty">
            Sales and inventory stay on this machine. Nothing is uploaded.
          </p>
        </div>
      ) : null}
    </div>
  );
}
