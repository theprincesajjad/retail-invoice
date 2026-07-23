import { useEffect, useState } from "react";
import { getAllSettings, saveSettings } from "../db/queries";
import {
  exportDatabaseBytes,
  getDatabase,
  getDbFilePathLabel,
  openDatabaseFromBytes,
  replaceDatabaseFromBytes,
  schedulePersist,
} from "../db/client";
import { importLegacyDatabase } from "../db/queries";
import type { AppSettings, ThemePreference } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";
import { useToast } from "../components/Toast";
import { Button, Field, inputClass, inputStyle } from "../components/ui";
import { saveAs } from "file-saver";

const RECEIPT_TOGGLES: { key: keyof AppSettings; label: string }[] = [
  { key: "receipt_show_logo", label: "Logo" },
  { key: "receipt_show_business_name", label: "Business name" },
  { key: "receipt_show_tagline", label: "Tagline" },
  { key: "receipt_show_address", label: "Address" },
  { key: "receipt_show_phone", label: "Phone" },
  { key: "receipt_show_website", label: "Website" },
  { key: "receipt_show_email", label: "Email" },
  { key: "receipt_show_customer", label: "Customer" },
  { key: "receipt_show_details", label: "Line details" },
  { key: "receipt_show_notes", label: "Notes" },
  { key: "receipt_show_thanks", label: "Thank you line" },
  { key: "receipt_show_footer", label: "Footer" },
  { key: "receipt_show_gst", label: "Tax ID" },
];

export function SetupPage({ onSaved }: { onSaved?: () => void }) {
  const toast = useToast();
  const { preference, setPreference } = useTheme();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const [dbPath, setDbPath] = useState("");

  useEffect(() => {
    setSettings(getAllSettings(getDatabase()));
    void getDbFilePathLabel().then(setDbPath);
  }, []);

  if (!settings) return null;

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function save() {
    if (!settings) return;
    saveSettings(getDatabase(), settings);
    schedulePersist();
    setPreference((settings.theme_preference as ThemePreference) || "light");
    toast.push("Settings saved", "success");
    onSaved?.();
  }

  async function backup() {
    const bytes = await exportDatabaseBytes();
    const copy = new Uint8Array(bytes);
    const blob = new Blob([copy], { type: "application/octet-stream" });
    saveAs(blob, `retail-invoice-backup-${new Date().toISOString().slice(0, 10)}.db`);
    toast.push("Backup downloaded", "success");
  }

  async function importLegacy(file: File) {
    const buf = new Uint8Array(await file.arrayBuffer());
    const source = await openDatabaseFromBytes(buf);
    const result = importLegacyDatabase(getDatabase(), source);
    schedulePersist();
    setSettings(getAllSettings(getDatabase()));
    toast.push(
      `Imported ${result.products} products and ${result.invoices} invoices`,
      "success",
    );
  }

  async function restoreBackup(file: File) {
    const buf = new Uint8Array(await file.arrayBuffer());
    await replaceDatabaseFromBytes(buf);
    setSettings(getAllSettings(getDatabase()));
    toast.push("Database restored from backup", "success");
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h2 className="text-xl font-semibold tracking-tight">Setup</h2>
      <p className="text-sm text-[var(--text-secondary)] text-pretty">
        All data stays on this computer. Nothing is uploaded.
      </p>

      <section className="mt-4 space-y-3">
        <h3 className="text-base font-semibold">Store</h3>
        <Field label="Business name">
          <input
            className={inputClass}
            style={inputStyle()}
            value={settings.business_name}
            onChange={(e) => update("business_name", e.target.value)}
          />
        </Field>
        <Field label="Tagline">
          <input
            className={inputClass}
            style={inputStyle()}
            value={settings.business_tagline}
            onChange={(e) => update("business_tagline", e.target.value)}
          />
        </Field>
        <Field label="Address">
          <input
            className={inputClass}
            style={inputStyle()}
            value={settings.business_address}
            onChange={(e) => update("business_address", e.target.value)}
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Phone">
            <input
              className={inputClass}
              style={inputStyle()}
              value={settings.business_phone}
              onChange={(e) => update("business_phone", e.target.value)}
            />
          </Field>
          <Field label="Email">
            <input
              className={inputClass}
              style={inputStyle()}
              value={settings.business_email}
              onChange={(e) => update("business_email", e.target.value)}
            />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Website">
            <input
              className={inputClass}
              style={inputStyle()}
              value={settings.business_website}
              onChange={(e) => update("business_website", e.target.value)}
            />
          </Field>
          <Field label="Tax ID">
            <input
              className={inputClass}
              style={inputStyle()}
              value={settings.gst_number}
              onChange={(e) => update("gst_number", e.target.value)}
            />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tax rate" hint="Example: 0.13 for 13%">
            <input
              className={`${inputClass} tabular`}
              style={inputStyle()}
              value={settings.tax_rate}
              onChange={(e) => update("tax_rate", e.target.value)}
            />
          </Field>
          <Field label="Default discount timing">
            <select
              className={inputClass}
              style={inputStyle()}
              value={settings.discount_timing}
              onChange={(e) => update("discount_timing", e.target.value)}
            >
              <option value="before_tax">Before tax</option>
              <option value="after_tax">After tax</option>
            </select>
          </Field>
        </div>
        <Field label="Receipt footer">
          <input
            className={inputClass}
            style={inputStyle()}
            value={settings.receipt_footer}
            onChange={(e) => update("receipt_footer", e.target.value)}
          />
        </Field>
        <Field label="Appearance">
          <select
            className={inputClass}
            style={inputStyle()}
            value={settings.theme_preference || preference}
            onChange={(e) => {
              const value = e.target.value as ThemePreference;
              update("theme_preference", value);
              setPreference(value);
            }}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </Field>
      </section>

      <section className="mt-10 space-y-3">
        <h3 className="text-lg font-semibold">Data on this computer</h3>
        <p className="text-sm text-[var(--text-secondary)]">Database location: {dbPath}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void backup()}>Download backup</Button>
          <label
            className="focus-ring inline-flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 text-base font-semibold"
            style={{ borderColor: "var(--border-strong)", background: "var(--surface)" }}
          >
            Restore backup
            <input
              type="file"
              accept=".db,application/octet-stream"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void restoreBackup(file);
                e.target.value = "";
              }}
            />
          </label>
          <label
            className="focus-ring inline-flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 text-base font-semibold"
            style={{ borderColor: "var(--border-strong)", background: "var(--surface)" }}
          >
            Import previous Retail Invoice database
            <input
              type="file"
              accept=".db,application/octet-stream"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void importLegacy(file);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </section>

      <div className="mt-10">
        <button
          type="button"
          className="focus-ring text-sm font-semibold text-[var(--accent)]"
          onClick={() => setAdvanced((v) => !v)}
        >
          {advanced ? "Hide advanced" : "Show advanced"} · receipt design and email
        </button>
      </div>

      {advanced ? (
        <>
          <section className="mt-6 space-y-3">
            <h3 className="text-lg font-semibold">Receipt design</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {RECEIPT_TOGGLES.map((t) => (
                <label key={t.key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={settings[t.key] === "1"}
                    onChange={(e) => update(t.key, e.target.checked ? "1" : "0")}
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </section>

          <section className="mt-8 space-y-3">
            <h3 className="text-lg font-semibold">Email receipts (optional)</h3>
            <p className="text-sm text-[var(--text-secondary)]">
              Only used when you press Email on a sale. Credentials stay in your local database.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="SMTP host">
                <input
                  className={inputClass}
                  style={inputStyle()}
                  value={settings.smtp_host}
                  onChange={(e) => update("smtp_host", e.target.value)}
                />
              </Field>
              <Field label="Port">
                <input
                  className={inputClass}
                  style={inputStyle()}
                  value={settings.smtp_port}
                  onChange={(e) => update("smtp_port", e.target.value)}
                />
              </Field>
              <Field label="SMTP email">
                <input
                  className={inputClass}
                  style={inputStyle()}
                  value={settings.smtp_email}
                  onChange={(e) => update("smtp_email", e.target.value)}
                />
              </Field>
              <Field label="App password">
                <input
                  type="password"
                  className={inputClass}
                  style={inputStyle()}
                  value={settings.smtp_password}
                  onChange={(e) => update("smtp_password", e.target.value)}
                />
              </Field>
            </div>
            <Field label="From name">
              <input
                className={inputClass}
                style={inputStyle()}
                value={settings.smtp_from_name}
                onChange={(e) => update("smtp_from_name", e.target.value)}
              />
            </Field>
          </section>
        </>
      ) : null}

      <div className="mt-10">
        <Button variant="primary" onClick={save}>
          Save settings
        </Button>
      </div>
    </div>
  );
}
