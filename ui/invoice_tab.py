import customtkinter as ctk
from tkinter import messagebox
from database import search_products, generate_invoice_number, save_invoice, get_setting
from models import Invoice, InvoiceItem
from printer import print_receipt
from utils import format_currency, compute_invoice_totals
from . import theme as T


class InvoiceTab(ctk.CTkFrame):
    PAYMENT_METHODS = ["Cash", "Card", "Other"]

    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.items = []
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        self.discount_type = ctk.StringVar(value="percent")
        self._tax_caption_prefix = "Tax"

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=300)
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
        inner.pack(fill="x", padx=20, pady=16)

        T.section_title(inner, "Customer").pack(anchor="w", pady=(0, 12))

        fields = ctk.CTkFrame(inner, fg_color="transparent")
        fields.pack(fill="x")

        name_col = ctk.CTkFrame(fields, fg_color="transparent")
        name_col.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ctk.CTkLabel(name_col, text="Name  ·  Alt+C", **T.label_secondary()).pack(anchor="w")
        self.customer_name_entry = ctk.CTkEntry(name_col, placeholder_text="Customer name", **T.entry_kwargs())
        self.customer_name_entry.pack(fill="x", pady=(4, 0))

        phone_col = ctk.CTkFrame(fields, fg_color="transparent")
        phone_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(phone_col, text="Phone  ·  Alt+P", **T.label_secondary()).pack(anchor="w")
        self.customer_phone_entry = ctk.CTkEntry(phone_col, placeholder_text="(416) 555-0100", **T.entry_kwargs())
        self.customer_phone_entry.pack(fill="x", pady=(4, 0))

    def _build_main_area(self):
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 8), pady=4)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        add_card = ctk.CTkFrame(left, **T.card_kwargs())
        add_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        add_inner = ctk.CTkFrame(add_card, fg_color="transparent")
        add_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(add_inner, text="Stock search", font=T.FONT_MEDIUM, text_color=T.TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            add_inner,
            text="Type SKU or name · Enter adds selected item · Alt+S focuses search",
            **T.label_secondary(),
        ).pack(anchor="w", pady=(0, 10))

        row1 = ctk.CTkFrame(add_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        row1.grid_columnconfigure(1, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            row1, textvariable=self.search_var, placeholder_text="SKU…", **T.entry_compact(),
        )
        self.search_entry.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Return>", self.on_search_enter)
        self.search_entry.bind("<KP_Enter>", self.on_search_enter)

        self.search_results = ctk.CTkComboBox(row1, values=[], **T.combo_kwargs(720))
        self.search_results.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            row1,
            text=T.with_shortcut("Add", "Enter"),
            width=120,
            command=self.add_inventory_item,
            **T.primary_button_kwargs(height=38),
        ).grid(row=0, column=2, sticky="e")
        self.current_search_products = []

        row2 = ctk.CTkFrame(add_inner, fg_color="transparent")
        row2.pack(fill="x")
        ctk.CTkLabel(row2, text="Manual entry  ·  Alt+M", **T.label_secondary()).pack(side="left", padx=(0, 12))
        self.man_desc = ctk.CTkEntry(row2, placeholder_text="Description", **T.entry_kwargs(340))
        self.man_desc.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.man_qty = ctk.CTkEntry(row2, placeholder_text="Qty", width=64, height=36, fg_color=T.SURFACE_ALT, border_color=T.BORDER, corner_radius=T.RADIUS_SM)
        self.man_qty.insert(0, "1")
        self.man_qty.pack(side="left", padx=(0, 6))
        self.man_price = ctk.CTkEntry(row2, placeholder_text="Price", width=88, height=36, fg_color=T.SURFACE_ALT, border_color=T.BORDER, corner_radius=T.RADIUS_SM)
        self.man_price.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row2, text=T.with_shortcut("Add line", "Alt+A"), width=120, command=self.add_manual_item, **T.button_kwargs()).pack(side="left")

        lines_card = ctk.CTkFrame(left, **T.card_kwargs())
        lines_card.grid(row=1, column=0, sticky="nsew")
        lines_inner = ctk.CTkFrame(lines_card, fg_color="transparent")
        lines_inner.pack(fill="both", expand=True, padx=20, pady=16)
        lines_inner.grid_rowconfigure(1, weight=1)
        lines_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lines_inner, text="Line items", font=T.FONT_MEDIUM, text_color=T.TEXT).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.items_scroll = ctk.CTkScrollableFrame(lines_inner, fg_color=T.SURFACE_ALT, corner_radius=T.RADIUS_SM)
        self.items_scroll.grid(row=1, column=0, sticky="nsew")

        hdr = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(8, 4))
        for text, w in [("#", 28), ("Description", 200), ("S/N", 100), ("Qty", 40), ("Price", 72), ("Amount", 80)]:
            ctk.CTkLabel(hdr, text=text, width=w, **T.table_header_kwargs()).pack(side="left", padx=4)

        self.item_rows_frame = ctk.CTkFrame(self.items_scroll, fg_color="transparent")
        self.item_rows_frame.pack(fill="both", expand=True, padx=4, pady=(0, 8))

    def _build_sidebar(self):
        side = ctk.CTkFrame(self, fg_color="transparent", width=300)
        side.grid(row=1, column=1, sticky="nsew", padx=(0, 4), pady=4)
        side.grid_rowconfigure(0, weight=1)
        side.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(side, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")

        summary = ctk.CTkFrame(scroll, **T.card_kwargs())
        summary.pack(fill="x", pady=(0, 8))

        s_inner = ctk.CTkFrame(summary, fg_color="transparent")
        s_inner.pack(fill="x", padx=20, pady=20)

        T.section_title(s_inner, "Summary").pack(anchor="w", pady=(0, 16))

        self.subtotal_label = self._summary_row(s_inner, "Subtotal", "$0.00")
        self.discount_summary_label = self._summary_row(s_inner, "Discount", "−$0.00")
        self.tax_label = self._summary_row(s_inner, self._tax_caption(), "$0.00")

        ctk.CTkFrame(s_inner, fg_color=T.BORDER, height=1, corner_radius=0).pack(fill="x", pady=12)
        self.total_label = ctk.CTkLabel(s_inner, text="$0.00", font=T.FONT_LARGE, text_color=T.TEXT, anchor="e")
        ctk.CTkLabel(s_inner, text="Total", **T.label_secondary()).pack(anchor="w")
        self.total_label.pack(anchor="e", pady=(0, 4))

        discount_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        discount_card.pack(fill="x", pady=(0, 8))
        d_inner = ctk.CTkFrame(discount_card, fg_color="transparent")
        d_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(d_inner, text="Discount  ·  Alt+D", font=T.FONT_MEDIUM, text_color=T.TEXT).pack(anchor="w", pady=(0, 10))

        type_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        type_row.pack(fill="x", pady=(0, 8))
        ctk.CTkRadioButton(
            type_row, text="%", variable=self.discount_type, value="percent",
            command=self.refresh_items, font=T.FONT, text_color=T.TEXT,
            fg_color=T.ACCENT, border_color=T.BORDER,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            type_row, text="$", variable=self.discount_type, value="fixed",
            command=self.refresh_items, font=T.FONT, text_color=T.TEXT,
            fg_color=T.ACCENT, border_color=T.BORDER,
        ).pack(side="left")

        self.discount_entry = ctk.CTkEntry(d_inner, placeholder_text="0", **T.entry_kwargs())
        self.discount_entry.pack(fill="x")
        self.discount_entry.bind("<KeyRelease>", lambda e: self.refresh_items())

        pay_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        pay_card.pack(fill="x", pady=(0, 8))
        p_inner = ctk.CTkFrame(pay_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(p_inner, text="Payment  ·  F7 cycles", **T.label_secondary()).pack(anchor="w", pady=(0, 10))
        self.payment_var = ctk.StringVar(value="Cash")
        pay_row = ctk.CTkFrame(p_inner, fg_color="transparent")
        pay_row.pack(fill="x")
        for method in self.PAYMENT_METHODS:
            ctk.CTkRadioButton(
                pay_row, text=method, variable=self.payment_var, value=method,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
            ).pack(side="left", padx=(0, 12))

        notes_card = ctk.CTkFrame(scroll, **T.card_kwargs())
        notes_card.pack(fill="x", pady=(0, 8))
        n_inner = ctk.CTkFrame(notes_card, fg_color="transparent")
        n_inner.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(n_inner, text="Notes", **T.label_secondary()).pack(anchor="w")
        self.notes_entry = ctk.CTkEntry(n_inner, placeholder_text="Optional", **T.entry_kwargs())
        self.notes_entry.pack(fill="x", pady=(6, 0))

        self._build_action_dock()

    def _build_action_dock(self):
        """Pinned bottom bar so Save/Print are always visible."""
        dock = ctk.CTkFrame(self, **T.card_kwargs())
        dock.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))

        inner = ctk.CTkFrame(dock, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=12)

        ctk.CTkButton(
            inner,
            text=T.with_shortcut("Print & save", "F12"),
            command=lambda: self.save(print_rcpt=True),
            **T.primary_button_kwargs(width=180, height=42),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            inner,
            text=T.with_shortcut("Save", "F11"),
            command=lambda: self.save(print_rcpt=False),
            **T.button_kwargs(width=120, height=42),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            inner,
            text=T.with_shortcut("Clear", "F9"),
            command=self.clear_form,
            **T.button_kwargs(width=120, height=42),
        ).pack(side="left")

    def _tax_caption(self):
        return f"Tax ({int(self.tax_rate * 100)}%)"

    def _summary_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        title = ctk.CTkLabel(row, text=label, **T.label_secondary())
        title.pack(side="left")
        val = ctk.CTkLabel(row, text=value, font=T.FONT, text_color=T.TEXT, anchor="e")
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
        values = [
            f"{(p.sku or '—'):<10}  {p.name}  ·  {format_currency(p.price)}  ·  qty {p.qty}"
            for p in self.current_search_products
        ]
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
            return

        idx = 0
        selection = self.search_results.get()
        values = self.search_results.cget("values") or []
        if selection and selection in values:
            idx = values.index(selection)
        elif len(self.current_search_products) != 1:
            messagebox.showinfo("Select item", "Choose a product from the list, or narrow your SKU search.")
            return

        p = self.current_search_products[idx]
        if p.qty <= 0:
            messagebox.showwarning("Out of stock", f"'{p.name}' has no stock left.")
            return
        self.items.append(InvoiceItem(
            id=None, invoice_id=None, product_id=p.id,
            description=p.name, serial_number=p.serial_number or "",
            qty=1, unit_price=p.price, line_total=p.price,
        ))
        self.refresh_items()
        self.search_var.set("")
        self.search_results.configure(values=[])
        self.current_search_products = []

    def add_manual_item(self):
        desc = self.man_desc.get().strip()
        if not desc:
            messagebox.showerror("Missing description", "Enter a description for the line item.")
            self.man_desc.focus_set()
            return
        try:
            qty = int(self.man_qty.get().strip())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a positive whole number.")
            self.man_qty.focus_set()
            return
        try:
            price = float(self.man_price.get().strip())
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid price", "Enter a valid price.")
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

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_items()

    def refresh_items(self):
        for w in self.item_rows_frame.winfo_children():
            w.destroy()

        widths = [28, 200, 100, 40, 72, 80]
        for i, item in enumerate(self.items):
            row = ctk.CTkFrame(self.item_rows_frame, fg_color=T.SURFACE if i % 2 == 0 else "transparent", corner_radius=T.RADIUS_SM)
            row.pack(fill="x", pady=1)
            cells = [str(i + 1), item.description, item.serial_number or "—", str(item.qty),
                     format_currency(item.unit_price), format_currency(item.line_total)]
            for text, w in zip(cells, widths):
                ctk.CTkLabel(row, text=text, width=w, anchor="w", font=T.FONT, text_color=T.TEXT).pack(side="left", padx=4, pady=6)
            ctk.CTkButton(row, text="×", command=lambda idx=i: self.remove_item(idx), **T.danger_button_kwargs()).pack(side="right", padx=4)

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

    def save(self, print_rcpt=True):
        if not self.items:
            messagebox.showwarning("Empty invoice", "Add at least one line item before saving.")
            return

        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        dtype = self.discount_type.get()
        dval = self._get_discount_value()
        subtotal, discount_amount, tax_amount, total = compute_invoice_totals(self.items, self.tax_rate, dtype, dval)

        invoice = Invoice(
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

        try:
            save_invoice(invoice, self.items)
            msg = f"Saved {invoice.invoice_number}"
            if print_rcpt:
                from datetime import datetime
                invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                printed, print_msg = print_receipt(invoice, self.items)
                msg += " · Printed" if printed else " · Print failed"
                if not printed:
                    messagebox.showerror("Print failed", print_msg)
            self.winfo_toplevel().set_status(msg)
            self.clear_form()
            app = self.winfo_toplevel()
            if hasattr(app, "inventory_tab"):
                app.inventory_tab.load_products()
            if hasattr(app, "reports_tab"):
                app.reports_tab.load_invoices()
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def clear_form(self):
        self.customer_name_entry.delete(0, "end")
        self.customer_phone_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.discount_entry.delete(0, "end")
        self.discount_type.set("percent")
        self.items = []
        self.payment_var.set("Cash")
        self.refresh_items()
        self.focus_customer()
