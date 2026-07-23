# Changelog

## [2.0.2] — 2026-07-23

### UI

- Compact top bar: business name top-left, menu beside it (no tall centered hero)
- App fills the window height; Sale keeps chrome fixed and scrolls only the line items
- Tighter Products / History / Setup headers so pages fit without forced page scroll

### Docs

- Mac Gatekeeper workaround for unsigned beta (xattr / right-click Open)

## [2.0.1] — 2026-07-23

### Fix

- Packaged app failed to start on Windows/Mac with a WebAssembly magic-word error. The SQLite engine (`.wasm`) is now bundled as a Vite asset with relative URLs so Tauri loads the binary instead of `index.html`.

## [2.0.0] — 2026-07-23

### Rewrite

- New **Tauri + React** desktop app — one codebase for Windows and Mac
- Local SQLite via sql.js, persisted to app data (or IndexedDB in browser dev)
- Clean UI: island navigation, light default + dark mode, Geist / Manrope, Phosphor icons
- PDF receipts with system print dialog (thermal ESC/POS deferred)
- Setup wizard, product import, sales history, optional SMTP email
- Import tool for previous Python `invoices.db` files
- Previous Python / CustomTkinter app moved to `legacy/`

## [1.6.0] — 2026-07-15

See `legacy/CHANGELOG.md` for 1.x history.
