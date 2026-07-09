import customtkinter as ctk
from tkinter import messagebox
from database import add_product, update_product, delete_product, search_products
from models import Product
from utils import format_currency
from . import theme as T


class InventoryTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_top_bar()
        self.create_table()
        self.load_products()

    def create_top_bar(self):
        bar = ctk.CTkFrame(self, **T.card_kwargs())
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkButton(inner, text="New product", command=self.show_product_dialog, **T.primary_button_kwargs(width=130, height=36)).pack(side="left")

        ctk.CTkLabel(inner, text="Search", **T.label_secondary()).pack(side="left", padx=(24, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(inner, textvariable=self.search_var, placeholder_text="SKU, description, or S/N…", **T.entry_kwargs(260))
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_products())

    def create_table(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkScrollableFrame(card, fg_color=T.SURFACE, corner_radius=0)
        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        self.headers = ["SKU", "Description", "S/N", "Qty", "Price", ""]
        self.widths = [100, 240, 140, 56, 90, 120]

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

        for i, p in enumerate(products):
            row = ctk.CTkFrame(self.rows_frame, fg_color=T.SURFACE_ALT if i % 2 == 0 else "transparent", corner_radius=T.RADIUS_SM)
            row.pack(fill="x", pady=1)

            color = T.DANGER if p.qty <= 3 else T.TEXT
            for text, width in [
                (p.sku or "—", self.widths[0]),
                (p.name, self.widths[1]),
                (p.serial_number or "—", self.widths[2]),
                (str(p.qty), self.widths[3]),
                (format_currency(p.price), self.widths[4]),
            ]:
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=color).pack(side="left", padx=6, pady=8)

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[5])
            actions.pack(side="left", padx=6)
            ctk.CTkButton(actions, text="Edit", width=52, command=lambda prod=p: self.show_product_dialog(prod), **T.button_kwargs(height=30)).pack(side="left", padx=2)
            ctk.CTkButton(actions, text="Delete", width=58, command=lambda prod=p: self.delete_product(prod), **T.button_kwargs(height=30, text_color=T.DANGER)).pack(side="left", padx=2)

    def delete_product(self, product: Product):
        if messagebox.askyesno("Delete product", f"Remove '{product.name}' from inventory?"):
            delete_product(product.id)
            self.load_products()
            self.winfo_toplevel().set_status(f"Deleted {product.name}")

    def show_product_dialog(self, product: Product = None):
        is_new = product is None
        dialog = ctk.CTkToplevel(self)
        dialog.title("New product" if is_new else "Edit product")
        dialog.geometry("440x420")
        dialog.configure(fg_color=T.BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.winfo_toplevel())

        card = ctk.CTkFrame(dialog, **T.card_kwargs())
        card.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)

        title = "Add product" if is_new else "Edit product"
        ctk.CTkLabel(inner, text=title, font=T.FONT_HEADLINE, text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="Ctrl+S to save · saves and opens next product" if is_new else "Ctrl+S to save",
            **T.label_secondary(),
        ).pack(anchor="w", pady=(4, 20))

        entries = {}
        field_defs = [
            ("SKU", "sku", "e.g. 60000"),
            ("Description", "name", "Product name"),
            ("Serial number", "serial_number", "Optional"),
            ("Price", "price", "0.00"),
            ("Quantity", "qty", "1"),
        ]

        ordered_entries = []
        for label, key, placeholder in field_defs:
            ctk.CTkLabel(inner, text=label, **T.label_secondary()).pack(anchor="w", pady=(0, 4))
            entry = ctk.CTkEntry(inner, placeholder_text=placeholder, **T.entry_kwargs())
            entry.pack(fill="x", pady=(0, 12))
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

        for i, entry in enumerate(ordered_entries[:-1]):
            entry.bind("<Return>", lambda e, n=ordered_entries[i + 1]: (n.focus_set(), "break")[1])
            entry.bind("<KP_Enter>", lambda e, n=ordered_entries[i + 1]: (n.focus_set(), "break")[1])
        ordered_entries[-1].bind("<Return>", lambda e: (save(), "break")[1])
        ordered_entries[-1].bind("<KP_Enter>", lambda e: (save(), "break")[1])

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))

        def save(add_another=False):
            try:
                name = entries["name"].get().strip()
                if not name:
                    raise ValueError("Description is required")
                price = float(entries["price"].get().strip() or "0")
                qty = int(entries["qty"].get().strip() or "0")
                if qty < 0:
                    raise ValueError("Quantity cannot be negative")

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
                    self.winfo_toplevel().set_status(f"Updated {name}")
                    dialog.destroy()
                else:
                    add_product(new_product)
                    self.winfo_toplevel().set_status(f"Added {name}")
                    dialog.destroy()
                    if add_another:
                        self.after(50, self.show_product_dialog)

                self.load_products()
            except ValueError as e:
                messagebox.showerror("Validation", str(e))

        def save_and_next():
            save(add_another=True)

        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, **T.button_kwargs()).pack(side="left")
        if is_new:
            ctk.CTkButton(btn_row, text="Save & next", command=save_and_next, **T.primary_button_kwargs(width=120, height=36)).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Save", command=lambda: save(False), **T.primary_button_kwargs(width=100, height=36)).pack(side="right")

        dialog.bind("<Control-s>", lambda e: save_and_next() if is_new else save(False))
        entries["sku"].focus_set()
