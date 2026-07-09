import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import get_all_settings, save_setting
import os
import shutil
from config import ASSETS_DIR
from PIL import Image

class SettingsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.entries = {}
        self.load_ui()
        self.load_settings()

    def load_ui(self):
        # Business Settings
        bus_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        bus_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(bus_frame, text="Business Information", font=("Consolas", 16, "bold"), text_color="#00FF00").pack(pady=10)
        
        fields = [
            ("Business Name", "business_name"),
            ("Address", "business_address"),
            ("Phone", "business_phone"),
            ("GST/HST Number", "gst_number"),
            ("Tax Rate (e.g. 0.13 for 13%)", "tax_rate")
        ]
        
        for label, key in fields:
            f = ctk.CTkFrame(bus_frame, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(f, text=label, width=200, anchor="w", text_color="#00FF00").pack(side="left")
            entry = ctk.CTkEntry(f, width=250, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
            entry.pack(side="left", expand=True, fill="x")
            self.entries[key] = entry
            
        # Printer Settings
        print_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        print_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(print_frame, text="Receipt & Printer", font=("Consolas", 16, "bold"), text_color="#00FF00").pack(pady=10)
        
        # Logo path
        logo_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        logo_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(logo_f, text="Logo Path", width=120, anchor="w", text_color="#00FF00").pack(side="left")
        self.entries["logo_path"] = ctk.CTkEntry(logo_f, width=200, fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.entries["logo_path"].pack(side="left", expand=True, fill="x", padx=5)
        ctk.CTkButton(logo_f, text="Browse", width=60, command=self.browse_logo, fg_color="#003300", hover_color="#00AA00", text_color="#00FF00", corner_radius=0).pack(side="left")
        
        # Printer name
        ptr_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        ptr_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ptr_f, text="Printer Name\n(Windows Share Name)", width=150, anchor="w", text_color="#00FF00").pack(side="left")
        self.entries["printer_name"] = ctk.CTkEntry(ptr_f, width=250, placeholder_text="e.g. EPSON TM-T20 Receipt", fg_color="#111111", text_color="#00FF00", border_color="#00FF00", corner_radius=0)
        self.entries["printer_name"].pack(side="left", expand=True, fill="x")
        
        # Receipt width
        width_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        width_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(width_f, text="Receipt Width", width=150, anchor="w", text_color="#00FF00").pack(side="left")
        self.width_var = ctk.StringVar(value="80mm")
        ctk.CTkRadioButton(width_f, text="80mm", variable=self.width_var, value="80mm", text_color="#00FF00", fg_color="#00FF00", hover_color="#00AA00", border_color="#00FF00").pack(side="left", padx=10)
        ctk.CTkRadioButton(width_f, text="58mm", variable=self.width_var, value="58mm", text_color="#00FF00", fg_color="#00FF00", hover_color="#00AA00", border_color="#00FF00").pack(side="left", padx=10)
        
        # Save Button
        save_f = ctk.CTkFrame(self, fg_color="transparent")
        save_f.grid(row=1, column=0, columnspan=2, pady=20)
        ctk.CTkButton(save_f, text="Save Settings", command=self.save_settings, width=200, height=40, fg_color="#00AA00", hover_color="#00FF00", text_color="#000000", corner_radius=0).pack()

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=(("Image files", "*.png *.jpg *.bmp"), ("All files", "*.*"))
        )
        if filepath:
            # Optionally copy to assets
            dest = ASSETS_DIR / os.path.basename(filepath)
            try:
                shutil.copy(filepath, dest)
                self.entries["logo_path"].delete(0, 'end')
                self.entries["logo_path"].insert(0, str(dest))
            except Exception as e:
                messagebox.showerror("Error", f"Could not copy image: {e}")

    def load_settings(self):
        settings = get_all_settings()
        for key, entry in self.entries.items():
            if key in settings:
                entry.delete(0, 'end')
                entry.insert(0, settings[key])
                
        if "receipt_width" in settings:
            self.width_var.set(settings["receipt_width"])

    def save_settings(self):
        try:
            for key, entry in self.entries.items():
                save_setting(key, entry.get().strip())
                
            save_setting("receipt_width", self.width_var.get())
            
            self.winfo_toplevel().set_status("Settings saved successfully!")
            messagebox.showinfo("Success", "Settings have been saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
