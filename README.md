# Retail Invoice

A simple, beautiful retail invoicing app for Windows shops — ring up sales, print receipts, track inventory, and see today’s numbers.

Built so an 85-year-old can complete a sale, and a busy business owner can run the store without fuss.

---

## Download (easiest)

1. Open **[Releases](https://github.com/theprincesajjad/retail-invoice/releases)**
2. Download the latest **Windows.exe**
3. Double-click — no install, no Python, no setup required

That’s it. A welcome wizard may appear; you can fill it in or click **Skip for now** and start selling immediately.

Current release: **1.6.0** (1.7.0-beta: categories + inventory sync)

---

## First launch

| Step | What happens |
|------|----------------|
| Welcome wizard | Optional. Store name, address, phone, tax %. Skip anytime. |
| New Sale | Add products, take payment, press the green **Complete Sale & Print Receipt** button. |
| Setup (later) | Pick your receipt printer, logo, email — only when you need them. |

Nothing has to be completed before you can sell. Defaults work out of the box (13% tax, sample store details you can change anytime).

---

## Features

- **New Sale** — Customer info, product search, custom lines, discounts (% or $, before or after tax), Cash/Card/Other
- **Quantity picker** — Choose how many when adding from inventory; adjust with +/− on each line
- **Preview Receipt** — See the receipt before you print
- **Beautiful thermal receipts** — Clear layout for Epson TM-T20 and similar printers
- **Products** — Add/edit stock; categories; **Download inventory** / Import spreadsheet (new SKUs only); low-stock warnings
- **Reports** — Sales history (Today / week / month / quarter / year), reprint, email, **print inventory list**
- **Setup** — Store details, tax, discount timing, **product categories**, printer test, email receipts, backup
- **Keyboard shortcuts** — F1–F4 tabs, F5/F6 product save, F10 save, F11 preview, F12 complete + print, then F7/F8 pay and F12 confirm

---

## Batch import / keep inventory up to date

1. Open **Products** → **Download inventory** (Excel or CSV)
2. Existing items show **Status = In inventory**
3. Add new products on blank rows — always fill **SKU** (and name, category, qty, price)
4. Leave Status blank (or `New`) for new rows
5. **Import spreadsheet** — only new SKUs are added; existing rows are skipped

For Google Sheets: open the CSV, edit, File → Download → Excel/CSV, then Import.
---

## How to make a sale

1. Open the **New Sale** tab  
2. (Optional) Enter customer name / phone  
3. Search for a product → **Add to sale** → choose quantity  
4. Choose how they paid (Cash / Card / Other)  
5. Press **Complete Sale & Print Receipt**  
6. Confirm the total — done  

Use **Preview Receipt** anytime before saving. Use **Save Without Printing** if you don’t need a paper copy.

---

## Requirements

- **Windows 10 or 11** for the `.exe`
- Receipt printer optional (configure in **Setup** when ready)
- Email receipts optional (Gmail app password in **Setup**)

---

## Run from source (developers)

```bash
git clone https://github.com/theprincesajjad/retail-invoice.git
cd retail-invoice
pip install -r requirements.txt
python main.py
```

### Build the Windows `.exe` yourself

On a Windows machine:

```bat
build.bat
```

Or let GitHub Actions build it — push a version tag:

```bash
# Update VERSION and CHANGELOG.md, commit, then:
git tag v1.6.0
git push origin v1.6.0
```

That triggers [.github/workflows/release.yml](.github/workflows/release.yml), which builds `RetailInvoice-x.x.x-Windows.exe` and publishes a GitHub Release.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for what’s new in each version.

---

## License

Use freely for your shop. Contributions welcome via pull request.
