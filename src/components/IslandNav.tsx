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
    <header
      className="z-20 shrink-0 border-b px-4"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-4">
        <div className="min-w-0 shrink-0">
          <p className="text-[10px] font-medium tracking-[0.12em] text-[var(--text-tertiary)] uppercase">
            Retail Invoice
          </p>
          <h1 className="truncate text-base font-semibold tracking-tight text-[var(--text)]">
            {businessName || "My Business"}
          </h1>
        </div>

        <nav
          className="flex min-w-0 flex-1 items-center justify-start gap-1 overflow-x-auto rounded-full border px-1 py-1 sm:flex-none"
          style={{
            background: "var(--bg)",
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
                className="focus-ring flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.98]"
                style={{
                  background: selected ? "var(--accent-soft)" : "transparent",
                  color: selected ? "var(--accent)" : "var(--text-secondary)",
                }}
                aria-current={selected ? "page" : undefined}
              >
                <Icon size={16} weight={selected ? "fill" : "regular"} />
                <span>{tab.label}</span>
                <span className="hidden text-xs text-[var(--text-tertiary)] lg:inline">
                  {tab.shortcut}
                </span>
              </button>
            );
          })}
        </nav>

        <p className="ml-auto hidden shrink-0 text-xs text-[var(--text-tertiary)] xl:block">
          Local only
        </p>
      </div>
    </header>
  );
}
