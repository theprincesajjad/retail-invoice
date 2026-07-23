import type { CSSProperties, ReactNode } from "react";

export function Dialog({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <button
        type="button"
        className="absolute inset-0"
        style={{ background: "var(--scrim)" }}
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        className="relative z-10 w-full max-w-md rounded-xl border p-6 shadow-[var(--shadow)] transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <h2 className="text-xl font-semibold tracking-tight text-[var(--text)] text-wrap-balance">
          {title}
        </h2>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}

export function Button({
  children,
  variant = "secondary",
  className = "",
  type = "button",
  disabled,
  onClick,
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  const styles: Record<string, CSSProperties> = {
    primary: {
      background: "var(--accent)",
      color: "#fff",
      borderColor: "transparent",
    },
    secondary: {
      background: "var(--surface)",
      color: "var(--text)",
      borderColor: "var(--border-strong)",
    },
    danger: {
      background: "var(--danger-soft)",
      color: "var(--danger)",
      borderColor: "transparent",
    },
    ghost: {
      background: "transparent",
      color: "var(--text-secondary)",
      borderColor: "transparent",
    },
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`focus-ring inline-flex items-center justify-center rounded-lg border px-3 py-2 text-base font-semibold transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)] hover:opacity-95 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      style={styles[variant]}
      onMouseEnter={(e) => {
        if (variant === "primary") {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--accent-hover)";
        }
      }}
      onMouseLeave={(e) => {
        if (variant === "primary") {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--accent)";
        }
      }}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium text-[var(--text)]">{label}</span>
      {hint ? <span className="text-xs text-[var(--text-tertiary)]">{hint}</span> : null}
      {children}
    </label>
  );
}

export const inputClass =
  "focus-ring w-full rounded-lg border bg-[var(--surface)] px-3 py-2 text-base text-[var(--text)] outline-none transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)] placeholder:text-[var(--text-tertiary)]";

export function inputStyle(): CSSProperties {
  return { borderColor: "var(--border-strong)" };
}
