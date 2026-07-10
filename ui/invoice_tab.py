import customtkinter as ctk
from tkinter import messagebox
from database import search_products, generate_invoice_number, save_invoice, get_setting
from models import Invoice, InvoiceItem
from printer import print_receipt
from utils import format_currency, compute_invoice_totals
from . import theme as T
from .dialogs import ask_yes_no, ask_quantity, show_info
from .receipt_viewer import show_receipt_viewer


class InvoiceTab(ctk.CTkFrame):
    PAYMENT_METHODS = ["Cash", "Card", "Other"]

    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.items = []
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        self.discount_type = ctk.StringVar(value="percent")
        self._tax_caption_prefix = "Tax"

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=340)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._build_customer_row()
        self._build_main_area()
        self._build_sidebar()
        self._bind_manual_enter_keys()

    def focus_customer(self):
        self.customer_name_entry.focus_set()

    def focus_manual_desc(self):
        self.man_desc.focus_set()

    def focus_discount(self):
        self.discount_entry.focus_set()

    def _build_customer_row(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)

        T.section_title(inner, "Customer", "Optional — leave blank for walk-in customers").pack(anchor="w", pady=(0, 12))

        fields = ctk.CTkFrame(inner, fg_color="transparent")
        fields.pack(fill="x")

        name_col = ctk.CTkFrame(fields, fg_color="transparent")
        name_col.pack(side="left", fill="x", expand=True, padx=(0, 12))
        T.field_label(name_col, "Name").pack(anchor="w")
        self.customer_name_entry = ctk.CTkEntry(name_col, placeholder_text="Walk-in customer", **T.entry_kwargs())
        self.customer_name_entry.pack(fill="x", pady=(6, 0))

        phone_col = ctk.CTkFrame(fields, fg_color="transparent")
        phone_col.pack(side="left", fill="x", expand=True)
        T.field_label(phone_col, "Phone").pack(anchor="w")
        self.customer_phone_entry = ctk.CTkEntry(phone_col, placeholder_text="(416) 555-0100", **T.entry_kwargs())
        self.customer_phone_entry.pack(fill="x", pady=(6, 0))

    def _build_main_area(self):
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 8), pady=4)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        add_card = ctk.CTkFrame(left, **T.card_kwargs())
        add_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        add_inner = ctk.CTkFrame(add_card, fg_color="transparent")
        add_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)

        T.section_title(add_inner, "Add a product", "Search by name or product code").pack(anchor="w", pady=(0, 10))

        row1 = ctk.CTkFrame(add_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 10))
        row1.grid_columnconfigure(1, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            row1, textvariable=self.search_var, placeholder_text="Type to search…", **T.entry_compact(),
        )
        self.search_entry.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Return>", self.on_search_enter)
        self.search_entry.bind("<KP_Enter>", self.on_search_enter)

        self.search_results = ctk.CTkComboBox(row1, values=[], **T.combo_kwargs(720))
        self.search_results.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            row1,
            text="Add to sale",
            width=140,
            command=self.add_inventory_item,
            **T.primary_button_kwargs(),
        ).grid(row=0, column=2, sticky="e")
        self.current_search_products = []

        row2 = ctk.CTkFrame(add_inner, fg_color="transparent")
        row2.pack(fill="x", pady=(4, 0))
        T.field_label(row2, "Custom item", "For items not in your inventory").pack(side="left", padx=(0, 12))
        self.man_desc = ctk.CTkEntry(row2, placeholder_text="What are you selling?", **T.entry_kwargs(300))
        self.man_desc.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.man_qty = ctk.CTkEntry(row2, placeholder_text="Qty", **T.entry_kwargs(72))
        self.man_qty.insert(0, "1")
        self.man_qty.pack(side="left", padx=(0, 8))
        self.man_price = ctk.CTkEntry(row2, placeholder_text="Price", **T.entry_kwargs(100))
        self.man_price.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row2, text="Add", width=90, command=self.add_manual_item, **T.button_kwargs()).pack(side="left")

        lines_card = ctk.CTkFrame(left, **T.card_kwargs())
        lines_card.grid(row=1, column=0, sticky="nsew")
        lines_inner = ctk.CTkFrame(lines_card, fg_color="transparent")
        lines_inner.pack(fill="both", expand=True, padx=T.PAD_CARD, pady=T.PAD_CARD)
        lines_inner.grid_rowconfigure(1, weight=1)
        lines_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lines_inner, text="Items in this sale", font=T.FONT_HEADLINE, text_color=T.TEXT).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.items_scroll = ctk.CTkScrollableFrame(lines_inner, fg_color=T.SURFACE_ALT, corner_radius=T.RADIUS_SM)
        self.items_scroll.grid(row=1, column=0, sticky="nsew")

        hdr = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 6))
        for text, w in [("#", 32), ("Item", 220), ("Qty", 100), ("Price", 80), ("Total", 90)]:
            ctk.CTkLabel(hdr, text=text, width=w, **T.table_header_kwargs()).pack(side="left", padx=4)

        self.item_rows_frame = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        self.item_rows_frame.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        self.empty_label = ctk.CTkLabel(
            self.item_rows_frame,
            text="No items yet — search for a product above to get started",
            font=T.FONT, text_color=T.TEXT_TERTIARY,
        )

    def _build_sidebar(self):
        side = ctk.CTkFrame(self, fg_color="transparent", width=340)
        side.grid(row=1, column=1, sticky="nsew", padx=(0, 4), pady=4)
        side.grid_rowconfigure(0, weight=1)
        side.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(side, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")

        summary = ctk.CTkFrame(scroll, fg_color=T.ACCENT_SOFT, corner_radius=T.RADIUS_LG, border_width=0)
        summary.pack(fill="x", pady=(0, 10))

        s_inner = ctk.CTkFrame(summary, fg_color="transparent")
        s_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)

        self.subtotal_label = self._summary_row(s_inner, "Subtotal", "$0.00")
        self.discount_summary_label = self._summary_row(s_inner, "Discount", "−$0.00")
        self.tax_label = self._summary_row(s_inner, self._tax_caption(), "$0.00")

        ctk.CTkFrame(s_inner, fg_color=T.BORDER, height=1, corner_radius=0).pack(fill="x", pady=12)
        ctk.CTkLabel(s_inner, text="Total due", font=T.FONT_MEDIUM, text_color=T.TEXT, anchor="w").pack(anchor="w")
        self.total_label = ctk.CTkLabel(s_inner, text="$0.00", font=T.FONT_HERO, text_color=T.ACCENT, anchor="e")
        self.total_label.pack(anchor="e", pady=(4, 0))

        discount_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        discount_card.pack(fill="x", pady=(0, 10))
        d_inner = ctk.CTkFrame(discount_card, fg_color="transparent")
        d_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)

        T.field_label(d_inner, "Discount").pack(anchor="w", pady=(0, 8))

        type_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        type_row.pack(fill="x", pady=(0, 8))
        ctk.CTkRadioButton(
            type_row, text="Percent (%)", variable=self.discount_type, value="percent",
            command=self.refresh_items, font=T.FONT, text_color=T.TEXT,
            fg_color=T.ACCENT, border_color=T.BORDER, radiobutton_width=20, radiobutton_height=20,
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            type_row, text="Dollar amount ($)", variable=self.discount_type, value="fixed",
            command=self.refresh_items, font=T.FONT, text_color=T.TEXT,
            fg_color=T.ACCENT, border_color=T.BORDER, radiobutton_width=20, radiobutton_height=20,
        ).pack(side="left")

        self.discount_entry = ctk.CTkEntry(d_inner, placeholder_text="0", **T.entry_kwargs())
        self.discount_entry.pack(fill="x")
        self.discount_entry.bind("<KeyRelease>", lambda e: self.refresh_items())

        pay_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        pay_card.pack(fill="x", pady=(0, 10))
        p_inner = ctk.CTkFrame(pay_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)

        T.field_label(p_inner, "How did they pay?").pack(anchor="w", pady=(0, 10))
        self.payment_var = ctk.StringVar(value="Cash")
        pay_row = ctk.CTkFrame(p_inner, fg_color="transparent")
        pay_row.pack(fill="x")
        for method in self.PAYMENT_METHODS:
            ctk.CTkRadioButton(
                pay_row, text=method, variable=self.payment_var, value=method,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
                radiobutton_width=20, radiobutton_height=20,
            ).pack(side="left", padx=(0, 16))

        notes_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        notes_card.pack(fill="x", pady=(0, 10))
        n_inner = ctk.CTkFrame(notes_card, fg_color="transparent")
        n_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.field_label(n_inner, "Note", "Only you see this — not printed on receipt").pack(anchor="w")
        self.notes_entry = ctk.CTkEntry(n_inner, placeholder_text="Optional internal note", **T.entry_kwargs())
        self.notes_entry.pack(fill="x", pady=(6, 0))

        self._build_action_dock()

    def _build_action_dock(self):
        dock = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=T.RADIUS_LG, border_width=1, border_color=T.BORDER_LIGHT)
        dock.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))

        inner = ctk.CTkFrame(dock, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=14)

        ctk.CTkButton(
            inner,
            text="Complete Sale & Print Receipt",
            command=lambda: self.save(print_rcpt=True),
            **T.success_button_kwargs(width=280),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            inner,
            text="Preview Receipt",
            command=self.preview_receipt,
            **T.button_kwargs(width=150),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            inner,
            text="Save Without Printing",
            command=lambda: self.save(print_rcpt=False),
            **T.button_kwargs(width=180),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            inner,
            text="Start New Sale",
            command=self.clear_form,
            **T.button_kwargs(width=140),
        ).pack(side="right")

    def _tax_caption(self):
        return f"Tax ({int(self.tax_rate * 100)}%)"

    def _summary_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        title = ctk.CTkLabel(row, text=label, **T.label_secondary())
        title.pack(side="left")
        val = ctk.CTkLabel(row, text=value, font=T.FONT_MEDIUM, text_color=T.TEXT, anchor="e")
        val.pack(side="right")
        val._title_label = title
        return val

    def _bind_manual_enter_keys(self):
        for widget, nxt in ((self.man_desc, self.man_qty), (self.man_qty, self.man_price)):
            widget.bind("<Return>", lambda e, n=nxt: (n.focus_set(), "break")[1])
            widget.bind("<KP_Enter>", lambda e, n=nxt: (n.focus_set(), "break")[1])
        self.man_price.bind("<Return>", lambda e: (self.add_manual_item(), "break")[1])
        self.man_price.bind("<KP_Enter>", lambda e: (self.add_manual_item(), "break")[1])

    def _get_discount_value(self) -> float:
        try:
            return max(0.0, float(self.discount_entry.get().strip() or "0"))
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
            return
        self.current_search_products = search_products(query)
        values = [f"{p.name}  —  {format_currency(p.price)}  ({p.qty} in stock)" for p in self.current_search_products]
        self.search_results.configure(values=values)
        if values:
            self.search_results.set(values[0])

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
            show_info(self.winfo_toplevel(), "Not found", "No products match your search. Try a different name or code.")
            return

        idx = 0
        selection = self.search_results.get()
        values = self.search_results.cget("values") or []
        if selection and selection in values:
            idx = values.index(selection)
        elif len(self.current_search_products) != 1:
            show_info(self.winfo_toplevel(), "Pick a product", "Please choose a product from the list first.")
            return

        p = self.current_search_products[idx]
        if p.qty <= 0:
            show_info(self.winfo_toplevel(), "Out of stock", f"'{p.name}' is out of stock.")
            return

        qty = ask_quantity(self.winfo_toplevel(), p.name, max_qty=p.qty)
        if qty is None:
            return

        self.items.append(InvoiceItem(
            id=None, invoice_id=None, product_id=p.id,
            description=p.name, serial_number=p.serial_number or "",
            qty=qty, unit_price=p.price, line_total=qty * p.price,
        ))
        self.refresh_items()
        self.search_var.set("")
        self.search_results.configure(values=[])
        self.current_search_products = []
        self.search_entry.focus_set()

    def add_manual_item(self):
        desc = self.man_desc.get().strip()
        if not desc:
            show_info(self.winfo_toplevel(), "Missing description", "Please enter what you're selling.")
            self.man_desc.focus_set()
            return
        try:
            qty = int(self.man_qty.get().strip())
            if qty <= 0:
                raise ValueError
        except ValueError:
            show_info(self.winfo_toplevel(), "Invalid quantity", "Quantity must be a whole number greater than zero.")
            self.man_qty.focus_set()
            return
        try:
            price = float(self.man_price.get().strip())
            if price < 0:
                raise ValueError
        except ValueError:
            show_info(self.winfo_toplevel(), "Invalid price", "Please enter a valid price.")
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
                    desc_text += f"\n  S/N: {item.serial_number}"
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
        subtotal, discount_amount, tax_amount, total = compute_invoice_totals(self.items, self.tax_rate, dtype, dval)

        self.subtotal_label.configure(text=format_currency(subtotal))
        if discount_amount > 0:
            label = f"−{format_currency(discount_amount)}"
            if dtype == "percent":
                label += f" ({dval:g}%)"
            self.discount_summary_label.configure(text=label)
        else:
            self.discount_summary_label.configure(text="−$0.00")
        self.tax_label.configure(text=format_currency(tax_amount))
        self.tax_label._title_label.configure(text=self._tax_caption())
        self.total_label.configure(text=format_currency(total))

    def _build_invoice(self) -> Invoice:
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        dtype = self.discount_type.get()
        dval = self._get_discount_value()
        subtotal, discount_amount, tax_amount, total = compute_invoice_totals(self.items, self.tax_rate, dtype, dval)

        return Invoice(
            id=None,
            invoice_number=generate_invoice_number(),
            customer_name=self.customer_name_entry.get().strip(),
            customer_phone=self.customer_phone_entry.get().strip(),
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
        )

    def preview_receipt(self):
        if not self.items:
            show_info(self.winfo_toplevel(), "Nothing to preview", "Add at least one item to preview the receipt.")
            return
        from datetime import datetime
        invoice = self._build_invoice()
        invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        show_receipt_viewer(self.winfo_toplevel(), invoice, list(self.items), is_preview=True)

    def save(self, print_rcpt=True):
        if not self.items:
            show_info(self.winfo_toplevel(), "Nothing to save", "Add at least one item before completing the sale.")
            return

        invoice = self._build_invoice()
        action = "complete this sale and print the receipt" if print_rcpt else "save this sale without printing"
        if not ask_yes_no(
            self.winfo_toplevel(),
            "Confirm sale",
            f"Total: {format_currency(invoice.total)}\n\nAre you ready to {action}?",
        ):
            return

        try:
            save_invoice(invoice, self.items)
            msg = f"Sale saved — {invoice.invoice_number}"
            if print_rcpt:
                from datetime import datetime
                invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                printed, print_msg = print_receipt(invoice, self.items)
                msg += " · Receipt printed" if printed else " · Print failed"
                if not printed:
                    messagebox.showerror("Print failed", print_msg)
                else:
                    show_info(self.winfo_toplevel(), "Sale complete!", f"Receipt printed.\n\n{invoice.invoice_number}\nTotal: {format_currency(invoice.total)}")
            else:
                show_info(self.winfo_toplevel(), "Sale saved!", f"{invoice.invoice_number}\nTotal: {format_currency(invoice.total)}")

            self.winfo_toplevel().set_status(msg)
            self.clear_form(keep_customer=True)
            app = self.winfo_toplevel()
            if hasattr(app, "inventory_tab"):
                app.inventory_tab.load_products()
            if hasattr(app, "reports_tab"):
                app.reports_tab.load_invoices()
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def clear_form(self, keep_customer=False):
        if not keep_customer:
            self.customer_name_entry.delete(0, "end")
            self.customer_phone_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.discount_entry.delete(0, "end")
        self.discount_type.set("percent")
        self.items = []
        self.payment_var.set("Cash")
        self.refresh_items()
        self.focus_customer()
