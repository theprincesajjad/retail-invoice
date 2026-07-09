import customtkinter as ctk
from database import get_invoices
from models import Invoice
from utils import format_currency
from datetime import datetime, timedelta
import calendar

class ReportsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.create_filters()
        self.create_summary()
        self.create_table()
        
        # Load current month by default
        self.period_var.set("Monthly")
        self.on_filter_change()

    def create_filters(self):
        frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="Period (Alt+P):", text_color="#00FF00").pack(side="left", padx=5)
        self.period_var = ctk.StringVar(value="Monthly")
        self.period_combo = ctk.CTkComboBox(frame, variable=self.period_var, values=["Monthly", "Quarterly", "Yearly"], command=self.on_filter_change, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", button_color="#003300", button_hover_color="#00AA00", corner_radius=0)
        self.period_combo.pack(side="left", padx=5)
        
        ctk.CTkLabel(frame, text="Date Range:", text_color="#00FF00").pack(side="left", padx=(20, 5))
        self.range_var = ctk.StringVar()
        self.range_combo = ctk.CTkComboBox(frame, variable=self.range_var, values=[], command=self.load_invoices, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", button_color="#003300", button_hover_color="#00AA00", corner_radius=0)
        self.range_combo.pack(side="left", padx=5)
        
        ctk.CTkButton(frame, text="Refresh (Alt+R)", command=self.load_invoices, fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0).pack(side="left", padx=20)

    def create_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.total_sales_var = ctk.StringVar(value="$0.00")
        self.total_tax_var = ctk.StringVar(value="$0.00")
        self.invoice_count_var = ctk.StringVar(value="0")
        self.avg_invoice_var = ctk.StringVar(value="$0.00")
        
        boxes = [
            ("Total Sales", self.total_sales_var),
            ("Total Tax", self.total_tax_var),
            ("Invoice Count", self.invoice_count_var),
            ("Avg Invoice", self.avg_invoice_var)
        ]
        
        for i, (title, var) in enumerate(boxes):
            box = ctk.CTkFrame(self.summary_frame, fg_color="#002200", corner_radius=0)
            box.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            self.summary_frame.grid_columnconfigure(i, weight=1)
            
            ctk.CTkLabel(box, text=title, font=("Consolas", 12), text_color="#00FF00").pack(pady=(10, 0))
            ctk.CTkLabel(box, textvariable=var, font=("Consolas", 18, "bold"), text_color="#00FF00").pack(pady=(0, 10))

    def create_table(self):
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color="#111111", corner_radius=0)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Headers
        self.headers = ["Invoice #", "Date", "Customer", "Subtotal", "Tax", "Total", "Payment", "Action"]
        self.widths = [120, 150, 150, 80, 80, 100, 100, 100]
        
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        
        for text, width in zip(self.headers, self.widths):
            ctk.CTkLabel(header_frame, text=text, width=width, anchor="w", font=("Consolas", 12, "bold"), text_color="#00FF00").pack(side="left", padx=5)
            
        self.rows_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True)

    def on_filter_change(self, *args):
        period = self.period_var.get()
        now = datetime.now()
        year = now.year
        
        values = []
        if period == "Monthly":
            # Show last 12 months
            for i in range(12):
                d = now - timedelta(days=30*i)
                values.append(d.strftime("%b %Y"))
        elif period == "Quarterly":
            values = [f"Q1 {year}", f"Q2 {year}", f"Q3 {year}", f"Q4 {year}", 
                      f"Q1 {year-1}", f"Q2 {year-1}", f"Q3 {year-1}", f"Q4 {year-1}"]
        elif period == "Yearly":
            values = [str(year), str(year-1), str(year-2)]
            
        self.range_combo.configure(values=values)
        self.range_var.set(values[0])
        self.load_invoices()

    def get_date_range(self):
        period = self.period_var.get()
        rng = self.range_var.get()
        
        start_date = None
        end_date = None
        
        try:
            if period == "Monthly":
                dt = datetime.strptime(rng, "%b %Y")
                start_date = dt.strftime("%Y-%m-01 00:00:00")
                _, last_day = calendar.monthrange(dt.year, dt.month)
                end_date = dt.strftime(f"%Y-%m-{last_day} 23:59:59")
                
            elif period == "Quarterly":
                q, y = rng.split()
                y = int(y)
                if q == "Q1": start_month, end_month = 1, 3
                elif q == "Q2": start_month, end_month = 4, 6
                elif q == "Q3": start_month, end_month = 7, 9
                else: start_month, end_month = 10, 12
                
                start_date = f"{y}-{start_month:02d}-01 00:00:00"
                _, last_day = calendar.monthrange(y, end_month)
                end_date = f"{y}-{end_month:02d}-{last_day} 23:59:59"
                
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
        invoices = get_invoices(start_date, end_date)
        
        total_sales = sum(inv.total for inv in invoices)
        total_tax = sum(inv.tax_amount for inv in invoices)
        count = len(invoices)
        avg = total_sales / count if count > 0 else 0
        
        self.total_sales_var.set(format_currency(total_sales))
        self.total_tax_var.set(format_currency(total_tax))
        self.invoice_count_var.set(str(count))
        self.avg_invoice_var.set(format_currency(avg))
        
        for inv in invoices:
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            # Formatting date
            date_str = inv.created_at[:16] if inv.created_at else ""
            
            ctk.CTkLabel(row, text=inv.invoice_number, width=self.widths[0], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=date_str, width=self.widths[1], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=inv.customer_name or "-", width=self.widths[2], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=format_currency(inv.subtotal), width=self.widths[3], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=format_currency(inv.tax_amount), width=self.widths[4], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            
            # Bold Total
            ctk.CTkLabel(row, text=format_currency(inv.total), width=self.widths[5], anchor="w", font=("Consolas", 12, "bold"), text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=inv.payment_method, width=self.widths[6], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            
            # Action column
            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[7])
            actions.pack(side="left", padx=5)
            
            def make_reprint_cmd(invoice_obj):
                return lambda: self.reprint_invoice(invoice_obj)
                
            ctk.CTkButton(actions, text="Reprint", width=80, command=make_reprint_cmd(inv), fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0).pack(side="left")

    def reprint_invoice(self, invoice):
        from printer import print_receipt
        from tkinter import messagebox
        if print_receipt(invoice, invoice.items):
            self.winfo_toplevel().set_status(f"Reprinted {invoice.invoice_number}")
            messagebox.showinfo("Success", f"Reprinted {invoice.invoice_number}")
        else:
            self.winfo_toplevel().set_status("Reprint failed.")
            messagebox.showerror("Error", "Printing failed. Check settings and printer connection.")
