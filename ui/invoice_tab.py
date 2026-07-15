import customtkinter as ctk
from tkinter import messagebox
from database import search_products, generate_invoice_number, save_invoice, get_setting
from models import Invoice, InvoiceItem
from printer import print_receipt
from utils import format_currency, compute_invoice_totals
from . import theme as T
from .dialogs import ask_yes_no, ask_payment_method
from .toast import toast
from .receipt_viewer import show_receipt_viewer


class InvoiceTab(ctk.CTkFrame):
    PAYMENT_METHODS = ["Cash", "Card", "Other"]

    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.items = []
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        self.discount_type = ctk.StringVar(value="percent")
        self.payment_var = ctk.StringVar(value="Cash")
        self._tax_caption_prefix = "HST"
        self.current_search_products = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=300)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)

        self._build_customer_row()
        self._build_entry_rows()
        self._build_sale_body()
        self._build_action_dock()
        self._bind_manual_enter_keys()
        self.refresh_items()

    def focus_customer(self):
        self.customer_name_entry.focus_set()

    def focus_manual_desc(self):
        self.man_desc.focus_set()

    def focus_discount(self):
        self.discount_pct_entry.focus_set()

    def _labeled_entry(self, parent, label, placeholder, width=None, expand=False):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(side="left", fill="x", expand=expand, padx=(0, 12))
        ctk.CTkLabel(wrap, text=label, font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).pack(anchor="w")
        kw = T.entry_kwargs(width=width) if width else T.entry_kwargs()
        entry = ctk.CTkEntry(wrap, placeholder_text=placeholder, **kw)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def _build_customer_row(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 4))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)

        self.customer_name_entry = self._labeled_entry(row, "NAME", "Customer name", expand=True)
        self.customer_phone_entry = self._labeled_entry(row, "PHONE", "(416) 555-0100", width=160)
        self.customer_email_entry = self._labeled_entry(row, "EMAIL", "name@email.com", expand=True)
        # last field shouldn't pad right
        self.customer_email_entry.master.pack_configure(padx=0)

    def _build_entry_rows(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # SKU row — search + product picker + ADD
        sku_row = ctk.CTkFrame(inner, fg_color="transparent")
        sku_row.pack(fill="x", pady=(0, 8))
        sku_row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(sku_row, text="SKU", font=T.FONT_MEDIUM, text_color=T.TEXT, width=64, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            sku_row, textvariable=self.search_var, placeholder_text="Code…", **T.entry_kwargs(width=110),
        )
        self.search_entry.grid(row=0, column=1, sticky="w", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Return>", self.on_search_enter)
        self.search_entry.bind("<KP_Enter>", self.on_search_enter)

        self.search_results = ctk.CTkComboBox(
            sku_row, values=[], command=self.on_product_selected, **T.combo_kwargs(width=520),
        )
        self.search_results.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.search_results.set("SKU — Name — Details — Qty")

        ctk.CTkButton(
            sku_row, text="ADD", width=88, command=self.add_inventory_item, **T.primary_button_kwargs(),
        ).grid(row=0, column=3, sticky="e")

        self.selected_details_var = ctk.StringVar(value="")

        # CUSTOM row
        custom_row = ctk.CTkFrame(inner, fg_color="transparent")
        custom_row.pack(fill="x")
        custom_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(custom_row, text="CUSTOM", font=T.FONT_MEDIUM, text_color=T.TEXT, width=64, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.man_desc = ctk.CTkEntry(custom_row, placeholder_text="Item not in inventory", **T.entry_kwargs())
        self.man_desc.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.man_qty = ctk.CTkEntry(custom_row, placeholder_text="Qty", **T.entry_kwargs(width=72))
        self.man_qty.insert(0, "1")
        self.man_qty.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.man_price = ctk.CTkEntry(custom_row, placeholder_text="Price", **T.entry_kwargs(width=100))
        self.man_price.grid(row=0, column=3, sticky="w", padx=(0, 8))
        ctk.CTkButton(
            custom_row, text="ADD", width=88, command=self.add_manual_item, **T.button_kwargs(),
        ).grid(row=0, column=4, sticky="e")

    def _build_sale_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=300)
        body.grid_rowconfigure(0, weight=1)

        # ITEMS IN THIS SALE — primary surface
        lines_card = ctk.CTkFrame(body, **T.card_kwargs())
        lines_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lines_inner = ctk.CTkFrame(lines_card, fg_color="transparent")
        lines_inner.pack(fill="both", expand=True, padx=14, pady=12)
        lines_inner.grid_rowconfigure(1, weight=1)
        lines_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            lines_inner, text="ITEMS IN THIS SALE", font=T.FONT_HEADLINE, text_color=T.TEXT,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.items_scroll = ctk.CTkScrollableFrame(lines_inner, fg_color=T.SURFACE_ALT, corner_radius=T.RADIUS_SM)
        self.items_scroll.grid(row=1, column=0, sticky="nsew")

        hdr = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 6))
        for text, w in [("#", 32), ("Item", 260), ("Qty", 100), ("Price", 90), ("Total", 90)]:
            ctk.CTkLabel(hdr, text=text, width=w, **T.table_header_kwargs()).pack(side="left", padx=4)

        self.item_rows_frame = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        self.item_rows_frame.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        # Right rail — scrollable so totals/notes/discount stay reachable at 125% scaling
        side = ctk.CTkScrollableFrame(body, fg_color="transparent", width=300, corner_radius=0)
        side.grid(row=0, column=1, sticky="nsew")

        summary = ctk.CTkFrame(side, fg_color=T.ACCENT_SOFT, corner_radius=T.RADIUS_LG, border_width=0)
        summary.pack(fill="x", pady=(0, 8))
        s_inner = ctk.CTkFrame(summary, fg_color="transparent")
        s_inner.pack(fill="x", padx=16, pady=16)

        self.subtotal_label = self._summary_row(s_inner, "Subtotal", "$0.00")
        self.discount_summary_label = self._summary_row(s_inner, "Discount", "−$0.00")
        self.tax_label = self._summary_row(s_inner, self._tax_caption(), "$0.00")

        ctk.CTkFrame(s_inner, fg_color=T.BORDER, height=1, corner_radius=0).pack(fill="x", pady=12)
        ctk.CTkLabel(s_inner, text="TOTAL DUE", font=T.FONT_MEDIUM, text_color=T.TEXT, anchor="w").pack(anchor="w")
        self.total_label = ctk.CTkLabel(s_inner, text="$0.00", font=T.FONT_HERO, text_color=T.ACCENT, anchor="e")
        self.total_label.pack(anchor="e", pady=(2, 0))

        notes_card = ctk.CTkFrame(side, **T.card_kwargs())
        notes_card.pack(fill="x", pady=(0, 8))
        n_inner = ctk.CTkFrame(notes_card, fg_color="transparent")
        n_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(n_inner, text="NOTES", font=T.FONT_MEDIUM, text_color=T.TEXT).pack(anchor="w")
        self.notes_entry = ctk.CTkEntry(n_inner, placeholder_text="Printed on the invoice", **T.entry_kwargs())
        self.notes_entry.pack(fill="x", pady=(6, 0))

        discount_card = ctk.CTkFrame(side, **T.card_kwargs())
        discount_card.pack(fill="x")
        d_inner = ctk.CTkFrame(discount_card, fg_color="transparent")
        d_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(d_inner, text="DISCOUNT", font=T.FONT_MEDIUM, text_color=T.TEXT).pack(anchor="w")

        d_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        d_row.pack(fill="x", pady=(8, 0))
        self.discount_pct_entry = ctk.CTkEntry(d_row, placeholder_text="0", **T.entry_kwargs(width=72))
        self.discount_pct_entry.pack(side="left")
        self.discount_pct_entry.bind("<KeyRelease>", self._on_discount_pct)
        ctk.CTkButton(
            d_row, text="%", width=40, command=self._apply_pct_discount, **T.button_kwargs(height=T.BTN_HEIGHT),
        ).pack(side="left", padx=(6, 14))
        self.discount_amt_entry = ctk.CTkEntry(d_row, placeholder_text="0.00", **T.entry_kwargs(width=88))
        self.discount_amt_entry.pack(side="left")
        self.discount_amt_entry.bind("<KeyRelease>", self._on_discount_amt)
        ctk.CTkButton(
            d_row, text="$", width=40, command=self._apply_amt_discount, **T.button_kwargs(height=T.BTN_HEIGHT),
        ).pack(side="left", padx=(6, 0))

        timing_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        timing_row.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(timing_row, text="Apply", font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY).pack(
            side="left", padx=(0, 10)
        )
        default_timing = get_setting("discount_timing", "before_tax") or "before_tax"
        self.discount_timing = ctk.StringVar(value=default_timing)
        for value, label in (("before_tax", "Before tax"), ("after_tax", "After tax")):
            ctk.CTkRadioButton(
                timing_row,
                text=label,
                variable=self.discount_timing,
                value=value,
                command=self.refresh_items,
                font=T.FONT_CAPTION,
                text_color=T.TEXT,
                fg_color=T.ACCENT,
                border_color=T.BORDER,
                radiobutton_width=18,
                radiobutton_height=18,
            ).pack(side="left", padx=(0, 12))

        # Compatibility alias used by older helpers
        self.discount_entry = self.discount_pct_entry

    def _build_action_dock(self):
        dock = ctk.CTkFrame(self, **T.raised_card_kwargs())
        dock.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 2))

        inner = ctk.CTkFrame(dock, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkButton(
            inner, text="COMPLETE  ·  F12", command=lambda: self.save(print_rcpt=True),
            **T.success_button_kwargs(width=180),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            inner, text="PREVIEW  ·  F11", command=self.preview_receipt, **T.button_kwargs(width=140),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            inner, text="SAVE  ·  F10", command=lambda: self.save(print_rcpt=False), **T.button_kwargs(width=120),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            inner, text="NEW  ·  F1", command=self.clear_form, **T.button_kwargs(width=110),
        ).pack(side="right")

        legend = ctk.CTkLabel(
            dock,
            text="F1 New  ·  F2 Products  ·  F3 Reports  ·  F4 Setup  ·  F10 Save  ·  F11 Preview  ·  F12 Complete + Print  ·  then F7 Cash / F8 Card / F12 Confirm",
            font=T.FONT_CAPTION, text_color=T.TEXT_TERTIARY, anchor="w",
        )
        legend.pack(fill="x", padx=14, pady=(0, 10))

    def _tax_caption(self):
        return f"HST ({int(self.tax_rate * 100)}%)"

    def _summary_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        title = ctk.CTkLabel(row, text=label, **T.label_secondary())
        title.pack(side="left")
        val = ctk.CTkLabel(row, text=value, font=T.FONT_MEDIUM, text_color=T.TEXT, anchor="e")
        val.pack(side="right")
        val._title_label = title
        return val

    def _on_discount_pct(self, event=None):
        self.discount_type.set("percent")
        self.refresh_items()

    def _on_discount_amt(self, event=None):
        self.discount_type.set("fixed")
        self.refresh_items()

    def _apply_pct_discount(self):
        self.discount_type.set("percent")
        self.discount_amt_entry.delete(0, "end")
        self.refresh_items()

    def _apply_amt_discount(self):
        self.discount_type.set("fixed")
        self.discount_pct_entry.delete(0, "end")
        self.refresh_items()

    def _bind_manual_enter_keys(self):
        for widget, nxt in ((self.man_desc, self.man_qty), (self.man_qty, self.man_price)):
            widget.bind("<Return>", lambda e, n=nxt: (n.focus_set(), "break")[1])
            widget.bind("<KP_Enter>", lambda e, n=nxt: (n.focus_set(), "break")[1])
        self.man_price.bind("<Return>", lambda e: (self.add_manual_item(), "break")[1])
        self.man_price.bind("<KP_Enter>", lambda e: (self.add_manual_item(), "break")[1])

    def _get_discount_value(self) -> float:
        if self.discount_type.get() == "fixed":
            try:
                return max(0.0, float(self.discount_amt_entry.get().strip() or "0"))
            except ValueError:
                return 0.0
        try:
            return max(0.0, float(self.discount_pct_entry.get().strip() or "0"))
        except ValueError:
            return 0.0

    def cycle_payment_method(self):
        methods = self.PAYMENT_METHODS
        idx = methods.index(self.payment_var.get()) if self.payment_var.get() in methods else 0
        self.payment_var.set(methods[(idx + 1) % len(methods)])
        self.winfo_toplevel().set_status(f"Payment: {self.payment_var.get()}")

    def on_search(self, event=None):
        query = self.search_var.get().strip()
        if not query:
            self.search_results.configure(values=[])
            self.current_search_products = []
            self.selected_details_var.set("")
            self.search_results.set("SKU — Name — Details — Qty")
            return
        self.current_search_products = search_products(query)
        values = []
        for p in self.current_search_products:
            sku = p.sku or "—"
            details = (p.serial_number or "—").replace("\n", " ")
            if len(details) > 40:
                details = details[:37] + "…"
            values.append(f"{sku} — {p.name} — {details} — {p.qty}")
        self.search_results.configure(values=values)
        if values:
            self.search_results.set(values[0])
            self.on_product_selected(values[0])
        else:
            self.selected_details_var.set("")
            self.search_results.set("No matches")

    def on_product_selected(self, choice=None):
        p = self._selected_search_product()
        self.selected_details_var.set((p.serial_number or "") if p else "")

    def _selected_search_product(self):
        if not self.current_search_products:
            return None
        selection = self.search_results.get()
        values = self.search_results.cget("values") or []
        if selection and selection in values:
            return self.current_search_products[values.index(selection)]
        if len(self.current_search_products) == 1:
            return self.current_search_products[0]
        return None

    def on_search_enter(self, event=None):
        query = self.search_var.get().strip()
        if query and not self.current_search_products:
            self.on_search()
        if self.current_search_products:
            self.add_inventory_item()
        return "break"

    def add_inventory_item(self):
        if not self.current_search_products:
            query = self.search_var.get().strip()
            if not query:
                return
            self.on_search()

        if not self.current_search_products:
            toast(self, "No products match your search. Try a different name or code.", kind="warning")
            return

        p = self._selected_search_product()
        if p is None:
            toast(self, "Choose a product from the list first.", kind="info")
            return

        if p.qty <= 0:
            toast(self, f"'{p.name}' is out of stock.", kind="warning")
            return

        details = self.selected_details_var.get().strip() or (p.serial_number or "")
        qty = 1
        self.items.append(InvoiceItem(
            id=None, invoice_id=None, product_id=p.id,
            description=p.name, serial_number=details,
            qty=qty, unit_price=p.price, line_total=qty * p.price,
        ))
        self.refresh_items()
        self.search_var.set("")
        self.search_results.configure(values=[])
        self.current_search_products = []
        self.selected_details_var.set("")
        self.search_entry.focus_set()
        toast(self, f"Added {p.name}", kind="success")

    def add_manual_item(self):
        desc = self.man_desc.get().strip()
        if not desc:
            toast(self, "Enter what you're selling.", kind="warning")
            self.man_desc.focus_set()
            return
        try:
            qty = int(self.man_qty.get().strip())
            if qty <= 0:
                raise ValueError
        except ValueError:
            toast(self, "Quantity must be a whole number greater than zero.", kind="warning")
            self.man_qty.focus_set()
            return
        try:
            price = float(self.man_price.get().strip())
            if price < 0:
                raise ValueError
        except ValueError:
            toast(self, "Enter a valid price.", kind="warning")
            self.man_price.focus_set()
            return
        self.items.append(InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description=desc, serial_number="", qty=qty, unit_price=price, line_total=qty * price,
        ))
        self.refresh_items()
        self.man_desc.delete(0, "end")
        self.man_qty.delete(0, "end")
        self.man_qty.insert(0, "1")
        self.man_price.delete(0, "end")
        self.man_desc.focus_set()
        toast(self, f"Added {desc}", kind="success")

    def change_qty(self, index: int, delta: int):
        if 0 <= index < len(self.items):
            item = self.items[index]
            new_qty = item.qty + delta
            if new_qty <= 0:
                self.remove_item(index)
            else:
                item.qty = new_qty
                item.line_total = new_qty * item.unit_price
                self.refresh_items()

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_items()

    def refresh_items(self):
        for w in self.item_rows_frame.winfo_children():
            w.destroy()

        if not self.items:
            self.empty_label = ctk.CTkLabel(
                self.item_rows_frame,
                text="No items yet — search for a product above to get started",
                font=T.FONT, text_color=T.TEXT_TERTIARY,
            )
            self.empty_label.pack(pady=40)
        else:
            for i, item in enumerate(self.items):
                row = ctk.CTkFrame(
                    self.item_rows_frame,
                    fg_color=T.SURFACE if i % 2 == 0 else "transparent",
                    corner_radius=T.RADIUS_SM,
                )
                row.pack(fill="x", pady=2)

                ctk.CTkLabel(row, text=str(i + 1), width=32, anchor="w", font=T.FONT, text_color=T.TEXT).pack(
                    side="left", padx=4, pady=10
                )
                desc_text = item.description
                if item.serial_number:
                    desc_text += f"\n  Details: {item.serial_number}"
                ctk.CTkLabel(row, text=desc_text, width=220, anchor="w", font=T.FONT, text_color=T.TEXT, justify="left").pack(
                    side="left", padx=4
                )

                qty_frame = ctk.CTkFrame(row, fg_color="transparent", width=100)
                qty_frame.pack(side="left", padx=4)
                ctk.CTkButton(qty_frame, text="−", width=36, command=lambda idx=i: self.change_qty(idx, -1), **T.button_kwargs(height=32)).pack(side="left")
                ctk.CTkLabel(qty_frame, text=str(item.qty), width=28, font=T.FONT_MEDIUM, text_color=T.TEXT).pack(side="left")
                ctk.CTkButton(qty_frame, text="+", width=36, command=lambda idx=i: self.change_qty(idx, 1), **T.button_kwargs(height=32)).pack(side="left")

                ctk.CTkLabel(row, text=format_currency(item.unit_price), width=80, anchor="w", font=T.FONT, text_color=T.TEXT).pack(side="left", padx=4)
                ctk.CTkLabel(row, text=format_currency(item.line_total), width=90, anchor="w", font=T.FONT_MEDIUM, text_color=T.TEXT).pack(side="left", padx=4)

                ctk.CTkButton(
                    row, text="Remove", command=lambda idx=i: self.remove_item(idx),
                    **T.button_kwargs(width=80, height=32, text_color=T.DANGER),
                ).pack(side="right", padx=6)

        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        dtype = self.discount_type.get()
        dval = self._get_discount_value()
        timing = self.discount_timing.get() if hasattr(self, "discount_timing") else "before_tax"
        subtotal, discount_amount, tax_amount, total = compute_invoice_totals(
            self.items, self.tax_rate, dtype, dval, timing,
        )

        self.subtotal_label.configure(text=format_currency(subtotal))
        if discount_amount > 0:
            label = f"−{format_currency(discount_amount)}"
            if dtype == "percent":
                label += f" ({dval:g}%)"
            when = "after tax" if timing == "after_tax" else "before tax"
            self.discount_summary_label.configure(text=f"{label} · {when}")
            self.discount_summary_label._title_label.configure(text="Discount")
        else:
            self.discount_summary_label.configure(text="−$0.00")
            self.discount_summary_label._title_label.configure(text="Discount")
        self.tax_label.configure(text=format_currency(tax_amount))
        self.tax_label._title_label.configure(text=self._tax_caption())
        self.total_label.configure(text=format_currency(total))

    def _build_invoice(self) -> Invoice:
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        dtype = self.discount_type.get()
        dval = self._get_discount_value()
        timing = self.discount_timing.get() if hasattr(self, "discount_timing") else "before_tax"
        subtotal, discount_amount, tax_amount, total = compute_invoice_totals(
            self.items, self.tax_rate, dtype, dval, timing,
        )

        return Invoice(
            id=None,
            invoice_number=generate_invoice_number(),
            customer_name=self.customer_name_entry.get().strip(),
            customer_phone=self.customer_phone_entry.get().strip(),
            customer_email=self.customer_email_entry.get().strip(),
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            total=total,
            payment_method=self.payment_var.get(),
            notes=self.notes_entry.get().strip(),
            created_at=None,
            items=[],
            discount_type=dtype if dval > 0 else "",
            discount_value=dval,
            discount_amount=discount_amount,
            discount_timing=timing,
        )

    def preview_receipt(self):
        if not self.items:
            toast(self, "Add at least one item to preview the receipt.", kind="info")
            return
        from datetime import datetime
        invoice = self._build_invoice()
        invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        show_receipt_viewer(self.winfo_toplevel(), invoice, list(self.items), is_preview=True)

    def save(self, print_rcpt=True):
        if not self.items:
            toast(self, "Add at least one item before completing the sale.", kind="warning")
            return

        if print_rcpt:
            payment = ask_payment_method(
                self.winfo_toplevel(),
                default=self.payment_var.get(),
            )
            if payment is None:
                return
            self.payment_var.set(payment)

        invoice = self._build_invoice()
        if print_rcpt:
            confirmed = ask_yes_no(
                self.winfo_toplevel(),
                "Complete sale & print?",
                f"Total: {format_currency(invoice.total)}\nPaid by: {invoice.payment_method}\n\nThis will save the sale and print the receipt.",
                confirm_label="Complete & print",
                cancel_label="Not yet",
            )
        else:
            confirmed = ask_yes_no(
                self.winfo_toplevel(),
                "Save this sale?",
                f"Total: {format_currency(invoice.total)}\n\nSave without printing a receipt.",
                confirm_label="Save sale",
                cancel_label="Not yet",
            )
        if not confirmed:
            return

        try:
            save_invoice(invoice, self.items)
            msg = f"Sale saved — {invoice.invoice_number}"
            if print_rcpt:
                from datetime import datetime
                invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                printed, print_msg = print_receipt(invoice, self.items)
                if printed:
                    msg = f"Sale complete · {invoice.invoice_number} · {format_currency(invoice.total)}"
                    toast(self, msg, kind="success", title="Receipt printed")
                else:
                    toast(self, print_msg, kind="error", title="Sale saved, but print failed")
                    messagebox.showerror("Print failed", print_msg)
            else:
                toast(
                    self,
                    f"{invoice.invoice_number} · {format_currency(invoice.total)}",
                    kind="success",
                    title="Sale saved",
                )

            self.winfo_toplevel().set_status(msg)
            self.clear_form(keep_customer=True)
            app = self.winfo_toplevel()
            if hasattr(app, "inventory_tab"):
                app.inventory_tab.load_products()
            if hasattr(app, "reports_tab"):
                app.reports_tab.load_invoices()
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            toast(self, str(e), kind="error", title="Could not save")

    def clear_form(self, keep_customer=False):
        if not keep_customer:
            self.customer_name_entry.delete(0, "end")
            self.customer_phone_entry.delete(0, "end")
            self.customer_email_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.discount_pct_entry.delete(0, "end")
        self.discount_amt_entry.delete(0, "end")
        self.discount_type.set("percent")
        if hasattr(self, "discount_timing"):
            self.discount_timing.set(get_setting("discount_timing", "before_tax") or "before_tax")
        self.items = []
        self.payment_var.set("Cash")
        self.selected_details_var.set("")
        self.search_var.set("")
        self.search_results.configure(values=[])
        self.search_results.set("SKU — Name — Details — Qty")
        self.current_search_products = []
        self.refresh_items()
        self.focus_customer()
