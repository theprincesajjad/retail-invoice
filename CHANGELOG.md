# Changelog

All notable changes to Retail Invoice are documented here.

## [1.7.0-beta] — 2026-07-15

### Products & inventory spreadsheet

- Product **categories**: Cell Phones, Laptops, Desktops, Monitors, Printers, Accessories, Other
- Add more categories anytime in **Setup → Product categories**
- **Download inventory** replaces Download template — exports current stock with **Status = In inventory**
- Spreadsheet columns: SKU, Product Name, Details, Category, Qty, Price, Status
- **Import** only adds **new** rows that have a SKU filled in (skips In inventory / existing SKUs)

### Reports

- Renamed **Sales History → Reports**
- **Print inventory** — preview and print a categorized inventory list

---

## [1.6.0] — 2026-07-15

### Products

- **Batch import** from Excel (`.xlsx`) or CSV (Google Sheets → Download → Excel/CSV)
- **Download template** on the Products tab — headings: SKU, Product Name, Details, Qty, Price
- Matching SKUs update existing products; new SKUs are added
- Add Product **Save Next** and **Save Close** buttons are the same size and style (F5 / F6)

### New Sale

- **Discount before or after tax** — choose per sale; default lives in Setup
- Totals / Notes / Discount rail is **scrollable** so it stays usable at 125% display scaling
- After **F12 Complete + Print**: **F7 Cash**, **F8 Card** (payment window), then **F12** to confirm

### Receipts

- One blank line between items on the printed invoice

---

## [1.5.0] — 2026-07-14

### UI polish

- Header: removed top-right nav menu; restored standard tab strip under the title bar
- Add Product: SKU + Price + Qty on one compact top row; Name and Details full width below
- Receipts: Item and Details wrap only inside the Item column (no spill into Qty/Price/Total)

### Stable cut

Promotes the 1.4.x beta line (wireframe New Sale, receipt design Setup, Details field, toast/print fixes) to a full release.

---

## [1.4.4-beta] — 2026-07-13

### Wireframe UI

- New Sale rebuilt to match desk wireframe: compact Name/Phone/Email, SKU + Custom rows, dominant items list, totals/notes/discount rail, COMPLETE / PREVIEW / SAVE / NEW dock
- Header shows store logo + business name with tabs inline
- Add Product dialog: SKU|Price, Name, Details, Save Next (F5) / Save Close (F6), Qty
- Hotkeys: F1 New, F10 Save, F11 Preview, F12 Complete + Print

---

## [1.4.3-beta] — 2026-07-13

### Receipt design

- Fixed broken thermal layout caused by double-height body text (wrapped dates, garbled columns)
- Customer / phone print inline; compact date format
- Setup tab: live receipt preview + show/hide toggles, title size, header spacing

### New Sale UI

- Compact Name | Phone row (removed Customer section title)
- Items list more visible without scrolling
- Tabs moved inline with the Retail Invoice title
- Details field shown when selecting a product by SKU/search

---

## [1.4.2-beta] — 2026-07-11

### Fixes

- Fixed post-save / post-print crash caused by toast `place(width=…)` (CustomTkinter requires width on the widget constructor/configure).

### New Sale / Products

- Renamed Serial / S/N to **Details** on products, sale lines, and receipts
- Inventory add skips quantity popup (adds qty 1; adjust with − / +)
- Sale notes print on the invoice when present
- Cash / Card payment prompt before complete & print
- Visible Alt / F-key shortcut legend on New Sale
- Product dialog buttons: **Save & Close** and **Save & Next**

### Receipt layout

- Larger thermal logo (512 dots)
- Larger double-height body text and roomier line spacing
- Blank lines between store contact fields
- Invoice numbers use `INV-786-xxxx`

---

## [1.4.1-beta] — 2026-07-10

### Design polish

Applied Emil Kowalski design-engineering and Apple interface craft to the desktop UI:

- Non-blocking toast notifications for everyday feedback (add item, save, print, backup)
- Confirmations reserved for meaningful actions, with specific button labels
- Destructive delete confirmation styled clearly
- Calmer color hierarchy and raised primary panels
- Beta version badge in the header

### Unchanged

- Skippable welcome wizard
- Large accessible controls from 1.4.0
- Beautiful receipt layout

---

## [1.4.0] — 2026-07-10

### Designed for everyone

Retail Invoice is now simple enough for anyone to use — large text, plain language, and a big green button to complete a sale. Power users still get keyboard shortcuts.

### Highlights

- **Welcome wizard (fully optional)** — On first launch, a short guided setup appears. Fill in what you know, or click **Skip for now** and start selling immediately. Nothing is required.
- **Larger, clearer UI** — Bigger fonts, taller buttons, higher contrast, and plain-language labels throughout.
- **Friendlier New Sale tab** — Quantity picker when adding products, +/− controls on line items, **Preview Receipt**, and a confirmation before completing a sale.
- **Beautiful receipts** — Cleaner layout with clear sections, a prominent TOTAL, and a warm thank-you message.
- **Sales History** — One-click **Today** filter, plus This week / Monthly / Quarterly / Yearly. Colorful summary cards for money collected, tax, sale count, and average.
- **Products** — Low-stock warning banner; clearer labels and larger action buttons.
- **Setup** — Tax rate as a percentage (e.g. 13), test print button, and **Save backup to file**.

### Tab names

| Before | After |
|--------|-------|
| Invoice | New Sale |
| Stock | Products |
| Reports | Sales History |
| Settings | Setup |

### Download

Download `RetailInvoice-1.4.0-Windows.exe` from [Releases](https://github.com/theprincesajjad/retail-invoice/releases) — no install, no Python required. Double-click and go.

---

## [1.3.0] — 2026-07-10

- Light “liquid glass” UI redesign
- Improved thermal receipt layout
- Printer picker and logo fixes
- Maximize on launch

## Earlier releases

See [GitHub Releases](https://github.com/theprincesajjad/retail-invoice/releases) for v1.0.x–v1.2.x notes.
