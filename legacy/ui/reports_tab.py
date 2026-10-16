import customtkinter as ctk
from tkinter import messagebox, filedialog
from database import search_invoices
from utils import (
    current_quarter_label,
    format_currency,
    parse_report_date,
    quarter_date_range,
)
from datetime import datetime, timedelta
import calendar
from pathlib import Path
from . import theme as T
from .receipt_viewer import show_receipt_viewer
from .toast import toast


class ReportsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._current_invoices = []
        self._totals_visible = False  # privacy: hide period totals until asked

        self.create_filters()
        self.create_summary()
        self.create_table()
        self._apply_totals_visibility()

        self.period_var.set("Today")
        self.on_filter_change()

    def create_filters(self):
        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=T.PAD_CARD, pady=(14, 6))

        ctk.CTkButton(
            top, text="Today", command=self._show_today, **T.primary_button_kwargs(width=100, height=T.BTN_HEIGHT),
        ).pack(side="left", padx=(0, 12))

        T.field_label(top, "Time period").pack(side="left", padx=(0, 8))
        self.period_var = ctk.StringVar(value="Today")
        self.period_combo = ctk.CTkComboBox(
            top, variable=self.period_var,
            values=["Today", "This week", "Monthly", "Quarterly", "Yearly", "Custom dates"],
            command=self.on_filter_change, **T.combo_kwargs(140),
        )
        self.period_combo.pack(side="left", padx=(0, 16))

        T.field_label(top, "Specific").pack(side="left", padx=(0, 8))
        self.range_var = ctk.StringVar()
        self.range_combo = ctk.CTkComboBox(
            top, variable=self.range_var, values=[], command=self._on_range_change, **T.combo_kwargs(140),
        )
        self.range_combo.pack(side="left", padx=(0, 20))

        T.field_label(top, "Search").pack(side="left", padx=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            top, textvariable=self.search_var,
            placeholder_text="Customer, phone, product, or SKU…", **T.entry_kwargs(220),
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_invoices())

        ctk.CTkButton(
            top, text="Refresh", command=self.load_invoices, **T.button_kwargs(width=100),
        ).pack(side="left")

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=T.PAD_CARD, pady=(0, 14))

        T.field_label(bottom, "From").pack(side="left", padx=(0, 8))
        self.from_date_var = ctk.StringVar()
        self.from_date_entry = ctk.CTkEntry(
            bottom, textvariable=self.from_date_var,
            placeholder_text="YYYY-MM-DD", **T.entry_kwargs(120),
        )
        self.from_date_entry.pack(side="left", padx=(0, 16))
        self.from_date_entry.bind("<Return>", lambda e: self._apply_custom_dates())

        T.field_label(bottom, "To").pack(side="left", padx=(0, 8))
        self.to_date_var = ctk.StringVar()
        self.to_date_entry = ctk.CTkEntry(
            bottom, textvariable=self.to_date_var,
            placeholder_text="YYYY-MM-DD", **T.entry_kwargs(120),
        )
        self.to_date_entry.pack(side="left", padx=(0, 12))
        self.to_date_entry.bind("<Return>", lambda e: self._apply_custom_dates())

        ctk.CTkButton(
            bottom, text="Apply dates", command=self._apply_custom_dates, **T.button_kwargs(width=110),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            bottom, text="Export PDF", command=self.export_report_pdf, **T.primary_button_kwargs(width=120),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            bottom, text="Monthly totals", command=self.export_monthly_totals_pdf, **T.button_kwargs(width=130),
        ).pack(side="left", padx=(0, 8))
        self.totals_toggle_btn = ctk.CTkButton(
            bottom, text="Show totals", command=self.toggle_totals, **T.button_kwargs(width=120),
        )
        self.totals_toggle_btn.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            bottom,
            text="Presets or Apply dates set the range for list + Export PDF / Monthly totals.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_TERTIARY,
        ).pack(side="left")

    def _show_today(self):
        self.period_var.set("Today")
        self.on_filter_change()

    def _apply_custom_dates(self):
        self.period_var.set("Custom dates")
        self.range_combo.configure(state="disabled")
        self.range_combo.configure(values=["Custom"])
        self.range_var.set("Custom")
        self.load_invoices()

    def _on_range_change(self, *_args):
        """Specific preset changed — refresh From/To then reload."""
        if self.period_var.get() != "Custom dates":
            start_date, end_date = self._date_range_from_period()
            if start_date and end_date:
                self.from_date_var.set(start_date[:10])
                self.to_date_var.set(end_date[:10])
        self.load_invoices()

    def toggle_totals(self):
        """Show or hide period summary totals (privacy when browsing with a customer)."""
        self._totals_visible = not self._totals_visible
        if self._totals_visible:
            self._refresh_summary_values()
        self._apply_totals_visibility()

    def _summary_grid_kwargs(self):
        return dict(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))

    def _apply_totals_visibility(self):
        if not hasattr(self, "summary_frame"):
            return
        if self._totals_visible:
            # Always re-pass grid options — bare grid() after grid_remove can leave a zero-height strip
            self.summary_frame.grid(**self._summary_grid_kwargs())
            if hasattr(self, "totals_toggle_btn"):
                self.totals_toggle_btn.configure(text="Hide totals")
            try:
                self.summary_frame.update_idletasks()
                self.update_idletasks()
            except Exception:
                pass
        else:
            self.summary_frame.grid_remove()
            if hasattr(self, "totals_toggle_btn"):
                self.totals_toggle_btn.configure(text="Show totals")

    def _refresh_summary_values(self):
        active = [
            inv for inv in self._current_invoices
            if not int(getattr(inv, "voided", 0) or 0)
        ]
        total_sales = sum(float(inv.total or 0) for inv in active)
        total_tax = sum(float(inv.tax_amount or 0) for inv in active)
        count = len(active)
        avg = total_sales / count if count else 0
        self.total_sales_var.set(format_currency(total_sales))
        self.total_tax_var.set(format_currency(total_tax))
        self.invoice_count_var.set(str(count))
        self.avg_invoice_var.set(format_currency(avg))

    def create_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(**self._summary_grid_kwargs())

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
            box.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="nsew")
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
        self.widths = [110, 120, 120, 95, 90, 80, 360]

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
            # Default to the current quarter (not always Q1)
            self.range_var.set(current_quarter_label(now))
        elif period == "Custom dates":
            self.range_combo.configure(state="disabled")
            self.range_combo.configure(values=["Custom"])
            self.range_var.set("Custom")
            if not self.from_date_var.get().strip():
                self.from_date_var.set(now.replace(day=1).strftime("%Y-%m-%d"))
            if not self.to_date_var.get().strip():
                self.to_date_var.set(now.strftime("%Y-%m-%d"))
        else:
            self.range_combo.configure(state="normal")
            values = [str(year - i) for i in range(3)]
            self.range_combo.configure(values=values)
            self.range_var.set(values[0])

        # Keep From/To in sync with presets so exports always match what you see
        if period != "Custom dates":
            start_date, end_date = self._date_range_from_period()
            if start_date and end_date:
                self.from_date_var.set(start_date[:10])
                self.to_date_var.set(end_date[:10])

        self.load_invoices()

    @staticmethod
    def _parse_user_date(raw: str, *, end_of_day: bool = False) -> str | None:
        return parse_report_date(raw, end_of_day=end_of_day)

    def _normalize_range(self, start_date: str, end_date: str) -> tuple[str, str]:
        if start_date[:10] > end_date[:10]:
            start_d = datetime.strptime(end_date[:10], "%Y-%m-%d")
            end_d = datetime.strptime(start_date[:10], "%Y-%m-%d")
            start_date = start_d.strftime("%Y-%m-%d 00:00:00")
            end_date = end_d.strftime("%Y-%m-%d 23:59:59")
        return start_date, end_date

    def _date_range_from_period(self):
        """Compute start/end from Time period + Specific (ignores From/To fields)."""
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
                start_date, end_date = quarter_date_range(rng)
            elif period == "Yearly":
                start_date = f"{rng}-01-01 00:00:00"
                end_date = f"{rng}-12-31 23:59:59"
            elif period == "Custom dates":
                start_date = parse_report_date(self.from_date_var.get(), end_of_day=False)
                end_date = parse_report_date(self.to_date_var.get(), end_of_day=True)
        except Exception:
            return None, None
        if start_date and end_date:
            return self._normalize_range(start_date, end_date)
        return start_date, end_date

    def get_date_range(self):
        """
        Active filter range for the list and PDF exports.

        Time period presets (Today / Monthly / Quarterly / …) drive the range
        from Specific. Custom dates / Apply dates use the From/To fields so
        multi-month manual ranges still work for Export PDF and Monthly totals.
        """
        period = self.period_var.get()
        if period == "Custom dates":
            start_date = parse_report_date(self.from_date_var.get(), end_of_day=False)
            end_date = parse_report_date(self.to_date_var.get(), end_of_day=True)
            if start_date and end_date:
                return self._normalize_range(start_date, end_date)
            return None, None
        start_date, end_date = self._date_range_from_period()
        if start_date and end_date:
            return start_date, end_date
        # Fallback if Specific failed to parse — still honor typed From/To
        start_date = parse_report_date(self.from_date_var.get(), end_of_day=False)
        end_date = parse_report_date(self.to_date_var.get(), end_of_day=True)
        if start_date and end_date:
            return self._normalize_range(start_date, end_date)
        return None, None

    def _period_label(self) -> str:
        start_date, end_date = self.get_date_range()
        if start_date and end_date:
            return f"{start_date[:10]} to {end_date[:10]}"
        period = self.period_var.get()
        rng = self.range_var.get()
        if period == "Today":
            return "Today"
        return f"{period}: {rng}" if rng else period

    def load_invoices(self, *args):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        start_date, end_date = self.get_date_range()
        if not start_date or not end_date:
            ctk.CTkLabel(
                self.rows_frame,
                text="Enter valid From and To dates (YYYY-MM-DD), then Apply dates.",
                font=T.FONT, text_color=T.TEXT_TERTIARY,
            ).pack(pady=40)
            self._current_invoices = []
            self._refresh_summary_values()
            return

        query = self.search_var.get().strip()
        try:
            # Headers only — loading every line item for long ranges made exports hang
            invoices = search_invoices(query, start_date, end_date, include_items=False)
        except Exception as e:
            self._current_invoices = []
            self._refresh_summary_values()
            toast(self, str(e), kind="error", title="Could not load sales")
            ctk.CTkLabel(
                self.rows_frame,
                text=f"Could not load sales: {e}",
                font=T.FONT, text_color=T.DANGER,
            ).pack(pady=40)
            return
        self._current_invoices = invoices
        self._refresh_summary_values()

        if not invoices:
            ctk.CTkLabel(
                self.rows_frame,
                text="No sales found for this period",
                font=T.FONT, text_color=T.TEXT_TERTIARY,
            ).pack(pady=40)
            return

        for i, inv in enumerate(invoices):
            is_voided = bool(int(getattr(inv, "voided", 0) or 0))
            row = ctk.CTkFrame(
                self.rows_frame,
                fg_color=T.DANGER_SOFT if is_voided else (T.SURFACE_ALT if i % 2 == 0 else "transparent"),
                corner_radius=T.RADIUS_SM,
            )
            row.pack(fill="x", pady=1)

            date_str = inv.created_at[:16] if inv.created_at else ""
            receipt_label = f"{inv.invoice_number}  VOID" if is_voided else inv.invoice_number
            payment_label = "Voided" if is_voided else (inv.payment_method or "—")
            cells = [
                receipt_label, date_str, inv.customer_name or "Walk-in", inv.customer_phone or "—",
                format_currency(inv.total), payment_label,
            ]
            text_color = T.DANGER if is_voided else T.TEXT
            for text, width in zip(cells, self.widths[:-1]):
                ctk.CTkLabel(row, text=text, width=width, anchor="w", font=T.FONT, text_color=text_color).pack(
                    side="left", padx=4, pady=10
                )

            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[-1])
            actions.pack(side="left", padx=4)
            if not is_voided:
                ctk.CTkButton(
                    actions, text="Edit", width=58, command=lambda inv_obj=inv: self.edit_invoice(inv_obj),
                    **T.primary_button_kwargs(height=T.BTN_HEIGHT_SM),
                ).pack(side="left", padx=3)
            ctk.CTkButton(
                actions, text="View", width=58, command=lambda inv_obj=inv: self.view_invoice(inv_obj),
                **T.button_kwargs(height=T.BTN_HEIGHT_SM),
            ).pack(side="left", padx=3)
            if not is_voided:
                ctk.CTkButton(
                    actions, text="Print", width=58, command=lambda inv_obj=inv: self.reprint_invoice(inv_obj),
                    **T.button_kwargs(height=T.BTN_HEIGHT_SM),
                ).pack(side="left", padx=3)
                ctk.CTkButton(
                    actions, text="Email", width=58, command=lambda inv_obj=inv: self.email_invoice(inv_obj),
                    **T.button_kwargs(height=T.BTN_HEIGHT_SM),
                ).pack(side="left", padx=3)
                ctk.CTkButton(
                    actions, text="Void", command=lambda inv_obj=inv: self.void_invoice(inv_obj),
                    **T.danger_button_kwargs(width=58, height=T.BTN_HEIGHT_SM),
                ).pack(side="left", padx=3)

    def edit_invoice(self, invoice):
        if int(getattr(invoice, "voided", 0) or 0):
            toast(self, "Voided sales cannot be edited.", kind="warning")
            return
        app = self.winfo_toplevel()
        if not hasattr(app, "invoice_tab"):
            return
        from database import get_invoice_by_id
        fresh = get_invoice_by_id(invoice.id) if invoice.id else invoice
        if not fresh:
            toast(self, "Could not load that sale.", kind="error")
            return
        if int(getattr(fresh, "voided", 0) or 0):
            toast(self, "Voided sales cannot be edited.", kind="warning")
            self.load_invoices()
            return
        app.tabview.set("New Sale")
        if hasattr(app, "_on_tab_change"):
            app._on_tab_change()
        app.invoice_tab.load_invoice_for_edit(fresh)

    def void_invoice(self, invoice):
        if int(getattr(invoice, "voided", 0) or 0):
            toast(self, "This sale is already voided.", kind="info")
            return
        from .dialogs import ask_yes_no
        from database import void_invoice as db_void_invoice

        confirmed = ask_yes_no(
            self.winfo_toplevel(),
            f"Void {invoice.invoice_number}?",
            (
                f"Customer: {invoice.customer_name or 'Walk-in'}\n"
                f"Total: {format_currency(invoice.total)}\n\n"
                "This permanently voids the sale and puts inventory back in stock.\n"
                "It will no longer count in sales totals.\n\n"
                "This cannot be undone."
            ),
            confirm_label="Void this sale",
            cancel_label="Keep sale",
            destructive=True,
        )
        if not confirmed:
            return

        # Second confirmation — requires typing the receipt number
        dialog = ctk.CTkInputDialog(
            text=(
                f"Type {invoice.invoice_number} to confirm voiding this sale.\n"
                "Inventory will be restocked."
            ),
            title="Confirm void",
        )
        typed = (dialog.get_input() or "").strip()
        if typed != invoice.invoice_number:
            if typed:
                toast(self, "Receipt number did not match — sale was not voided.", kind="warning")
            return

        try:
            db_void_invoice(invoice.id)
            try:
                from inventory_excel_sync import try_auto_export_inventory_excel
                try_auto_export_inventory_excel()
            except Exception:
                pass
            self.winfo_toplevel().set_status(f"Voided {invoice.invoice_number}")
            toast(self, f"Voided {invoice.invoice_number} — stock restored", kind="success", title="Sale voided")
            app = self.winfo_toplevel()
            if hasattr(app, "inventory_tab"):
                app.inventory_tab.load_products()
            self.load_invoices()
        except Exception as e:
            toast(self, str(e), kind="error", title="Could not void sale")
            messagebox.showerror("Void failed", str(e))

    def _active_invoices_for_export(self):
        """Re-query the active From/To range so exports match the list."""
        start_date, end_date = self.get_date_range()
        if not start_date or not end_date:
            return [], start_date, end_date
        query = self.search_var.get().strip()
        # PDF exports only need invoice headers (totals / dates) — skip line items
        invoices = search_invoices(query, start_date, end_date, include_items=False)
        active = [
            inv for inv in invoices
            if not int(getattr(inv, "voided", 0) or 0)
        ]
        self._current_invoices = invoices
        self._refresh_summary_values()
        return active, start_date, end_date

    def _ask_pdf_path(self, title: str, default_name: str) -> str | None:
        root = self.winfo_toplevel()
        # Keep the save dialog above the CustomTkinter window (otherwise it can
        # open behind the app and look like Export / Monthly totals "does nothing").
        try:
            root.lift()
            root.focus_force()
            root.attributes("-topmost", True)
            root.update_idletasks()
            root.after(150, lambda: root.attributes("-topmost", False))
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            parent=root,
            title=title,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return None
        if not str(path).lower().endswith(".pdf"):
            path = f"{path}.pdf"
        return path

    def export_report_pdf(self):
        try:
            invoices, start_date, end_date = self._active_invoices_for_export()
        except Exception as e:
            toast(self, str(e), kind="error", title="PDF export failed")
            messagebox.showerror("PDF export failed", str(e))
            return
        if not start_date or not end_date:
            toast(self, "Choose a time period or set valid From/To dates first.", kind="warning")
            messagebox.showwarning(
                "Choose a date range",
                "Select Today / Monthly / Quarterly (or enter From/To and Apply dates), then try Export PDF again.",
            )
            return
        if not invoices:
            label = self._period_label()
            toast(self, f"No sales for {label}.", kind="warning")
            messagebox.showwarning(
                "Nothing to export",
                f"No sales found for {label}.\n\nPick a Specific quarter/month that has sales, or widen From/To.",
            )
            return
        period = self._period_label()
        stamp = datetime.now().strftime("%Y%m%d")
        path = self._ask_pdf_path("Save sales report PDF", f"sales-report-{stamp}.pdf")
        if not path:
            return
        try:
            from sales_report_pdf import build_sales_report_pdf
            pdf_bytes = build_sales_report_pdf(
                invoices,
                period_label=period,
                start_date=start_date,
                end_date=end_date,
            )
            Path(path).write_bytes(pdf_bytes)
            self.winfo_toplevel().set_status(f"Saved report — {Path(path).name}")
            toast(self, f"Saved {Path(path).name}", kind="success", title="Sales report PDF")
        except Exception as e:
            toast(self, str(e), kind="error", title="PDF export failed")
            messagebox.showerror("PDF export failed", str(e))

    def export_monthly_totals_pdf(self):
        try:
            invoices, start_date, end_date = self._active_invoices_for_export()
        except Exception as e:
            toast(self, str(e), kind="error", title="PDF export failed")
            messagebox.showerror("PDF export failed", str(e))
            return
        if not start_date or not end_date:
            toast(self, "Choose a time period or set valid From/To dates first.", kind="warning")
            messagebox.showwarning(
                "Choose a date range",
                "Select Today / Monthly / Quarterly (or enter From/To and Apply dates), then try Monthly totals again.",
            )
            return
        if not invoices:
            label = self._period_label()
            toast(self, f"No sales for {label}.", kind="warning")
            messagebox.showwarning(
                "Nothing to export",
                f"No sales found for {label}.\n\nPick a Specific quarter/month that has sales, or widen From/To.",
            )
            return
        period = self._period_label()
        stamp = datetime.now().strftime("%Y%m%d")
        path = self._ask_pdf_path("Save monthly totals PDF", f"monthly-totals-{stamp}.pdf")
        if not path:
            return
        try:
            from sales_report_pdf import build_monthly_totals_pdf
            pdf_bytes = build_monthly_totals_pdf(
                invoices,
                period_label=period,
                start_date=start_date,
                end_date=end_date,
            )
            Path(path).write_bytes(pdf_bytes)
            self.winfo_toplevel().set_status(f"Saved monthly totals — {Path(path).name}")
            toast(self, f"Saved {Path(path).name}", kind="success", title="Monthly totals PDF")
        except Exception as e:
            toast(self, str(e), kind="error", title="PDF export failed")
            messagebox.showerror("PDF export failed", str(e))

    def _fresh_invoice(self, invoice):
        from database import get_invoice_by_id

        if not getattr(invoice, "id", None):
            return invoice
        fresh = get_invoice_by_id(invoice.id)
        if not fresh:
            raise ValueError("Could not load that sale from the database.")
        return fresh

    def view_invoice(self, invoice):
        try:
            fresh = self._fresh_invoice(invoice)
            show_receipt_viewer(self.winfo_toplevel(), fresh, list(fresh.items or []))
        except Exception as e:
            toast(self, str(e), kind="error", title="Could not open receipt")
            messagebox.showerror("Could not open receipt", str(e))

    def reprint_invoice(self, invoice):
        from printer import print_receipt
        try:
            fresh = self._fresh_invoice(invoice)
        except Exception as e:
            toast(self, str(e), kind="error", title="Print failed")
            messagebox.showerror("Print failed", str(e))
            return
        ok, msg = print_receipt(fresh, list(fresh.items or []))
        if ok:
            self.winfo_toplevel().set_status(f"Printed {fresh.invoice_number}")
            toast(self, f"Printed {fresh.invoice_number}", kind="success")
        else:
            toast(self, msg, kind="error", title="Print failed")
            messagebox.showerror("Print failed", msg)

    def email_invoice(self, invoice):
        from email_service import send_receipt_email

        try:
            fresh = self._fresh_invoice(invoice)
        except Exception as e:
            toast(self, str(e), kind="error", title="Email failed")
            messagebox.showerror("Email failed", str(e))
            return

        dialog = ctk.CTkInputDialog(
            text=f"Send receipt for {fresh.invoice_number} to:",
            title="Email receipt",
        )
        to_addr = dialog.get_input()
        if not to_addr:
            return
        ok, msg = send_receipt_email(to_addr, fresh, list(fresh.items or []))
        if ok:
            self.winfo_toplevel().set_status(msg)
            toast(self, msg, kind="success", title="Email sent")
        else:
            toast(self, msg, kind="error", title="Email failed")
            messagebox.showerror("Email failed", msg)
