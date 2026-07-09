# Retail Invoice System

A clean, keyboard-friendly retail invoicing app for Windows — inventory, invoicing with discounts, searchable reports, and thermal receipt printing.

## Features

- Refined light UI with calm spacing and system-native typography
- Invoice workflow with customer-first focus, line items, and **% or $ discounts**
- Inventory entry: SKU → Description → S/N → Price → Qty with **Ctrl+S** save and auto-next
- Reports search by **customer name, phone, or product**
- Single-file Windows `.exe` via GitHub Releases

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| F1–F4 | Switch tabs |
| Alt+C | Focus customer name |
| Alt+P | Focus phone / period |
| Alt+S | Focus search |
| Alt+M | Focus manual description |
| Alt+D | Focus discount |
| Alt+N | New product (Inventory) |
| F7 | Cycle payment method |
| Enter | Tab through manual line fields, submit on Price |
| Ctrl+S | Save product (Inventory dialog) |
| F11 / F12 | Save / Print & save invoice |

## Download

**[Releases](https://github.com/theprincesajjad/retail-invoice/releases)** — download `RetailInvoice-x.x.x-Windows.exe` and run.

Current version: **1.1.0**

## New release

```bash
# Update VERSION, commit, then:
git tag v1.1.0
git push origin v1.1.0
```
