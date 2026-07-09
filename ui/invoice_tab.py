import customtkinter as ctk
from tkinter import messagebox
from database import search_products, generate_invoice_number, save_invoice, get_setting
from models import Invoice, InvoiceItem
from printer import print_receipt
from utils import format_currency
from . import theme as T


class InvoiceTab(ctk.CTkFrame):
    PAYMENT_METHODS = ["Cash", "Card", "Other"]

    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.items = []
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        self.payment_radios = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_items_list_section()
        self.create_customer_section()
        self.create_item_entry_section()
        self.create_bottom_section()

        self._bind_manual_enter_keys()

    def create_items_list_section(self):
        panel = ctk.CTkFrame(self, **T.panel_kwargs())
        panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))

        self.items_frame = ctk.CTkScrollableFrame(panel, fg_color=T.BG, corner_radius=0)
        self.items_frame.pack(fill="both", expand=True, padx=4, pady=4)

        headers = ["Line", "Qty", "Description", "S/N", "Price", "Amount", ""]
        widths = [40, 45, 260, 130, 90, 100, 50]

        header_frame = ctk.CTkFrame(self.items_frame, fg_color=T.HEADER_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 4))

        for text, width in zip(headers, widths):
            ctk.CTkLabel(header_frame, text=text, width=width, anchor="w", font=T.FONT_HEADER, text_color=T.HEADER_TEXT).pack(
                side="left", padx=4, pady=3
            )

        self.item_rows_frame = ctk.CTkFrame(self.items_frame, fg_color="transparent")
        self.item_rows_frame.pack(fill="both", expand=True)

    def create_customer_section(self):
        frame = ctk.CTkFrame(self, **T.panel_kwargs())
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        ctk.CTkLabel(frame, text="Customer (Alt+C):", **T.label_kwargs(text_color=T.LABEL_ACCENT)).pack(side="left", padx=8, pady=6)
        self.customer_name_entry = ctk.CTkEntry(frame, **T.entry_kwargs(220))
        self.customer_name_entry.pack(side="left", padx=4, pady=6)

        ctk.CTkLabel(frame, text="Phone (Alt+P):", **T.label_kwargs(text_color=T.LABEL_ACCENT)).pack(side="left", padx=(16, 4), pady=6)
        self.customer_phone_entry = ctk.CTkEntry(frame, **T.entry_kwargs(150))
        self.customer_phone_entry.pack(side="left", padx=4, pady=6)

    def create_item_entry_section(self):
        frame = ctk.CTkFrame(self, **T.panel_kwargs())
        frame.grid(row=2, column=0, sticky="ew", padx=8, pady=4)

        ctk.CTkLabel(frame, text="Stock Search (Alt+S):", **T.label_kwargs(text_color=T.LABEL_ACCENT)).pack(side="left", padx=8, pady=6)
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(frame, textvariable=self.search_var, placeholder_text="Name or Serial", **T.entry_kwargs(180))
        self.search_entry.pack(side="left", padx=4, pady=6)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.search_results = ctk.CTkComboBox(frame, values=[], **T.combo_kwargs(260))
        self.search_results.pack(side="left", padx=4, pady=6)

        ctk.CTkButton(frame, text="Add Stock", command=self.add_inventory_item, width=90, **T.button_kwargs()).pack(
            side="left", padx=8, pady=6
        )

        self.current_search_products = []

    def create_bottom_section(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        bottom.grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 8))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=2)

        manual_panel = ctk.CTkFrame(bottom, **T.panel_kwargs())
        manual_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        enter_hdr = ctk.CTkFrame(manual_panel, fg_color=T.INPUT_BG, corner_radius=0)
        enter_hdr.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(enter_hdr, text="Enter", font=T.FONT_BOLD, text_color=T.INPUT_TEXT).pack(padx=8, pady=4, anchor="w")

        fields = ctk.CTkFrame(manual_panel, fg_color="transparent")
        fields.pack(fill="x", padx=6, pady=6)

        ctk.CTkLabel(fields, text="Description (Alt+M):", **T.label_kwargs(text_color=T.LABEL_ACCENT)).grid(row=0, column=0, sticky="w", pady=4)
        self.man_desc = ctk.CTkEntry(fields, placeholder_text="Item description", **T.entry_kwargs(220))
        self.man_desc.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(fields, text="Quantity:", **T.label_kwargs()).grid(row=1, column=0, sticky="w", pady=4)
        self.man_qty = ctk.CTkEntry(fields, **T.entry_kwargs(80))
        self.man_qty.insert(0, "1")
        self.man_qty.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(fields, text="Price:", **T.label_kwargs()).grid(row=2, column=0, sticky="w", pady=4)
        self.man_price = ctk.CTkEntry(fields, placeholder_text="0.00", **T.entry_kwargs(100))
        self.man_price.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkButton(
            fields,
            text="Add Line (Enter / Alt+A)",
            command=self.add_manual_item,
            width=180,
            **T.primary_button_kwargs(),
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))

        right_panel = ctk.CTkFrame(bottom, **T.panel_kwargs())
        right_panel.grid(row=0, column=1, sticky="nsew")

        totals_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        totals_frame.pack(fill="x", padx=12, pady=(12, 6))

        self.subtotal_label = ctk.CTkLabel(totals_frame, text="Sub Total: $0.00", font=T.FONT_BOLD, text_color=T.TEXT, anchor="e")
        self.subtotal_label.pack(fill="x", pady=2)
        tax_pct = int(self.tax_rate * 100)
        self.tax_label = ctk.CTkLabel(totals_frame, text=f"Tax ({tax_pct}%): $0.00", font=T.FONT_BOLD, text_color=T.TEXT, anchor="e")
        self.tax_label.pack(fill="x", pady=2)
        self.total_label = ctk.CTkLabel(totals_frame, text="Total: $0.00", font=T.FONT_TOTAL, text_color=T.LABEL_ACCENT, anchor="e")
        self.total_label.pack(fill="x", pady=6)

        pay_frame = ctk.CTkFrame(right_panel, fg_color=T.INPUT_BG, corner_radius=0)
        pay_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(pay_frame, text="Payment (F7):", font=T.FONT_BOLD, text_color=T.INPUT_TEXT).pack(anchor="w", padx=8, pady=(6, 2))

        radio_row = ctk.CTkFrame(pay_frame, fg_color="transparent")
        radio_row.pack(fill="x", padx=8, pady=(0, 8))
        self.payment_var = ctk.StringVar(value="Cash")
        for i, method in enumerate(self.PAYMENT_METHODS):
            rb = ctk.CTkRadioButton(
                radio_row,
                text=method,
                variable=self.payment_var,
                value=method,
                text_color=T.INPUT_TEXT,
                fg_color=T.HEADER_BG,
                hover_color=T.LABEL_ACCENT,
                border_color=T.BORDER,
                font=T.FONT,
            )
            rb.pack(side="left", padx=8)
            self.payment_radios[method] = rb

        self.payment_status = ctk.CTkLabel(right_panel, text="Payment: Cash", font=T.FONT, text_color=T.LABEL_ACCENT)
        self.payment_status.pack(anchor="e", padx=12, pady=(0, 4))

        ctk.CTkLabel(right_panel, text="Press [F12] to total & print", font=T.FONT_SMALL, text_color=T.TEXT).pack(anchor="e", padx=12)

        notes_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        notes_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(notes_frame, text="Notes:", **T.label_kwargs()).pack(anchor="w")
        self.notes_entry = ctk.CTkEntry(notes_frame, **T.entry_kwargs(280))
        self.notes_entry.pack(fill="x", pady=4)

        actions = ctk.CTkFrame(right_panel, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(actions, text="Print & Save (F12)", command=lambda: self.save(print_rcpt=True), **T.primary_button_kwargs()).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(actions, text="Save (F11)", command=lambda: self.save(print_rcpt=False), **T.button_kwargs()).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Clear (F9)", command=self.clear_form, **T.danger_button_kwargs()).pack(side="left", padx=6)

    def _bind_manual_enter_keys(self):
        self.man_desc.bind("<Return>", self._on_manual_desc_enter)
        self.man_desc.bind("<KP_Enter>", self._on_manual_desc_enter)
        self.man_qty.bind("<Return>", self._on_manual_qty_enter)
        self.man_qty.bind("<KP_Enter>", self._on_manual_qty_enter)
        self.man_price.bind("<Return>", self._on_manual_price_enter)
        self.man_price.bind("<KP_Enter>", self._on_manual_price_enter)

    def _on_manual_desc_enter(self, event=None):
        self.man_qty.focus_set()
        return "break"

    def _on_manual_qty_enter(self, event=None):
        self.man_price.focus_set()
        return "break"

    def _on_manual_price_enter(self, event=None):
        self.add_manual_item()
        return "break"

    def cycle_payment_method(self):
        current = self.payment_var.get()
        idx = self.PAYMENT_METHODS.index(current) if current in self.PAYMENT_METHODS else 0
        next_method = self.PAYMENT_METHODS[(idx + 1) % len(self.PAYMENT_METHODS)]
        self.payment_var.set(next_method)
        self._update_payment_status()
        self.winfo_toplevel().set_status(f"Payment method: {next_method}")

    def _update_payment_status(self):
        method = self.payment_var.get()
        self.payment_status.configure(text=f"Payment: {method}")

    def on_search(self, event):
        query = self.search_var.get().strip()
        if len(query) < 2:
            self.search_results.configure(values=[])
            self.current_search_products = []
            return

        products = search_products(query)
        self.current_search_products = products

        values = []
        for p in products:
            sn_text = f" S/N:{p.serial_number}" if p.serial_number else ""
            values.append(f"{p.name}{sn_text} ${p.price:.2f} [{p.qty}]")

        self.search_results.configure(values=values)
        if values:
            self.search_results.set(values[0])

    def add_inventory_item(self):
        selection = self.search_results.get()
        if not selection:
            return

        idx = self.search_results._values.index(selection) if selection in self.search_results._values else -1
        if idx >= 0 and idx < len(self.current_search_products):
            p = self.current_search_products[idx]

            if p.qty <= 0:
                messagebox.showwarning("Out of Stock", f"Product '{p.name}' is out of stock.")
                return

            item = InvoiceItem(
                id=None,
                invoice_id=None,
                product_id=p.id,
                description=p.name,
                serial_number=p.serial_number or "",
                qty=1,
                unit_price=p.price,
                line_total=p.price,
            )
            self.items.append(item)
            self.refresh_items()

            self.search_var.set("")
            self.search_results.set("")
            self.search_results.configure(values=[])
            self.current_search_products = []
            self.man_desc.focus_set()

    def add_manual_item(self):
        desc = self.man_desc.get().strip()
        qty_str = self.man_qty.get().strip()
        price_str = self.man_price.get().strip()

        if not desc:
            messagebox.showerror("Error", "Description is required.")
            self.man_desc.focus_set()
            return

        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer.")
            self.man_qty.focus_set()
            return

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Price must be a valid number.")
            self.man_price.focus_set()
            return

        item = InvoiceItem(
            id=None,
            invoice_id=None,
            product_id=None,
            description=desc,
            serial_number="",
            qty=qty,
            unit_price=price,
            line_total=qty * price,
        )
        self.items.append(item)
        self.refresh_items()

        self.man_desc.delete(0, "end")
        self.man_qty.delete(0, "end")
        self.man_qty.insert(0, "1")
        self.man_price.delete(0, "end")
        self.man_desc.focus_set()
        self.winfo_toplevel().set_status(f"Added: {desc}")

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_items()

    def refresh_items(self):
        for widget in self.item_rows_frame.winfo_children():
            widget.destroy()

        widths = [40, 45, 260, 130, 90, 100, 50]
        subtotal = 0.0

        for i, item in enumerate(self.items):
            row_frame = ctk.CTkFrame(self.item_rows_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)

            ctk.CTkLabel(row_frame, text=str(i + 1), width=widths[0], anchor="w", **T.label_kwargs()).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=str(item.qty), width=widths[1], anchor="w", **T.label_kwargs()).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=item.description, width=widths[2], anchor="w", **T.label_kwargs()).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=item.serial_number or "-", width=widths[3], anchor="w", **T.label_kwargs()).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=format_currency(item.unit_price), width=widths[4], anchor="w", **T.label_kwargs()).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=format_currency(item.line_total), width=widths[5], anchor="w", font=T.FONT_BOLD, text_color=T.LABEL_ACCENT).pack(
                side="left", padx=4
            )
            ctk.CTkButton(row_frame, text="X", width=widths[6], command=lambda idx=i: self.remove_item(idx), **T.danger_button_kwargs()).pack(
                side="left", padx=4
            )

            subtotal += item.line_total

        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        tax_amount = subtotal * self.tax_rate
        total = subtotal + tax_amount
        tax_pct = int(self.tax_rate * 100)

        self.subtotal_label.configure(text=f"Sub Total: {format_currency(subtotal)}")
        self.tax_label.configure(text=f"Tax ({tax_pct}%): {format_currency(tax_amount)}")
        self.total_label.configure(text=f"Total: {format_currency(total)}")

    def save(self, print_rcpt=True):
        if not self.items:
            messagebox.showwarning("Warning", "Cannot save an empty invoice.")
            return

        subtotal = sum(item.line_total for item in self.items)
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        tax_amount = subtotal * self.tax_rate
        total = subtotal + tax_amount

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
        )

        try:
            save_invoice(invoice, self.items)
            msg = f"Invoice {invoice.invoice_number} saved!"

            if print_rcpt:
                from datetime import datetime

                invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if print_receipt(invoice, self.items):
                    msg += " Printed."
                else:
                    msg += " Print failed - check settings."

            self.winfo_toplevel().set_status(msg)
            self.clear_form()

            app = self.winfo_toplevel()
            if hasattr(app, "inventory_tab"):
                app.inventory_tab.load_products()
            if hasattr(app, "reports_tab"):
                app.reports_tab.load_invoices()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save invoice: {str(e)}")

    def clear_form(self):
        self.customer_name_entry.delete(0, "end")
        self.customer_phone_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.items = []
        self.payment_var.set("Cash")
        self._update_payment_status()
        self.refresh_items()
        self.man_desc.focus_set()
