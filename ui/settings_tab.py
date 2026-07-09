import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import get_all_settings, save_setting
import os
import shutil
from config import ASSETS_DIR
from . import theme as T


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.entries = {}
        self.load_ui()
        self.load_settings()

    def load_ui(self):
        bus_frame = ctk.CTkFrame(self, **T.panel_kwargs())
        bus_frame.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        ctk.CTkLabel(bus_frame, text="Business Information", font=T.FONT_BOLD, text_color=T.LABEL_ACCENT).pack(pady=10)

        fields = [
            ("Business Name", "business_name"),
            ("Address", "business_address"),
            ("Phone", "business_phone"),
            ("GST/HST Number", "gst_number"),
            ("Tax Rate (e.g. 0.13 for 13%)", "tax_rate"),
        ]

        for label, key in fields:
            f = ctk.CTkFrame(bus_frame, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(f, text=label, width=200, anchor="w", **T.label_kwargs()).pack(side="left")
            entry = ctk.CTkEntry(f, **T.entry_kwargs(250))
            entry.pack(side="left", expand=True, fill="x")
            self.entries[key] = entry

        print_frame = ctk.CTkFrame(self, **T.panel_kwargs())
        print_frame.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")

        ctk.CTkLabel(print_frame, text="Receipt & Printer", font=T.FONT_BOLD, text_color=T.LABEL_ACCENT).pack(pady=10)

        logo_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        logo_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(logo_f, text="Logo Path", width=120, anchor="w", **T.label_kwargs()).pack(side="left")
        self.entries["logo_path"] = ctk.CTkEntry(logo_f, **T.entry_kwargs(200))
        self.entries["logo_path"].pack(side="left", expand=True, fill="x", padx=5)
        ctk.CTkButton(logo_f, text="Browse", width=60, command=self.browse_logo, **T.button_kwargs()).pack(side="left")

        ptr_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        ptr_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ptr_f, text="Printer Name\n(Windows Share Name)", width=150, anchor="w", **T.label_kwargs()).pack(side="left")
        self.entries["printer_name"] = ctk.CTkEntry(ptr_f, placeholder_text="e.g. EPSON TM-T20 Receipt", **T.entry_kwargs(250))
        self.entries["printer_name"].pack(side="left", expand=True, fill="x")

        width_f = ctk.CTkFrame(print_frame, fg_color="transparent")
        width_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(width_f, text="Receipt Width", width=150, anchor="w", **T.label_kwargs()).pack(side="left")
        self.width_var = ctk.StringVar(value="80mm")
        for val in ("80mm", "58mm"):
            ctk.CTkRadioButton(
                width_f,
                text=val,
                variable=self.width_var,
                value=val,
                text_color=T.TEXT,
                fg_color=T.HEADER_BG,
                hover_color=T.LABEL_ACCENT,
                border_color=T.BORDER,
                font=T.FONT,
            ).pack(side="left", padx=10)

        save_f = ctk.CTkFrame(self, fg_color="transparent")
        save_f.grid(row=1, column=0, columnspan=2, pady=20)
        ctk.CTkButton(save_f, text="Save Settings", command=self.save_settings, width=200, height=40, **T.primary_button_kwargs()).pack()

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=(("Image files", "*.png *.jpg *.bmp"), ("All files", "*.*")),
        )
        if filepath:
            dest = ASSETS_DIR / os.path.basename(filepath)
            try:
                shutil.copy(filepath, dest)
                self.entries["logo_path"].delete(0, "end")
                self.entries["logo_path"].insert(0, str(dest))
            except Exception as e:
                messagebox.showerror("Error", f"Could not copy image: {e}")

    def load_settings(self):
        settings = get_all_settings()
        for key, entry in self.entries.items():
            if key in settings:
                entry.delete(0, "end")
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
