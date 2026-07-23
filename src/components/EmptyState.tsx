import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
  compact = false,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-start justify-center gap-2 ${compact ? "min-h-24 py-6" : "min-h-48 py-12"}`}
    >
      <h3
        className={`font-semibold tracking-tight text-[var(--text)] text-wrap-balance ${compact ? "text-lg" : "text-2xl"}`}
      >
        {title}
      </h3>
      <p className="max-w-md text-sm text-[var(--text-secondary)] text-pretty">{body}</p>
      {action}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-12 animate-pulse rounded-lg"
          style={{ background: "var(--bg-deep)" }}
        />
      ))}
    </div>
  );
}
