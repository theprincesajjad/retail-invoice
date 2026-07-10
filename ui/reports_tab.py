import customtkinter as ctk
from tkinter import messagebox
from database import search_invoices
from utils import format_currency
from datetime import datetime, timedelta
import calendar
from . import theme as T
from .receipt_viewer import show_receipt_viewer


class ReportsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_filters()
        self.create_summary()
        self.create_table()

        self.period_var.set("Monthly")
        self.on_filter_change()

    def create_filters(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD + 4, pady=12)

        T.field_label(inner, "Period", "Alt+P").pack(side="left", padx=(0, 8))
        self.period_var = ctk.StringVar(value="Monthly")
        self.period_combo = ctk.CTkComboBox(
            inner, variable=self.period_var, values=["Monthly", "Quarterly", "Yearly"],
            command=self.on_filter_change, **T.combo_kwargs(130),
        )
        self.period_combo.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(inner, text="Range", **T.label_secondary()).pack(side="left", padx=(0, 8))
        self.range_var = ctk.StringVar()
        self.range_combo = ctk.CTkComboBox(
            inner, variable=self.range_var, values=[], command=self.load_invoices, **T.combo_kwargs(130),
        )
        self.range_combo.pack(side="left", padx=(0, 24))

        T.field_label(inner, "Search", "Alt+S").pack(side="left", padx=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner, textvariable=self.search_var,
            placeholder_text="Name, phone, or product…", **T.entry_kwargs(240),
        )
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_invoices())

        ctk.CTkButton(
            inner, text=T.with_shortcut("Refresh", "Alt+R"), command=self.load_invoices, **T.button_kwargs(width=120),
        ).pack(side="left")

    def create_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))

        self.total_sales_var = ctk.StringVar(value="$0.00")
        self.total_tax_var = ctk.StringVar(value="$0.00")
        self.invoice_count_var = ctk.StringVar(value="0")
        self.avg_invoice_var = ctk.StringVar(value="$0.00")

        for i, (title, var) in enumerate([
            ("Total sales", self.total_sales_var),
            ("Total tax", self.total_tax_var),
            ("Invoices", self.invoice_count_var),
            ("Average", self.avg_invoice_var),
        ]):
            box = ctk.CTkFrame(self.summary_frame, **T.card_kwargs())
            box.grid(row=0, column=i, padx=(0 if i == 0 else 6, 0), sticky="ew")
            self.summary_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(box, text=title, **T.label_secondary()).pack(padx=16, pady=(14, 0), anchor="w")
            ctk.CTkLabel(box, textvariable=var, font=T.FONT_HEADLINE, text_color=T.TEXT).pack(padx=16, pady=(4, 14), anchor="w")

    def create_table(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkScrollableFrame(card, fg_color=T.SURFACE, corner_radius=0)
        self.table_frame.grid(row=0, column=0, sticky="nsew")

        self.headers = ["Invoice", "Date", "Customer", "Phone", "Total", "Pay", "Actions"]
        self.widths = [110, 120, 140, 110, 88, 56, 200]

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
        if period == "Monthly":
            values = [(now - timedelta(days=30 * i)).strftime("%b %Y") for i in range(12)]
        elif period == "Quarterly":
            values = [f"Q{q} {year}" for q in range(1, 5)] + [f"Q{q} {year - 1}" for q in range(1, 5)]
        else:
            values = [str(year - i) for i in range(3)]
        self.range_combo.configure(values=values)
        self.range_var.set(values[0])
        self.load_invoices()

    def get_date_range(self):
        period = self.period_var.get()
        rng = self.range_var.get()
        start_date = end_date = None
        try:
            if period == "Monthly":
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

        for i, inv in enumerate(invoices):
            row = ctk.CTkFrame(
                self.rows_frame,
                fg_color=T.SURFACE_ALT if i % 2 == 0 else "transparent",
                corner_radius=T.RADIUS_SM,
            )
            row.pack(fill="x", pady=1)

            date_str = inv.created_at[:16] if inv.created_at else ""
            cells = [
                inv.invoice_number, date_str, inv.customer_name or "—", inv.customer_phone or "—",
                format_currency(inv.total), inv.payment_method,
            ]
            for text, width in zip(cells, self.widths[:-1]):
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=T.TEXT).pack(
                    side="left", padx=4, pady=8
                )

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[-1])
            actions.pack(side="left", padx=4)
            ctk.CTkButton(
                actions, text="View", width=52, command=lambda inv_obj=inv: self.view_invoice(inv_obj),
                **T.button_kwargs(height=30),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                actions, text="Print", width=52, command=lambda inv_obj=inv: self.reprint_invoice(inv_obj),
                **T.button_kwargs(height=30),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                actions, text="Email", width=52, command=lambda inv_obj=inv: self.email_invoice(inv_obj),
                **T.button_kwargs(height=30),
            ).pack(side="left", padx=2)

    def view_invoice(self, invoice):
        show_receipt_viewer(self.winfo_toplevel(), invoice, invoice.items)

    def reprint_invoice(self, invoice):
        from printer import print_receipt
        ok, msg = print_receipt(invoice, invoice.items)
        if ok:
            self.winfo_toplevel().set_status(f"Printed {invoice.invoice_number}")
        else:
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
            messagebox.showinfo("Email sent", msg)
        else:
            messagebox.showerror("Email failed", msg)
