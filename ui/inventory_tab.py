import customtkinter as ctk
from tkinter import messagebox
from database import add_product, update_product, delete_product, search_products
from models import Product
from utils import format_currency
from . import theme as T

class InventoryTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.create_top_bar()
        self.create_table()
        
        self.load_products()

    def create_top_bar(self):
        frame = ctk.CTkFrame(self, **T.panel_kwargs())
        frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        
        ctk.CTkButton(frame, text="+ Add Product (Alt+N)", command=self.show_product_dialog, **T.primary_button_kwargs()).pack(side="left", padx=8)
        
        ctk.CTkLabel(frame, text="Search (Alt+S):", **T.label_kwargs(text_color=T.LABEL_ACCENT)).pack(side="left", padx=(20, 5))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(frame, textvariable=self.search_var, **T.entry_kwargs(200))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.load_products())

    def create_table(self):
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color=T.BG, corner_radius=0)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=5)
        
        self.headers = ["ID", "Name", "Serial Number", "SKU", "Qty", "Price", "Category", "Actions"]
        self.widths = [50, 200, 150, 100, 50, 100, 100, 150]
        
        header_frame = ctk.CTkFrame(self.table_frame, fg_color=T.HEADER_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 5))
        
        for text, width in zip(self.headers, self.widths):
            ctk.CTkLabel(header_frame, text=text, width=width, anchor="w", font=T.FONT_HEADER, text_color=T.HEADER_TEXT).pack(side="left", padx=5, pady=3)
            
        self.rows_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True)

    def load_products(self):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()
            
        query = self.search_var.get().strip()
        products = search_products(query)
        
        for p in products:
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            # Highlight low stock
            text_color = T.WARN if p.qty <= 3 else T.TEXT
            
            ctk.CTkLabel(row, text=str(p.id), width=self.widths[0], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=p.name, width=self.widths[1], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=p.serial_number or "-", width=self.widths[2], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=p.sku or "-", width=self.widths[3], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(p.qty), width=self.widths[4], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=format_currency(p.price), width=self.widths[5], anchor="w", text_color=text_color).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=p.category or "-", width=self.widths[6], anchor="w", text_color=text_color).pack(side="left", padx=5)
            
            actions = ctk.CTkFrame(row, fg_color="transparent", width=self.widths[7])
            actions.pack(side="left", padx=5)
            
            ctk.CTkButton(actions, text="Edit", width=60, command=lambda prod=p: self.show_product_dialog(prod), **T.button_kwargs()).pack(side="left", padx=2)
            ctk.CTkButton(actions, text="Del", width=60, command=lambda prod=p: self.delete_product(prod), **T.danger_button_kwargs()).pack(side="left", padx=2)

    def delete_product(self, product: Product):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{product.name}'?"):
            delete_product(product.id)
            self.load_products()
            self.winfo_toplevel().set_status(f"Deleted product: {product.name}")

    def show_product_dialog(self, product: Product = None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Product" if product else "Add Product")
        dialog.geometry("400x500")
        dialog.configure(fg_color=T.BG)
        dialog.grab_set() # Modal
        
        entries = {}
        
        fields = [
            ("Name *", "name"),
            ("Serial Number", "serial_number"),
            ("SKU", "sku"),
            ("Price *", "price"),
            ("Quantity *", "qty"),
            ("Category", "category")
        ]
        
        for i, (label_text, key) in enumerate(fields):
            ctk.CTkLabel(dialog, text=label_text, **T.label_kwargs(text_color=T.LABEL_ACCENT)).grid(row=i, column=0, padx=20, pady=10, sticky="w")
            entry = ctk.CTkEntry(dialog, **T.entry_kwargs(200))
            entry.grid(row=i, column=1, padx=20, pady=10)
            entries[key] = entry
            
        if product:
            entries["name"].insert(0, product.name)
            entries["serial_number"].insert(0, product.serial_number or "")
            entries["sku"].insert(0, product.sku or "")
            entries["price"].insert(0, str(product.price))
            entries["qty"].insert(0, str(product.qty))
            entries["category"].insert(0, product.category or "")
        else:
            entries["qty"].insert(0, "1")
            entries["price"].insert(0, "0.00")
            
        def save():
            try:
                name = entries["name"].get().strip()
                if not name: raise ValueError("Name is required")
                
                price = float(entries["price"].get())
                qty = int(entries["qty"].get())
                
                new_product = Product(
                    id=product.id if product else None,
                    name=name,
                    serial_number=entries["serial_number"].get().strip(),
                    sku=entries["sku"].get().strip(),
                    price=price,
                    qty=qty,
                    category=entries["category"].get().strip(),
                    created_at=""
                )
                
                if product:
                    update_product(new_product)
                    self.winfo_toplevel().set_status(f"Updated product: {name}")
                else:
                    add_product(new_product)
                    self.winfo_toplevel().set_status(f"Added product: {name}")
                    
                self.load_products()
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Validation Error", str(e))
                
        ctk.CTkButton(dialog, text="Save", command=save, **T.primary_button_kwargs()).grid(row=len(fields), column=0, columnspan=2, pady=20)
