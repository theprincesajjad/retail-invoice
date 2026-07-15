import customtkinter as ctk
from tkinter import messagebox
from database import search_invoices
from utils import format_currency
from datetime import datetime, timedelta
import calendar
from . import theme as T
from .receipt_viewer import show_receipt_viewer
from .toast import toast


class ReportsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_filters()
        self.create_summary()
        self.create_table()

        self.period_var.set("Today")
        self.on_filter_change()

    def create_filters(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=14)

        ctk.CTkButton(
            inner, text="Today", command=self._show_today, **T.primary_button_kwargs(width=100, height=T.BTN_HEIGHT),
        ).pack(side="left", padx=(0, 12))

        T.field_label(inner, "Time period").pack(side="left", padx=(0, 8))
        self.period_var = ctk.StringVar(value="Today")
        self.period_combo = ctk.CTkComboBox(
            inner, variable=self.period_var,
            values=["Today", "This week", "Monthly", "Quarterly", "Yearly"],
            command=self.on_filter_change, **T.combo_kwargs(140),
        )
        self.period_combo.pack(side="left", padx=(0, 16))

        T.field_label(inner, "Specific").pack(side="left", padx=(0, 8))
        self.range_var = ctk.StringVar()
        self.range_combo = ctk.CTkComboBox(
            inner, variable=self.range_var, values=[], command=self.load_invoices, **T.combo_kwargs(140),
        )
        self.range_combo.pack(side="left", padx=(0, 20))

        T.field_label(inner, "Search").pack(side="left", padx=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner, textvariable=self.search_var,
            placeholder_text="Customer name, phone, or product…", **T.entry_kwargs(260),
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_invoices())

        ctk.CTkButton(
            inner, text="Refresh", command=self.load_invoices, **T.button_kwargs(width=110),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            inner, text="Print inventory", command=self.print_inventory, **T.button_kwargs(width=150),
        ).pack(side="left")

    def _show_today(self):
        self.period_var.set("Today")
        self.on_filter_change()

    def print_inventory(self):
        from inventory_list import build_inventory_list_text
        from printer import print_inventory_list
        from .receipt_viewer import show_text_viewer

        text = build_inventory_list_text()
        # Preview first so shops without a printer can still review the list
        show_text_viewer(
            self.winfo_toplevel(),
            title="Inventory list",
            body=text,
            print_callback=print_inventory_list,
        )
    def create_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))

        self.total_sales_var = ctk.StringVar(value="$0.00")
        self.total_tax_var = ctk.StringVar(value="$0.00")
        self.invoice_count_var = ctk.StringVar(value="0")
        self.avg_invoice_var = ctk.StringVar(value="$0.00")

        summaries = [
            ("Money collected", self.total_sales_var, T.ACCENT_SOFT, T.ACCENT),
            ("Tax collected", self.total_tax_var, T.SUCCESS_SOFT, T.SUCCESS),
            ("Number of sales", self.invoice_count_var, T.WARNING_SOFT, T.WARNING),
            ("Average sale", self.avg_invoice_var, T.SURFACE, T.TEXT),
        ]
        for i, (title, var, bg, fg) in enumerate(summaries):
            box = ctk.CTkFrame(self.summary_frame, fg_color=bg, corner_radius=T.RADIUS_LG, border_width=0)
            box.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="ew")
            self.summary_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(box, text=title, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY).pack(
                padx=18, pady=(16, 0), anchor="w"
            )
            ctk.CTkLabel(box, textvariable=var, font=T.FONT_LARGE, text_color=fg).pack(
                padx=18, pady=(4, 16), anchor="w"
            )

    def create_table(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkScrollableFrame(card, fg_color=T.SURFACE, corner_radius=0)
        self.table_frame.grid(row=0, column=0, sticky="nsew")

        self.headers = ["Receipt #", "Date", "Customer", "Phone", "Total", "Payment", ""]
        self.widths = [120, 130, 150, 120, 100, 80, 240]

        header_frame = ctk.CTkFrame(self.table_frame, fg_color=T.SURFACE_ALT, corner_radius=0)
        header_frame.pack(fill="x", padx=12, pady=(12, 4))
        for text, width in zip(self.headers, self.widths):
            ctk.CTkLabel(header_frame, text=text, width=width, **T.table_header_kwargs()).pack(side="left", padx=4, pady=8)

        self.rows_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def on_filter_change(self, *args):
        period = self.period_var.get()
        now = datetime.now()
        year = now.year

        if period == "Today":
            self.range_combo.configure(values=["Today"])
            self.range_var.set("Today")
            self.range_combo.configure(state="disabled")
        elif period == "This week":
            self.range_combo.configure(state="normal")
            start = now - timedelta(days=now.weekday())
            values = []
            for i in range(8):
                d = start - timedelta(weeks=i)
                values.append(f"Week of {d.strftime('%b %d, %Y')}")
            self.range_combo.configure(values=values)
            self.range_var.set(values[0])
        elif period == "Monthly":
            self.range_combo.configure(state="normal")
            values = [(now - timedelta(days=30 * i)).strftime("%b %Y") for i in range(12)]
            self.range_combo.configure(values=values)
            self.range_var.set(values[0])
        elif period == "Quarterly":
            self.range_combo.configure(state="normal")
            values = [f"Q{q} {year}" for q in range(1, 5)] + [f"Q{q} {year - 1}" for q in range(1, 5)]
            self.range_combo.configure(values=values)
            self.range_var.set(values[0])
        else:
            self.range_combo.configure(state="normal")
            values = [str(year - i) for i in range(3)]
            self.range_combo.configure(values=values)
            self.range_var.set(values[0])

        self.load_invoices()

    def get_date_range(self):
        period = self.period_var.get()
        rng = self.range_var.get()
        start_date = end_date = None
        now = datetime.now()
        try:
            if period == "Today":
                start_date = now.strftime("%Y-%m-%d 00:00:00")
                end_date = now.strftime("%Y-%m-%d 23:59:59")
            elif period == "This week":
                week_start = datetime.strptime(rng.replace("Week of ", ""), "%b %d, %Y")
                week_end = week_start + timedelta(days=6)
                start_date = week_start.strftime("%Y-%m-%d 00:00:00")
                end_date = week_end.strftime("%Y-%m-%d 23:59:59")
            elif period == "Monthly":
                dt = datetime.strptime(rng, "%b %Y")
                start_date = dt.strftime("%Y-%m-01 00:00:00")
                _, last_day = calendar.monthrange(dt.year, dt.month)
                end_date = dt.strftime(f"%Y-%m-{last_day} 23:59:59")
            elif period == "Quarterly":
                q, y = rng.split()
                y = int(y)
                sm, em = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}[int(q[1])]
                start_date = f"{y}-{sm:02d}-01 00:00:00"
                _, ld = calendar.monthrange(y, em)
                end_date = f"{y}-{em:02d}-{ld} 23:59:59"
            elif period == "Yearly":
                start_date = f"{rng}-01-01 00:00:00"
                end_date = f"{rng}-12-31 23:59:59"
        except Exception:
            pass
        return start_date, end_date

    def load_invoices(self, *args):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        start_date, end_date = self.get_date_range()
        query = self.search_var.get().strip()
        invoices = search_invoices(query, start_date, end_date)

        total_sales = sum(inv.total for inv in invoices)
        total_tax = sum(inv.tax_amount for inv in invoices)
        count = len(invoices)
        avg = total_sales / count if count else 0

        self.total_sales_var.set(format_currency(total_sales))
        self.total_tax_var.set(format_currency(total_tax))
        self.invoice_count_var.set(str(count))
        self.avg_invoice_var.set(format_currency(avg))

        if not invoices:
            ctk.CTkLabel(
                self.rows_frame,
                text="No sales found for this period",
                font=T.FONT, text_color=T.TEXT_TERTIARY,
            ).pack(pady=40)
            return

        for i, inv in enumerate(invoices):
            row = ctk.CTkFrame(
                self.rows_frame,
                fg_color=T.SURFACE_ALT if i % 2 == 0 else "transparent",
                corner_radius=T.RADIUS_SM,
            )
            row.pack(fill="x", pady=1)

            date_str = inv.created_at[:16] if inv.created_at else ""
            cells = [
                inv.invoice_number, date_str, inv.customer_name or "Walk-in", inv.customer_phone or "—",
                format_currency(inv.total), inv.payment_method,
            ]
            for text, width in zip(cells, self.widths[:-1]):
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=T.TEXT).pack(
                    side="left", padx=4, pady=10
                )

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[-1])
            actions.pack(side="left", padx=4)
            ctk.CTkButton(
                actions, text="View", width=64, command=lambda inv_obj=inv: self.view_invoice(inv_obj),
                **T.button_kwargs(height=T.BTN_HEIGHT_SM),
            ).pack(side="left", padx=3)
            ctk.CTkButton(
                actions, text="Print", width=64, command=lambda inv_obj=inv: self.reprint_invoice(inv_obj),
                **T.button_kwargs(height=T.BTN_HEIGHT_SM),
            ).pack(side="left", padx=3)
            ctk.CTkButton(
                actions, text="Email", width=64, command=lambda inv_obj=inv: self.email_invoice(inv_obj),
                **T.button_kwargs(height=T.BTN_HEIGHT_SM),
            ).pack(side="left", padx=3)

    def view_invoice(self, invoice):
        show_receipt_viewer(self.winfo_toplevel(), invoice, invoice.items)

    def reprint_invoice(self, invoice):
        from printer import print_receipt
        ok, msg = print_receipt(invoice, invoice.items)
        if ok:
            self.winfo_toplevel().set_status(f"Printed {invoice.invoice_number}")
            toast(self, f"Printed {invoice.invoice_number}", kind="success")
        else:
            toast(self, msg, kind="error", title="Print failed")
            messagebox.showerror("Print failed", msg)

    def email_invoice(self, invoice):
        from email_service import send_receipt_email

        default = ""
        dialog = ctk.CTkInputDialog(
            text=f"Send receipt for {invoice.invoice_number} to:",
            title="Email receipt",
        )
        to_addr = dialog.get_input()
        if not to_addr:
            return
        ok, msg = send_receipt_email(to_addr, invoice, invoice.items)
        if ok:
            self.winfo_toplevel().set_status(msg)
            toast(self, msg, kind="success", title="Email sent")
        else:
            toast(self, msg, kind="error", title="Email failed")
            messagebox.showerror("Email failed", msg)
