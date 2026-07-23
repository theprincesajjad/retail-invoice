# Retail Invoice

Local-first invoicing and inventory for small businesses. One app for **Windows and Mac**. Your data stays on this computer — nothing is uploaded to the cloud.

Built so anyone can complete a sale quickly, with a clean interface and optional keyboard shortcuts for power users.

---

## Download

1. Open **[Releases](https://github.com/theprincesajjad/retail-invoice/releases)**
2. Download the installer for your system (Windows `.msi` / `.exe` or macOS `.dmg`)
3. Open the app — no account, no internet required

Current version: **2.0.0**

---

## Privacy

- Sales, products, and settings live in a **local SQLite database** on your machine
- Optional email receipts only leave the computer when you press Email
- Backup and restore are plain files you control

---

## Features

- **Sale** — customer info, product search, custom lines, discounts, Cash / Card / Other
- **Products** — add and edit stock; import CSV or Excel; low-stock hints
- **History** — filter by period, reprint PDF, email receipts
- **Setup** — store details, tax rate, light / dark / system appearance, receipt toggles, SMTP, backup, import from the older Python app database
- **Shortcuts** — F1–F4 tabs, F10 save PDF, F11 preview, F12 complete + print

---

## Run from source

```bash
git clone https://github.com/theprincesajjad/retail-invoice.git
cd retail-invoice
npm install
npm run dev          # web UI (local DB in the browser)
npm run tauri:dev    # desktop shell (needs Rust + platform deps)
```

### Build desktop installers

```bash
npm run tauri:build
```

Artifacts appear under `src-tauri/target/release/bundle/`.

---

## Migrating from the Python app (v1)

1. Open **Setup → Import previous Retail Invoice database**
2. Choose your old `data/invoices.db`
3. Products, settings, and past invoices are copied in

The previous CustomTkinter app is preserved under [`legacy/`](legacy/) for reference.

---

## Develop

```bash
npm test             # unit tests
npm run build        # production web build
```

Design tokens follow [`.agents/skills/redesign-existing-projects/SKILL.md`](.agents/skills/redesign-existing-projects/SKILL.md) (Geist / Manrope, light default, skill dark palette).

---

## License

Use freely for your shop. Contributions welcome via pull request.
