import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type ToastKind = "info" | "success" | "error";

interface ToastItem {
  id: number;
  message: string;
  kind: ToastKind;
}

interface ToastContextValue {
  push: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, kind: ToastKind = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, kind }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-40 flex w-80 flex-col gap-2">
        {items.map((t) => (
          <button
            key={t.id}
            type="button"
            className="pointer-events-auto rounded-lg border px-4 py-3 text-left text-sm shadow-[var(--shadow)] transition-[transform,opacity] duration-[400ms] ease-[ease]"
            style={{
              background: "var(--surface-raised)",
              borderColor:
                t.kind === "error"
                  ? "var(--danger)"
                  : t.kind === "success"
                    ? "var(--accent)"
                    : "var(--border)",
              color: "var(--text)",
              animation: "statusIn 180ms cubic-bezier(0.23, 1, 0.32, 1)",
            }}
            onClick={() => setItems((prev) => prev.filter((x) => x.id !== t.id))}
          >
            {t.message}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast requires ToastProvider");
  return ctx;
}
