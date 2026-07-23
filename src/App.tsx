import { useCallback, useEffect, useState } from "react";
import { IslandNav } from "./components/IslandNav";
import { ToastProvider } from "./components/Toast";
import { getAllSettings } from "./db/queries";
import { openDatabase, getDatabase } from "./db/client";
import type { AppTab, ThemePreference } from "./lib/types";
import { HistoryPage } from "./pages/HistoryPage";
import { ProductsPage } from "./pages/ProductsPage";
import { SalePage } from "./pages/SalePage";
import { SetupPage } from "./pages/SetupPage";
import { SetupWizard } from "./pages/SetupWizard";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<AppTab>("sale");
  const [businessName, setBusinessName] = useState("My Business");
  const [showWizard, setShowWizard] = useState(false);
  const [themeInitial, setThemeInitial] = useState<ThemePreference>("light");

  const refreshBrand = useCallback(() => {
    const settings = getAllSettings(getDatabase());
    setBusinessName(settings.business_name || "My Business");
    setThemeInitial((settings.theme_preference as ThemePreference) || "light");
    setShowWizard(settings.setup_complete !== "1");
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await openDatabase();
        if (cancelled) return;
        refreshBrand();
        setReady(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not open local database");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshBrand]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "F1") {
        e.preventDefault();
        setTab("sale");
      } else if (e.key === "F2") {
        e.preventDefault();
        setTab("products");
      } else if (e.key === "F3") {
        e.preventDefault();
        setTab("history");
      } else if (e.key === "F4") {
        e.preventDefault();
        setTab("setup");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (error) {
    return (
      <div className="flex h-dvh items-center justify-center p-8">
        <div className="max-w-md">
          <h1 className="text-2xl font-semibold">Could not start</h1>
          <p className="mt-2 text-[var(--text-secondary)]">{error}</p>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <p className="text-[var(--text-secondary)]">Opening local database…</p>
      </div>
    );
  }

  return (
    <ThemeProvider initial={themeInitial}>
      <ToastProvider>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <div className="grain" aria-hidden />
        <div className="flex h-dvh flex-col overflow-hidden">
          <IslandNav active={tab} onChange={setTab} businessName={businessName} />
          <main id="main" className="min-h-0 flex-1 overflow-hidden px-4 py-3">
            <div className="h-full overflow-y-auto">
              {tab === "sale" ? <div className="h-full overflow-hidden"><SalePage /></div> : null}
              {tab === "products" ? <ProductsPage /> : null}
              {tab === "history" ? <HistoryPage /> : null}
              {tab === "setup" ? <SetupPage onSaved={refreshBrand} /> : null}
            </div>
          </main>
        </div>
        {showWizard ? (
          <SetupWizard
            onDone={() => {
              refreshBrand();
              setShowWizard(false);
            }}
          />
        ) : null}
      </ToastProvider>
    </ThemeProvider>
  );
}
