import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from product_import import (
    TEMPLATE_HEADERS,
    ensure_templates,
    import_products_from_file,
    write_csv_template,
    write_excel_template,
    write_products_csv,
    today_date_stamp,
)
from inventory_excel_sync import (
    default_inventory_excel_path,
    resolve_inventory_excel_path,
    sync_inventory_excel as run_inventory_excel_sync,
)
from utils import format_currency
from database import (
    add_product,
    update_product,
    delete_product,
    search_products,
    list_all_products,
    reapply_sku_prefix_categories,
    get_setting,
    save_setting,
)
from models import Product
from product_categories import PRODUCT_CATEGORIES, category_for_sku
from . import theme as T
from .dialogs import ask_yes_no
from .toast import toast


class InventoryTab(ctk.CTkFrame):
    LOW_STOCK_THRESHOLD = 3

    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self._product_dialog = None
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_top_bar()
        self.create_low_stock_banner()
        self.create_table()
        self.load_products()

    def create_top_bar(self):
        bar = ctk.CTkFrame(self, **T.card_kwargs())
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=14)

        ctk.CTkButton(
            inner,
            text="+ Add new product",
            command=self.show_product_dialog,
            **T.primary_button_kwargs(width=180),
        ).pack(side="left")

        ctk.CTkButton(
            inner,
            text="Export CSV",
            command=self.export_products_csv,
            **T.button_kwargs(width=120),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Import CSV",
            command=self.import_products,
            **T.button_kwargs(width=120),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Sync Excel",
            command=self.sync_inventory_excel,
            **T.primary_button_kwargs(width=120),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Choose Excel…",
            command=self.choose_inventory_excel,
            **T.button_kwargs(width=130),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Download template",
            command=self.download_import_template,
            **T.button_kwargs(width=150),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Export checklist PDF",
            command=self.export_checklist_pdf,
            **T.button_kwargs(width=170),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            inner,
            text="Apply SKU categories",
            command=self.apply_sku_categories,
            **T.button_kwargs(width=160),
        ).pack(side="left", padx=(10, 0))

        T.field_label(inner, "Search products").pack(side="left", padx=(24, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner, textvariable=self.search_var,
            placeholder_text="Name, code, category, or details…", **T.entry_kwargs(280),
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_products())

    def export_products_csv(self):
        """Export full inventory to CSV (SKU, name, details, qty, price, category, date stamp)."""
        products = list_all_products()
        stamp = today_date_stamp()
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export inventory CSV",
            defaultextension=".csv",
            initialfile=f"inventory-export-{stamp}.csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            dest = Path(path)
            if dest.suffix.lower() != ".csv":
                dest = dest.with_suffix(".csv")
            write_products_csv(dest, products)
            toast(self, f"Exported {len(products)} products", kind="success")
            self.winfo_toplevel().set_status(f"CSV exported to {dest.name}")
        except Exception as e:
            messagebox.showerror("Could not export CSV", str(e), parent=self.winfo_toplevel())

    def download_import_template(self):
        """Let the user save the Excel (or CSV) template with headings filled in."""
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save product import template",
            defaultextension=".xlsx",
            initialfile="product_import_template.xlsx",
            filetypes=[
                ("Excel spreadsheet", "*.xlsx"),
                ("CSV (Google Sheets)", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            dest = Path(path)
            if dest.suffix.lower() == ".csv":
                write_csv_template(dest)
            else:
                if dest.suffix.lower() != ".xlsx":
                    dest = dest.with_suffix(".xlsx")
                write_excel_template(dest)
            # Keep a copy in assets for packaging / docs
            ensure_templates()
            toast(self, f"Template saved — columns: {', '.join(TEMPLATE_HEADERS)}", kind="success")
            self.winfo_toplevel().set_status(f"Template saved to {dest.name}")
        except Exception as e:
            messagebox.showerror("Could not save template", str(e), parent=self.winfo_toplevel())

    def export_checklist_pdf(self):
        """Export a printable PDF of in-stock products only, sorted by category."""
        from datetime import datetime
        from inventory_pdf import build_inventory_checklist_pdf, in_stock_products

        in_stock = in_stock_products()
        if not in_stock:
            messagebox.showinfo(
                "Nothing to export",
                "There are no in-stock products (qty greater than 0).",
                parent=self.winfo_toplevel(),
            )
            return

        stamp = datetime.now().strftime("%Y-%m-%d")
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save inventory checklist PDF",
            defaultextension=".pdf",
            initialfile=f"inventory-checklist-{stamp}.pdf",
            filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            dest = Path(path)
            if dest.suffix.lower() != ".pdf":
                dest = dest.with_suffix(".pdf")
            pdf_bytes = build_inventory_checklist_pdf(in_stock)
            dest.write_bytes(pdf_bytes)
            toast(
                self,
                f"Checklist saved · {len(in_stock)} in-stock products",
                kind="success",
            )
            self.winfo_toplevel().set_status(f"Checklist PDF saved to {dest.name}")
        except Exception as e:
            messagebox.showerror(
                "Could not export checklist",
                str(e),
                parent=self.winfo_toplevel(),
            )

    def apply_sku_categories(self):
        """Batch: SKU 92* → Laptops, SKU 110* → Cell Phones."""
        n = reapply_sku_prefix_categories()
        self.load_products()
        toast(
            self,
            f"Updated categories · 92→Laptops, 110→Cell Phones ({n} rows)",
            kind="success",
        )
        self.winfo_toplevel().set_status("SKU category rules applied")

    def choose_inventory_excel(self):
        """Pick or create the local inventory Excel workbook used for Sync."""
        current = ""
        try:
            current = str(resolve_inventory_excel_path())
        except Exception:
            current = str(default_inventory_excel_path())
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Choose inventory Excel file",
            defaultextension=".xlsx",
            initialfile=Path(current).name if current else "inventory.xlsx",
            initialdir=str(Path(current).parent) if current else None,
            filetypes=[("Excel spreadsheet", "*.xlsx"), ("All files", "*.*")],
        )
        if not path:
            return
        dest = Path(path)
        if dest.suffix.lower() != ".xlsx":
            dest = dest.with_suffix(".xlsx")
        save_setting("inventory_excel_path", str(dest))
        try:
            result = run_inventory_excel_sync(dest)
            self.load_products()
            msg = f"Using {dest.name} · {result.exported} products written"
            if result.added or result.updated:
                msg += f" · pulled {result.added} new, {result.updated} updated"
            toast(self, msg, kind="success", title="Inventory Excel")
            self.winfo_toplevel().set_status(f"Inventory Excel: {dest}")
        except Exception as e:
            messagebox.showerror("Could not set Excel file", str(e), parent=self.winfo_toplevel())

    def sync_inventory_excel(self):
        """
        Sync the local inventory Excel:
          - Pull new/edited products from the spreadsheet into the app
          - Rewrite the spreadsheet with current Status / qty / date sold
        """
        path = resolve_inventory_excel_path()
        if not path.exists():
            # First-time: offer to create at default or chosen path
            create = ask_yes_no(
                self.winfo_toplevel(),
                "Create inventory Excel?",
                (
                    f"No inventory Excel found yet.\n\n"
                    f"Create one at:\n{path}\n\n"
                    "You can change the location with Choose Excel…"
                ),
                confirm_label="Create & sync",
                cancel_label="Cancel",
            )
            if not create:
                return
        try:
            result = run_inventory_excel_sync(path)
            self.load_products()
            parts = [f"{result.exported} in Excel"]
            if result.created_file:
                parts.insert(0, "file created")
            if result.added:
                parts.append(f"{result.added} added from Excel")
            if result.updated:
                parts.append(f"{result.updated} updated from Excel")
            summary = " · ".join(parts)
            toast(self, summary, kind="success", title="Excel synced")
            self.winfo_toplevel().set_status(f"Synced {result.path.name} — {summary}")
            if result.errors:
                messagebox.showwarning(
                    "Some Excel rows had problems",
                    "\n".join(result.errors[:12]),
                    parent=self.winfo_toplevel(),
                )
        except PermissionError:
            messagebox.showerror(
                "Excel file is open",
                (
                    f"Could not write:\n{path}\n\n"
                    "Close the spreadsheet in Excel, then Sync again."
                ),
                parent=self.winfo_toplevel(),
            )
        except Exception as e:
            messagebox.showerror("Sync failed", str(e), parent=self.winfo_toplevel())

    def import_products(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import products from CSV / Excel",
            filetypes=[
                ("Spreadsheets", "*.csv *.xlsx *.xlsm"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xlsm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        result = import_products_from_file(path)
        self.load_products()
        if result.errors and not result.ok_count and not result.skipped_dated:
            messagebox.showerror(
                "Import failed",
                "\n".join(result.errors[:8]),
                parent=self.winfo_toplevel(),
            )
            return

        parts = []
        if result.added:
            parts.append(f"{result.added} added")
        if result.updated:
            parts.append(f"{result.updated} updated")
        if result.skipped_dated:
            parts.append(f"{result.skipped_dated} skipped (already dated)")
        elif result.skipped:
            parts.append(f"{result.skipped} skipped")
        summary = ", ".join(parts) if parts else "Nothing imported"
        if result.ok_count:
            summary += f" · stamped {today_date_stamp()}"
        toast(self, summary, kind="success" if result.ok_count else "warning", title="Import complete")
        self.winfo_toplevel().set_status(f"Import complete — {summary}")
        if result.errors:
            messagebox.showwarning(
                "Some rows had problems",
                "\n".join(result.errors[:12]),
                parent=self.winfo_toplevel(),
            )

    def create_low_stock_banner(self):
        self.banner_frame = ctk.CTkFrame(self, fg_color=T.WARNING_SOFT, corner_radius=T.RADIUS_MD)
        self.banner_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        self.banner_label = ctk.CTkLabel(
            self.banner_frame, text="", font=T.FONT, text_color=T.WARNING, anchor="w",
        )
        self.banner_label.pack(fill="x", padx=T.PAD_CARD, pady=12)
        self.banner_frame.grid_remove()

    def create_table(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkScrollableFrame(card, fg_color=T.SURFACE, corner_radius=0)
        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        self.headers = ["Code", "Product name", "Category", "Details", "In stock", "Price", "Date", ""]
        self.widths = [80, 200, 100, 110, 70, 80, 90, 140]

        header_frame = ctk.CTkFrame(self.table_frame, fg_color=T.SURFACE_ALT, corner_radius=0)
        header_frame.pack(fill="x", padx=12, pady=(12, 4))
        for text, width in zip(self.headers, self.widths):
            ctk.CTkLabel(header_frame, text=text, width=width, **T.table_header_kwargs()).pack(side="left", padx=6, pady=8)

        self.rows_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def load_products(self):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        products = search_products(self.search_var.get().strip())

        low_stock = [p for p in products if 0 < p.qty <= self.LOW_STOCK_THRESHOLD]
        if low_stock:
            names = ", ".join(p.name for p in low_stock[:3])
            extra = f" and {len(low_stock) - 3} more" if len(low_stock) > 3 else ""
            self.banner_label.configure(text=f"Low stock warning: {names}{extra}")
            self.banner_frame.grid()
        else:
            self.banner_frame.grid_remove()

        if not products:
            ctk.CTkLabel(
                self.rows_frame,
                text="No products yet — click \"Add new product\" to get started",
                font=T.FONT, text_color=T.TEXT_TERTIARY,
            ).pack(pady=40)
            return

        for i, p in enumerate(products):
            row = ctk.CTkFrame(self.rows_frame, fg_color=T.SURFACE_ALT if i % 2 == 0 else "transparent", corner_radius=T.RADIUS_SM)
            row.pack(fill="x", pady=2)

            is_low = 0 < p.qty <= self.LOW_STOCK_THRESHOLD
            is_out = p.qty <= 0
            color = T.DANGER if is_out else (T.WARNING if is_low else T.TEXT)

            qty_text = str(p.qty)
            if is_out:
                qty_text = "Out of stock"
            elif is_low:
                qty_text = f"{p.qty} (low)"

            for text, width in [
                (p.sku or "—", self.widths[0]),
                (p.name, self.widths[1]),
                (p.category or "—", self.widths[2]),
                (p.serial_number or "—", self.widths[3]),
                (qty_text, self.widths[4]),
                (format_currency(p.price), self.widths[5]),
                (getattr(p, "import_date", "") or "—", self.widths[6]),
            ]:
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=color).pack(side="left", padx=6, pady=10)

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[7])
            actions.pack(side="left", padx=6)
            ctk.CTkButton(actions, text="Edit", width=70, command=lambda prod=p: self.show_product_dialog(prod), **T.button_kwargs(height=T.BTN_HEIGHT_SM)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Delete", width=76, command=lambda prod=p: self.delete_product(prod), **T.button_kwargs(height=T.BTN_HEIGHT_SM, text_color=T.DANGER)).pack(side="left", padx=3)

    def delete_product(self, product: Product):
        if ask_yes_no(
            self.winfo_toplevel(),
            "Delete product?",
            f"Remove '{product.name}' from your inventory?\n\nThis cannot be undone.",
            confirm_label="Delete product",
            cancel_label="Keep it",
            destructive=True,
        ):
            delete_product(product.id)
            self.load_products()
            try:
                from inventory_excel_sync import try_auto_export_inventory_excel
                try_auto_export_inventory_excel()
            except Exception:
                pass
            self.winfo_toplevel().set_status(f"Deleted {product.name}")
            toast(self, f"Removed {product.name}", kind="info")

    def show_product_dialog(self, product: Product = None):
        if self._product_dialog is not None:
            try:
                if self._product_dialog.winfo_exists():
                    self._product_dialog.lift()
                    self._product_dialog.focus_force()
                    return
            except Exception:
                self._product_dialog = None

        is_new = product is None
        parent = self.winfo_toplevel()

        dialog = ctk.CTkToplevel(parent)
        self._product_dialog = dialog
        dialog.title("Add product" if is_new else "Edit product")

        width, height = 520, 520
        dialog.configure(fg_color=T.BG)
        dialog.resizable(False, True)
        dialog.geometry(f"{width}x{height}")
        dialog.minsize(width, 420)
        dialog.transient(parent)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        def close_dialog():
            dialog.destroy()

        dialog.bind("<Destroy>", lambda e: setattr(self, "_product_dialog", None) if e.widget == dialog else None)

        card = ctk.CTkFrame(dialog, **T.card_kwargs())
        card.pack(fill="both", expand=True, padx=18, pady=18)
        # Use grid inside the card so the scroll area grows and buttons stay pinned
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        # Scrollable fields — footer buttons stay pinned below so they never hide
        body = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=0)
        body.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=0)

        # Top row: PRODUCT SKU | PRICE | QTY (same as 1.6.0)
        ctk.CTkLabel(body, text="PRODUCT SKU", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=0, sticky="w", padx=(8, 10)
        )
        ctk.CTkLabel(body, text="PRICE", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=1, sticky="w", padx=(0, 10)
        )
        ctk.CTkLabel(body, text="QTY", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        sku_entry = ctk.CTkEntry(body, placeholder_text="e.g. 60000", **T.entry_kwargs(width=120))
        sku_entry.grid(row=1, column=0, sticky="w", padx=(8, 10), pady=(4, 14))
        price_entry = ctk.CTkEntry(body, placeholder_text="0.00", **T.entry_kwargs(width=90))
        price_entry.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(4, 14))
        qty_entry = ctk.CTkEntry(body, placeholder_text="1", **T.entry_kwargs(width=70))
        qty_entry.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=(4, 14))

        # Category only — added on top of the 1.6.0 dialog
        ctk.CTkLabel(body, text="CATEGORY", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=8
        )
        category_var = ctk.StringVar(value="Select category")
        category_menu = ctk.CTkOptionMenu(
            body,
            variable=category_var,
            values=["Select category", *PRODUCT_CATEGORIES],
            width=280,
            height=T.BTN_HEIGHT,
            font=T.FONT,
            fg_color=T.SURFACE_GLASS if hasattr(T, "SURFACE_GLASS") else T.SURFACE,
            button_color=T.BORDER,
            button_hover_color=T.TEXT_TERTIARY,
            dropdown_fg_color=T.SURFACE,
            dropdown_hover_color=T.ACCENT_SOFT if hasattr(T, "ACCENT_SOFT") else T.SURFACE_ALT,
            dropdown_text_color=T.TEXT,
            text_color=T.TEXT,
        )
        category_menu.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 14))

        # Full-width name + details (same as 1.6.0)
        ctk.CTkLabel(body, text="PRODUCT NAME", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=4, column=0, columnspan=3, sticky="w", padx=8
        )
        name_entry = ctk.CTkEntry(body, placeholder_text="What is this product called?", **T.entry_kwargs())
        name_entry.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 14))

        ctk.CTkLabel(body, text="DETAILS", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=6, column=0, columnspan=3, sticky="w", padx=8
        )
        details_entry = ctk.CTkEntry(
            body, placeholder_text="Specs, S/N, or other text for the invoice", **T.entry_kwargs(),
        )
        details_entry.grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 16))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 18))

        def sync_category_from_sku(_event=None):
            suggested = category_for_sku(sku_entry.get())
            if suggested and category_var.get() in ("", "Select category"):
                category_var.set(suggested)

        sku_entry.bind("<FocusOut>", sync_category_from_sku)

        if product:
            sku_entry.insert(0, product.sku or "")
            name_entry.insert(0, product.name)
            details_entry.insert(0, product.serial_number or "")
            price_entry.insert(0, str(product.price))
            qty_entry.insert(0, str(product.qty))
            if product.category:
                if product.category not in PRODUCT_CATEGORIES:
                    category_menu.configure(values=["Select category", product.category, *PRODUCT_CATEGORIES])
                category_var.set(product.category)
            else:
                category_var.set(category_for_sku(product.sku or "") or "Select category")
        else:
            qty_entry.insert(0, "1")
            price_entry.insert(0, "0.00")
            category_var.set("Select category")

        def save(add_another=False):
            try:
                name = name_entry.get().strip()
                if not name:
                    raise ValueError("Product name is required")
                price = float(price_entry.get().strip() or "0")
                qty = int(qty_entry.get().strip() or "0")
                if qty < 0:
                    raise ValueError("Stock quantity cannot be negative")
                sku = sku_entry.get().strip()
                category = category_var.get().strip()
                if category == "Select category":
                    category = ""
                if not category:
                    category = category_for_sku(sku)

                new_product = Product(
                    id=product.id if product else None,
                    name=name,
                    serial_number=details_entry.get().strip(),
                    sku=sku,
                    price=price,
                    qty=qty,
                    category=category,
                    created_at="",
                    import_date=(
                        (getattr(product, "import_date", "") or "")
                        if product
                        else today_date_stamp()
                    ),
                    sold_date=(getattr(product, "sold_date", "") or "") if product else "",
                )
                if qty > 0:
                    new_product.sold_date = ""
                elif not new_product.sold_date:
                    new_product.sold_date = today_date_stamp()

                if product:
                    update_product(new_product)
                    parent.set_status(f"Updated {name}")
                    toast(self, f"Updated {name}", kind="success")
                    close_dialog()
                else:
                    add_product(new_product)
                    parent.set_status(f"Added {name}")
                    toast(self, f"Added {name}", kind="success")
                    close_dialog()
                    if add_another:
                        self.after(120, self.show_product_dialog)

                self.load_products()
                try:
                    from inventory_excel_sync import try_auto_export_inventory_excel
                    try_auto_export_inventory_excel()
                except Exception:
                    pass
            except ValueError as e:
                messagebox.showerror("Please check your entries", str(e), parent=dialog)

        ordered = [sku_entry, price_entry, qty_entry, name_entry, details_entry]

        def focus_next(index: int):
            ordered[(index + 1) % len(ordered)].focus_set()

        def focus_prev(index: int):
            ordered[(index - 1) % len(ordered)].focus_set()

        for i, entry in enumerate(ordered):
            if i < len(ordered) - 1:
                entry.bind("<Return>", lambda e, idx=i: (focus_next(idx), "break")[1])
                entry.bind("<KP_Enter>", lambda e, idx=i: (focus_next(idx), "break")[1])
            else:
                entry.bind("<Return>", lambda e: (save(add_another=is_new), "break")[1])
                entry.bind("<KP_Enter>", lambda e: (save(add_another=is_new), "break")[1])
            entry.bind("<Tab>", lambda e, idx=i: (focus_next(idx), "break")[1])
            entry.bind("<Shift-Tab>", lambda e, idx=i: (focus_prev(idx), "break")[1])

        actions = ctk.CTkFrame(footer, fg_color="transparent")
        actions.pack(side="left")
        btn_style = T.success_button_kwargs(width=170, height=T.BTN_HEIGHT_LG)
        if is_new:
            ctk.CTkButton(
                actions, text="SAVE NEXT  ·  F5", command=lambda: save(add_another=True),
                **btn_style,
            ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            actions, text="SAVE CLOSE  ·  F6", command=lambda: save(add_another=False),
            **btn_style,
        ).pack(side="left")

        dialog.bind("<F5>", lambda e: (save(add_another=True), "break")[1] if is_new else "break")
        dialog.bind("<F6>", lambda e: (save(add_another=False), "break")[1])
        dialog.bind("<Control-s>", lambda e: (save(add_another=False), "break")[1])
        dialog.bind("<Escape>", lambda e: (close_dialog(), "break")[1])

        parent.update_idletasks()
        px = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{px}+{py}")

        dialog.update_idletasks()
        dialog.deiconify()
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.after(50, lambda: dialog.attributes("-topmost", False))
        dialog.grab_set()
        dialog.focus_force()
        sku_entry.focus_set()
