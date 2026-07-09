# Retail Invoice System

A classic POS-style retail invoicing desktop app built with Python and CustomTkinter. Features keyboard-driven data entry, inventory management, sales reports, and thermal receipt printing on Windows.

## Features

- **Retro POS terminal UI** — dark blue background, magenta headers, teal inputs, white monospace text
- **Keyboard shortcuts** for fast mouse-free operation
- **Enter to add manual line items** — tab through Description → Qty → Price, press Enter to submit
- **F7 payment cycling** — quickly switch Cash / Card / Other
- **Invoice creation** with inventory lookup and manual line items
- **Inventory management** with low-stock highlighting
- **Sales reports** with monthly/quarterly/yearly filters
- **Invoice reprints** from the Reports tab
- **Thermal receipt printing** via Windows shared printers (ESC/POS)

## Keyboard Shortcuts

### Global
| Key | Action |
|-----|--------|
| F1 | New Invoice tab |
| F2 | Inventory tab |
| F3 | Reports tab |
| F4 | Settings tab |

### New Invoice (F1)
| Key | Action |
|-----|--------|
| Alt+C | Focus customer name |
| Alt+P | Focus phone number |
| Alt+S | Focus inventory search |
| Alt+M | Focus manual item description |
| Alt+A | Add manual item |
| Enter | Add manual line (from Price field; tabs through fields) |
| F7 | Cycle payment method (Cash → Card → Other) |
| F12 | Print & save invoice |
| F11 | Save invoice only |
| F9 | Clear form |

### Inventory (F2)
| Key | Action |
|-----|--------|
| Alt+N | Add new product |
| Alt+S | Focus search |

### Reports (F3)
| Key | Action |
|-----|--------|
| Alt+P | Focus period dropdown |
| Alt+R | Refresh reports |

## Running from Source

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Download (Windows)

Go to **[Releases](https://github.com/theprincesajjad/retail-invoice/releases)** and download the latest `RetailInvoice-x.x.x-Windows.exe`. Double-click to run — no install or extra folders needed.

Current version: **1.0.1**

## Building Windows .exe locally

On a Windows PC, run:

```bat
build.bat
```

The single-file executable will be at `dist\RetailInvoice.exe`.

## Releasing a new version

1. Update `VERSION` (e.g. `1.1.0`)
2. Commit the change
3. Tag and push:

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions will build the `.exe` and publish a new release automatically.

## Requirements

- Python 3.12+
- Windows for receipt printing (uses `pywin32` / ESC/POS Win32Raw)
