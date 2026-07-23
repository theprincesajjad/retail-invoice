import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-48 flex-col items-start justify-center gap-3 py-12">
      <h3 className="text-2xl font-semibold tracking-tight text-[var(--text)] text-wrap-balance">
        {title}
      </h3>
      <p className="max-w-md text-base text-[var(--text-secondary)] text-pretty">{body}</p>
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
