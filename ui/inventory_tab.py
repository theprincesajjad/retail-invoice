import customtkinter as ctk
from tkinter import messagebox
from database import add_product, update_product, delete_product, search_products
from models import Product
from utils import format_currency
from . import theme as T
from .dialogs import ask_yes_no


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

        T.field_label(inner, "Search products").pack(side="left", padx=(24, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner, textvariable=self.search_var,
            placeholder_text="Name, code, or serial number…", **T.entry_kwargs(300),
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_products())

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

        self.headers = ["Code", "Product name", "Serial #", "In stock", "Price", ""]
        self.widths = [100, 260, 140, 80, 100, 160]

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
                (p.serial_number or "—", self.widths[2]),
                (qty_text, self.widths[3]),
                (format_currency(p.price), self.widths[4]),
            ]:
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=color).pack(side="left", padx=6, pady=10)

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[5])
            actions.pack(side="left", padx=6)
            ctk.CTkButton(actions, text="Edit", width=70, command=lambda prod=p: self.show_product_dialog(prod), **T.button_kwargs(height=T.BTN_HEIGHT_SM)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Delete", width=76, command=lambda prod=p: self.delete_product(prod), **T.button_kwargs(height=T.BTN_HEIGHT_SM, text_color=T.DANGER)).pack(side="left", padx=3)

    def delete_product(self, product: Product):
        if ask_yes_no(self.winfo_toplevel(), "Delete product?", f"Remove '{product.name}' from your inventory?\n\nThis cannot be undone."):
            delete_product(product.id)
            self.load_products()
            self.winfo_toplevel().set_status(f"Deleted {product.name}")

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

        width, height = 500, 580
        dialog.configure(fg_color=T.BG)
        dialog.resizable(False, False)
        dialog.geometry(f"{width}x{height}")
        dialog.minsize(width, height)
        dialog.maxsize(width, height)
        dialog.transient(parent)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        def close_dialog():
            dialog.destroy()

        dialog.bind("<Destroy>", lambda e: setattr(self, "_product_dialog", None))

        card = ctk.CTkFrame(dialog, **T.card_kwargs())
        card.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 6))
        ctk.CTkLabel(
            header,
            text="Add a new product" if is_new else "Edit product",
            font=T.FONT_HEADLINE,
            text_color=T.TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Fill in the details below, then press Save",
            font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(6, 0))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(10, 8))
        body.grid_columnconfigure(0, weight=1)

        entries = {}
        field_defs = [
            ("Product code (SKU)", "sku", "e.g. 60000"),
            ("Product name", "name", "What is this product called?"),
            ("Serial number (optional)", "serial_number", "Leave blank if not applicable"),
            ("Price ($)", "price", "0.00"),
            ("How many in stock", "qty", "1"),
        ]

        ordered_entries = []
        for row, (label, key, placeholder) in enumerate(field_defs):
            T.field_label(body, label).grid(row=row * 2, column=0, sticky="w", pady=(0, 4))
            entry = ctk.CTkEntry(body, placeholder_text=placeholder, **T.entry_kwargs(width=360))
            entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 12))
            entries[key] = entry
            ordered_entries.append(entry)

        if product:
            entries["sku"].insert(0, product.sku or "")
            entries["name"].insert(0, product.name)
            entries["serial_number"].insert(0, product.serial_number or "")
            entries["price"].insert(0, str(product.price))
            entries["qty"].insert(0, str(product.qty))
        else:
            entries["qty"].insert(0, "1")
            entries["price"].insert(0, "0.00")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(4, 22))

        def save(add_another=False):
            try:
                name = entries["name"].get().strip()
                if not name:
                    raise ValueError("Product name is required")
                price = float(entries["price"].get().strip() or "0")
                qty = int(entries["qty"].get().strip() or "0")
                if qty < 0:
                    raise ValueError("Stock quantity cannot be negative")

                new_product = Product(
                    id=product.id if product else None,
                    name=name,
                    serial_number=entries["serial_number"].get().strip(),
                    sku=entries["sku"].get().strip(),
                    price=price,
                    qty=qty,
                    category="",
                    created_at="",
                )

                if product:
                    update_product(new_product)
                    parent.set_status(f"Updated {name}")
                    close_dialog()
                else:
                    add_product(new_product)
                    parent.set_status(f"Added {name}")
                    close_dialog()
                    if add_another:
                        self.after(120, self.show_product_dialog)

                self.load_products()
            except ValueError as e:
                messagebox.showerror("Please check your entries", str(e), parent=dialog)

        def focus_next(index: int):
            ordered_entries[(index + 1) % len(ordered_entries)].focus_set()

        def focus_prev(index: int):
            ordered_entries[(index - 1) % len(ordered_entries)].focus_set()

        for i, entry in enumerate(ordered_entries):
            if i < len(ordered_entries) - 1:
                entry.bind("<Return>", lambda e, idx=i: (focus_next(idx), "break")[1])
                entry.bind("<KP_Enter>", lambda e, idx=i: (focus_next(idx), "break")[1])
            else:
                entry.bind("<Return>", lambda e: (save(add_another=is_new), "break")[1])
                entry.bind("<KP_Enter>", lambda e: (save(add_another=is_new), "break")[1])
            entry.bind("<Tab>", lambda e, idx=i: (focus_next(idx), "break")[1])
            entry.bind("<Shift-Tab>", lambda e, idx=i: (focus_prev(idx), "break")[1])

        ctk.CTkButton(footer, text="Cancel", command=close_dialog, **T.button_kwargs(width=110)).pack(side="left")
        if is_new:
            ctk.CTkButton(
                footer,
                text="Save & add another",
                command=lambda: save(add_another=True),
                **T.button_kwargs(width=160),
            ).pack(side="right", padx=(10, 0))
        ctk.CTkButton(
            footer,
            text="Save product",
            command=lambda: save(add_another=False),
            **T.success_button_kwargs(width=140),
        ).pack(side="right")

        def on_ctrl_s(event=None):
            save(add_another=False)
            return "break"

        dialog.bind("<Control-s>", on_ctrl_s)
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
        entries["sku"].focus_set()
