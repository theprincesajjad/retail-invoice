import { useState } from "react";
import { getAllSettings, saveSettings } from "../db/queries";
import { getDatabase, schedulePersist } from "../db/client";
import { Button, Field, inputClass, inputStyle } from "../components/ui";

export function SetupWizard({ onDone }: { onDone: () => void }) {
  const existing = getAllSettings(getDatabase());
  const [step, setStep] = useState(0);
  const [name, setName] = useState(existing.business_name === "My Business" ? "" : existing.business_name);
  const [address, setAddress] = useState(
    existing.business_address.startsWith("123 Main") ? "" : existing.business_address,
  );
  const [phone, setPhone] = useState(
    existing.business_phone.includes("555-0123") ? "" : existing.business_phone,
  );
  const [taxRate, setTaxRate] = useState(existing.tax_rate || "0.13");

  function finish(skip: boolean) {
    const db = getDatabase();
    if (!skip) {
      saveSettings(db, {
        business_name: name.trim() || "My Business",
        business_address: address.trim() || existing.business_address,
        business_phone: phone.trim() || existing.business_phone,
        tax_rate: taxRate.trim() || "0.13",
        setup_complete: "1",
      });
    } else {
      saveSettings(db, { setup_complete: "1" });
    }
    schedulePersist();
    onDone();
  }

  const steps = [
    {
      title: "Welcome to Retail Invoice",
      body: "Ring up sales and track inventory on this computer. Your data never leaves the machine unless you email a receipt.",
    },
    {
      title: "Your store",
      body: "Add a name customers will recognize on receipts. You can change this anytime in Setup.",
    },
    {
      title: "Tax rate",
      body: "Enter your local rate as a decimal. Example: 0.13 for 13%.",
    },
    {
      title: "You are ready",
      body: "Start with Sale. Add products when you have a moment. Setup can wait.",
    },
  ];

  const current = steps[step];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "var(--scrim)" }}>
      <div
        className="w-full max-w-lg rounded-xl border p-8 shadow-[var(--shadow)]"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <p className="text-xs font-medium tracking-[0.14em] text-[var(--text-tertiary)] uppercase">
          Step {step + 1} of {steps.length}
        </p>
        <h2 className="hero-text mt-3 text-3xl font-semibold tracking-tight text-wrap-balance">
          {current.title}
        </h2>
        <p className="mt-3 text-base text-[var(--text-secondary)] text-pretty">{current.body}</p>

        {step === 1 ? (
          <div className="mt-6 space-y-3">
            <Field label="Business name">
              <input
                className={inputClass}
                style={inputStyle()}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="River Street Goods"
              />
            </Field>
            <Field label="Address">
              <input
                className={inputClass}
                style={inputStyle()}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </Field>
            <Field label="Phone">
              <input
                className={inputClass}
                style={inputStyle()}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </Field>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="mt-6">
            <Field label="Tax rate">
              <input
                className={`${inputClass} tabular`}
                style={inputStyle()}
                value={taxRate}
                onChange={(e) => setTaxRate(e.target.value)}
              />
            </Field>
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap gap-2">
          {step < steps.length - 1 ? (
            <Button variant="primary" onClick={() => setStep((s) => s + 1)}>
              Continue
            </Button>
          ) : (
            <Button variant="primary" onClick={() => finish(false)}>
              Start selling
            </Button>
          )}
          <Button variant="ghost" onClick={() => finish(true)}>
            Skip for now
          </Button>
        </div>
      </div>
    </div>
  );
}
