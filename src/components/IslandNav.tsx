import { Package, Receipt, ClockCounterClockwise, GearSix } from "@phosphor-icons/react";
import type { AppTab } from "../lib/types";

const TABS: { id: AppTab; label: string; shortcut: string; icon: typeof Receipt }[] = [
  { id: "sale", label: "Sale", shortcut: "F1", icon: Receipt },
  { id: "products", label: "Products", shortcut: "F2", icon: Package },
  { id: "history", label: "History", shortcut: "F3", icon: ClockCounterClockwise },
  { id: "setup", label: "Setup", shortcut: "F4", icon: GearSix },
];

export function IslandNav({
  active,
  onChange,
  businessName,
}: {
  active: AppTab;
  onChange: (tab: AppTab) => void;
  businessName: string;
}) {
  return (
    <header className="sticky top-0 z-20 px-4 pt-6">
      <div className="mx-auto flex max-w-[1440px] flex-col items-center gap-4">
        <div className="text-center">
          <p className="text-xs font-medium tracking-[0.14em] text-[var(--text-tertiary)] uppercase">
            Retail Invoice
          </p>
          <h1 className="hero-text mt-1 text-3xl font-semibold tracking-tight text-wrap-balance md:text-4xl">
            {businessName || "My Business"}
          </h1>
          <p className="mt-2 max-w-[680px] text-sm text-[var(--text-secondary)] text-pretty">
            Invoicing and inventory on this computer. Nothing is uploaded.
          </p>
        </div>

        <nav
          className="flex w-max max-w-full items-center gap-1 rounded-full border px-2 py-2 shadow-[var(--shadow)] backdrop-blur-md"
          style={{
            background: "color-mix(in srgb, var(--surface) 88%, transparent)",
            borderColor: "var(--border)",
          }}
          aria-label="Main"
        >
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const selected = active === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onChange(tab.id)}
                className="focus-ring flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.98]"
                style={{
                  background: selected ? "var(--accent-soft)" : "transparent",
                  color: selected ? "var(--accent)" : "var(--text-secondary)",
                }}
                aria-current={selected ? "page" : undefined}
              >
                <Icon size={18} weight={selected ? "fill" : "regular"} />
                <span>{tab.label}</span>
                <span className="hidden text-xs text-[var(--text-tertiary)] sm:inline">
                  {tab.shortcut}
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
