# Retail Invoice System

A DOS-style retail invoicing desktop app built with Python and CustomTkinter. Features keyboard-driven data entry, inventory management, sales reports, and thermal receipt printing on Windows.

## Features

- **DOS green-on-black UI** with sharp corners for a retro terminal feel
- **Keyboard shortcuts** for fast mouse-free operation
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

## Building Windows .exe

On a Windows PC, run:

```bat
build.bat
```

The executable will be in `dist\RetailInvoice\RetailInvoice.exe`.

Or download the latest build from GitHub Actions artifacts (Actions → Build Windows EXE → Artifacts).

## Requirements

- Python 3.12+
- Windows for receipt printing (uses `pywin32` / ESC/POS Win32Raw)
