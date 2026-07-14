import customtkinter as ctk
from tkinter import messagebox
from database import add_product, update_product, delete_product, search_products
from models import Product
from utils import format_currency
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

        T.field_label(inner, "Search products").pack(side="left", padx=(24, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner, textvariable=self.search_var,
            placeholder_text="Name, code, or details…", **T.entry_kwargs(300),
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

        self.headers = ["Code", "Product name", "Details", "In stock", "Price", ""]
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

        width, height = 520, 360
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
        card.pack(fill="both", expand=True, padx=18, pady=18)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(18, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=0)

        # Top row: PRODUCT SKU | PRICE | QTY (compact)
        ctk.CTkLabel(body, text="PRODUCT SKU", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        ctk.CTkLabel(body, text="PRICE", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=1, sticky="w", padx=(0, 10)
        )
        ctk.CTkLabel(body, text="QTY", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=0, column=2, sticky="w"
        )
        sku_entry = ctk.CTkEntry(body, placeholder_text="e.g. 60000", **T.entry_kwargs(width=120))
        sku_entry.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(4, 14))
        price_entry = ctk.CTkEntry(body, placeholder_text="0.00", **T.entry_kwargs(width=90))
        price_entry.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(4, 14))
        qty_entry = ctk.CTkEntry(body, placeholder_text="1", **T.entry_kwargs(width=70))
        qty_entry.grid(row=1, column=2, sticky="w", pady=(4, 14))

        # Full-width name + details
        ctk.CTkLabel(body, text="PRODUCT NAME", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=2, column=0, columnspan=3, sticky="w"
        )
        name_entry = ctk.CTkEntry(body, placeholder_text="What is this product called?", **T.entry_kwargs())
        name_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 14))

        ctk.CTkLabel(body, text="DETAILS", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).grid(
            row=4, column=0, columnspan=3, sticky="w"
        )
        details_entry = ctk.CTkEntry(
            body, placeholder_text="Specs, S/N, or other text for the invoice", **T.entry_kwargs(),
        )
        details_entry.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 8))

        entries = {
            "sku": sku_entry,
            "price": price_entry,
            "qty": qty_entry,
            "name": name_entry,
            "serial_number": details_entry,
        }

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(4, 18))

        if product:
            sku_entry.insert(0, product.sku or "")
            name_entry.insert(0, product.name)
            details_entry.insert(0, product.serial_number or "")
            price_entry.insert(0, str(product.price))
            qty_entry.insert(0, str(product.qty))
        else:
            qty_entry.insert(0, "1")
            price_entry.insert(0, "0.00")

        def save(add_another=False):
            try:
                name = name_entry.get().strip()
                if not name:
                    raise ValueError("Product name is required")
                price = float(price_entry.get().strip() or "0")
                qty = int(qty_entry.get().strip() or "0")
                if qty < 0:
                    raise ValueError("Stock quantity cannot be negative")

                new_product = Product(
                    id=product.id if product else None,
                    name=name,
                    serial_number=details_entry.get().strip(),
                    sku=sku_entry.get().strip(),
                    price=price,
                    qty=qty,
                    category="",
                    created_at="",
                )

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
        if is_new:
            ctk.CTkButton(
                actions, text="SAVE NEXT  ·  F5", command=lambda: save(add_another=True),
                **T.button_kwargs(width=150),
            ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            actions, text="SAVE CLOSE  ·  F6", command=lambda: save(add_another=False),
            **T.success_button_kwargs(width=160),
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
