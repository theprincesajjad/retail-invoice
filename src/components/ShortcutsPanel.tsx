import { SHORTCUTS, isMac } from "../lib/platform";

export function ShortcutsPanel({ compact = false }: { compact?: boolean }) {
  const mac = isMac();
  return (
    <div>
      {!compact ? (
        <p className="mb-3 text-sm text-[var(--text-secondary)] text-pretty">
          {mac
            ? "On Mac, use Command shortcuts. Function keys often control brightness and volume."
            : "On Windows, use the F keys for the fastest sale flow."}
        </p>
      ) : null}
      <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--border)" }}>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-[var(--text-tertiary)]" style={{ borderColor: "var(--border)" }}>
              <th className="px-3 py-2 font-medium">Action</th>
              <th className="px-3 py-2 font-medium">{mac ? "Mac" : "Windows"}</th>
              <th className="hidden px-3 py-2 font-medium sm:table-cell">
                {mac ? "Windows" : "Mac"}
              </th>
            </tr>
          </thead>
          <tbody>
            {SHORTCUTS.map((row) => (
              <tr key={row.action} className="border-b last:border-0" style={{ borderColor: "var(--border)" }}>
                <td className="px-3 py-2">{row.action}</td>
                <td className="tabular px-3 py-2 font-semibold">
                  {mac ? row.mac : row.windows}
                </td>
                <td className="tabular hidden px-3 py-2 text-[var(--text-tertiary)] sm:table-cell">
                  {mac ? row.windows : row.mac}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
