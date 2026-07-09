import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from database import search_products, generate_invoice_number, save_invoice, get_setting
from models import Invoice, InvoiceItem
from printer import print_receipt
from utils import format_currency, parse_currency

class InvoiceTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.items = [] # list of InvoiceItem
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.create_customer_section()
        self.create_item_entry_section()
        self.create_items_list_section()
        self.create_totals_section()
    def create_customer_section(self):
        frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(frame, text="Customer Name (Alt+C):", text_color="#00FF00").pack(side="left", padx=5, pady=5)
        self.customer_name_entry = ctk.CTkEntry(frame, width=200, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.customer_name_entry.pack(side="left", padx=5, pady=5)
        
        ctk.CTkLabel(frame, text="Phone Number (Alt+P):", text_color="#00FF00").pack(side="left", padx=5, pady=5)
        self.customer_phone_entry = ctk.CTkEntry(frame, width=150, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.customer_phone_entry.pack(side="left", padx=5, pady=5)

    def create_item_entry_section(self):
        frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        # Inventory Search
        inv_frame = ctk.CTkFrame(frame, fg_color="transparent")
        inv_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(inv_frame, text="Search Inventory (Alt+S):", text_color="#00FF00").pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(inv_frame, textvariable=self.search_var, width=200, placeholder_text="Name or Serial", fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        self.search_results = ctk.CTkComboBox(inv_frame, width=200, values=[], fg_color="#111111", text_color="#00FF00", border_color="#00FF00", button_color="#003300", button_hover_color="#00AA00", corner_radius=0)
        self.search_results.pack(side="left", padx=5)
        
        ctk.CTkButton(inv_frame, text="Add Inventory Item", fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0, command=self.add_inventory_item, width=120).pack(side="left", padx=5)
        
        # Manual Item
        man_frame = ctk.CTkFrame(frame, fg_color="transparent")
        man_frame.pack(side="right", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(man_frame, text="Manual (Alt+M):", text_color="#00FF00").pack(side="left", padx=5)
        self.man_desc = ctk.CTkEntry(man_frame, width=120, placeholder_text="Description", fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.man_desc.pack(side="left", padx=5)
        
        self.man_qty = ctk.CTkEntry(man_frame, width=50, placeholder_text="Qty", fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.man_qty.insert(0, "1")
        self.man_qty.pack(side="left", padx=5)
        
        self.man_price = ctk.CTkEntry(man_frame, width=80, placeholder_text="Price", fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.man_price.pack(side="left", padx=5)
        
        ctk.CTkButton(man_frame, text="Add Manual Item (Alt+A)", fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0, command=self.add_manual_item, width=120).pack(side="left", padx=5)
        
        self.current_search_products = []

    def create_items_list_section(self):
        self.items_frame = ctk.CTkScrollableFrame(self, fg_color="#111111", corner_radius=0)
        self.items_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Header
        headers = ["Description", "S/N", "Qty", "Price", "Total", "Action"]
        widths = [250, 150, 50, 100, 100, 80]
        
        header_frame = ctk.CTkFrame(self.items_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        
        for i, (text, width) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(header_frame, text=text, width=width, anchor="w", font=("Consolas", 12, "bold"), text_color="#00FF00").pack(side="left", padx=5)
            
        self.item_rows_frame = ctk.CTkFrame(self.items_frame, fg_color="transparent")
        self.item_rows_frame.pack(fill="both", expand=True)

    def create_totals_section(self):
        frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        # Left side - Payment & Notes
        left_frame = ctk.CTkFrame(frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(left_frame, text="Payment Method:", text_color="#00FF00").grid(row=0, column=0, sticky="w", pady=5)
        self.payment_var = ctk.StringVar(value="Cash")
        ctk.CTkRadioButton(left_frame, text="Cash", variable=self.payment_var, value="Cash", text_color="#00FF00", fg_color="#00FF00", hover_color="#00AA00", border_color="#00FF00").grid(row=0, column=1, padx=5)
        ctk.CTkRadioButton(left_frame, text="Card", variable=self.payment_var, value="Card", text_color="#00FF00", fg_color="#00FF00", hover_color="#00AA00", border_color="#00FF00").grid(row=0, column=2, padx=5)
        ctk.CTkRadioButton(left_frame, text="Other", variable=self.payment_var, value="Other", text_color="#00FF00", fg_color="#00FF00", hover_color="#00AA00", border_color="#00FF00").grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(left_frame, text="Notes:", text_color="#00FF00").grid(row=1, column=0, sticky="w", pady=5)
        self.notes_entry = ctk.CTkEntry(left_frame, width=300, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.notes_entry.grid(row=1, column=1, columnspan=3, sticky="w", pady=5)
        
        # Actions
        actions_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        actions_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="w")
        
        ctk.CTkButton(actions_frame, text="🖨️ Print & Save (F12)", command=lambda: self.save(print_rcpt=True), fg_color="#00AA00", hover_color="#00FF00", text_color="#000000", corner_radius=0).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="💾 Save Only (F11)", command=lambda: self.save(print_rcpt=False), fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="🗑️ Clear (F9)", command=self.clear_form, fg_color="#550000", hover_color="#AA0000", text_color="#00FF00", corner_radius=0).pack(side="left", padx=5)
        
        # Right side - Totals
        right_frame = ctk.CTkFrame(frame, fg_color="transparent")
        right_frame.pack(side="right", padx=20)
        
        self.subtotal_label = ctk.CTkLabel(right_frame, text="Subtotal: $0.00", font=("Consolas", 14), text_color="#00FF00")
        self.subtotal_label.pack(anchor="e", pady=2)
        
        tax_pct = int(self.tax_rate * 100)
        self.tax_label = ctk.CTkLabel(right_frame, text=f"HST ({tax_pct}%): $0.00", font=("Consolas", 14), text_color="#00FF00")
        self.tax_label.pack(anchor="e", pady=2)
        
        self.total_label = ctk.CTkLabel(right_frame, text="TOTAL: $0.00", font=("Consolas", 18, "bold"), text_color="#00FF00")
        self.total_label.pack(anchor="e", pady=5)

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
            sn_text = f" (S/N: {p.serial_number})" if p.serial_number else ""
            values.append(f"{p.name}{sn_text} - ${p.price:.2f} [{p.qty} in stock]")
            
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
                line_total=p.price
            )
            self.items.append(item)
            self.refresh_items()
            
            # Reset search
            self.search_var.set("")
            self.search_results.set("")
            self.search_results.configure(values=[])
            self.current_search_products = []

    def add_manual_item(self):
        desc = self.man_desc.get().strip()
        qty_str = self.man_qty.get().strip()
        price_str = self.man_price.get().strip()
        
        if not desc:
            messagebox.showerror("Error", "Description is required.")
            return
            
        try:
            qty = int(qty_str)
            if qty <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer.")
            return
            
        try:
            price = float(price_str)
            if price < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Price must be a valid number.")
            return
            
        item = InvoiceItem(
            id=None, invoice_id=None, product_id=None,
            description=desc, serial_number="",
            qty=qty, unit_price=price, line_total=qty*price
        )
        self.items.append(item)
        self.refresh_items()
        
        # Reset inputs
        self.man_desc.delete(0, 'end')
        self.man_qty.delete(0, 'end')
        self.man_qty.insert(0, "1")
        self.man_price.delete(0, 'end')

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_items()

    def refresh_items(self):
        # Clear existing rows
        for widget in self.item_rows_frame.winfo_children():
            widget.destroy()
            
        widths = [250, 150, 50, 100, 100, 80]
        subtotal = 0.0
        
        for i, item in enumerate(self.items):
            row_frame = ctk.CTkFrame(self.item_rows_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row_frame, text=item.description, width=widths[0], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=item.serial_number, width=widths[1], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=str(item.qty), width=widths[2], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=format_currency(item.unit_price), width=widths[3], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=format_currency(item.line_total), width=widths[4], anchor="w", text_color="#00FF00").pack(side="left", padx=5)
            
            ctk.CTkButton(row_frame, text="X", width=widths[5], fg_color="#330000", hover_color="#AA0000", text_color="#FF0000", corner_radius=0, 
                         command=lambda idx=i: self.remove_item(idx)).pack(side="left", padx=5)
                         
            subtotal += item.line_total
            
        # Update totals
        self.tax_rate = float(get_setting("tax_rate", "0.13"))
        tax_amount = subtotal * self.tax_rate
        total = subtotal + tax_amount
        
        tax_pct = int(self.tax_rate * 100)
        self.subtotal_label.configure(text=f"Subtotal: {format_currency(subtotal)}")
        self.tax_label.configure(text=f"HST ({tax_pct}%): {format_currency(tax_amount)}")
        self.total_label.configure(text=f"TOTAL: {format_currency(total)}")

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
            created_at=None, # Will be set by DB
            items=[]
        )
        
        try:
            save_invoice(invoice, self.items)
            msg = f"Invoice {invoice.invoice_number} saved successfully!"
            
            if print_rcpt:
                # Set created_at for printing
                from datetime import datetime
                invoice.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if print_receipt(invoice, self.items):
                    msg += " Printed successfully."
                else:
                    msg += " Printing failed. Check settings."
                    
            self.winfo_toplevel().set_status(msg)
            self.clear_form()
            
            # If InventoryTab exists, refresh it
            app = self.winfo_toplevel()
            if hasattr(app, 'inventory_tab'):
                app.inventory_tab.load_products()
            if hasattr(app, 'reports_tab'):
                app.reports_tab.load_invoices()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save invoice: {str(e)}")

    def clear_form(self):
        self.customer_name_entry.delete(0, 'end')
        self.customer_phone_entry.delete(0, 'end')
        self.notes_entry.delete(0, 'end')
        self.items = []
        self.payment_var.set("Cash")
        self.refresh_items()
