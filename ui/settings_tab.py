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
        bus_frame = ctk.CTkFrame(self, **T.card_kwargs())
        bus_frame.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        bus_inner = ctk.CTkFrame(bus_frame, fg_color="transparent")
        bus_inner.pack(fill="both", expand=True, padx=24, pady=24)

        T.section_title(bus_inner, "Business", "Shown on printed receipts").pack(anchor="w", pady=(0, 16))

        for label, key in [
            ("Business name", "business_name"),
            ("Address", "business_address"),
            ("Phone", "business_phone"),
            ("GST/HST number", "gst_number"),
            ("Tax rate (0.13 = 13%)", "tax_rate"),
        ]:
            ctk.CTkLabel(bus_inner, text=label, **T.label_secondary()).pack(anchor="w", pady=(0, 4))
            entry = ctk.CTkEntry(bus_inner, **T.entry_kwargs())
            entry.pack(fill="x", pady=(0, 12))
            self.entries[key] = entry

        print_frame = ctk.CTkFrame(self, **T.card_kwargs())
        print_frame.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        pr_inner = ctk.CTkFrame(print_frame, fg_color="transparent")
        pr_inner.pack(fill="both", expand=True, padx=24, pady=24)

        T.section_title(pr_inner, "Printer", "Windows shared printer name").pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(pr_inner, text="Logo", **T.label_secondary()).pack(anchor="w")
        logo_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        logo_row.pack(fill="x", pady=(4, 12))
        self.entries["logo_path"] = ctk.CTkEntry(logo_row, **T.entry_kwargs())
        self.entries["logo_path"].pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(logo_row, text="Browse", command=self.browse_logo, **T.button_kwargs(width=72)).pack(side="left")

        ctk.CTkLabel(pr_inner, text="Printer name", **T.label_secondary()).pack(anchor="w", pady=(0, 4))
        self.entries["printer_name"] = ctk.CTkEntry(pr_inner, placeholder_text="EPSON TM-T20 Receipt", **T.entry_kwargs())
        self.entries["printer_name"].pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(pr_inner, text="Receipt width", **T.label_secondary()).pack(anchor="w", pady=(0, 4))
        self.width_var = ctk.StringVar(value="80mm")
        w_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        w_row.pack(anchor="w")
        for val in ("80mm", "58mm"):
            ctk.CTkRadioButton(
                w_row, text=val, variable=self.width_var, value=val,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
            ).pack(side="left", padx=(0, 16))

        save_f = ctk.CTkFrame(self, fg_color="transparent")
        save_f.grid(row=1, column=0, columnspan=2, pady=16)
        ctk.CTkButton(save_f, text="Save settings", command=self.save_settings, **T.primary_button_kwargs(width=160)).pack()

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select logo",
            filetypes=(("Images", "*.png *.jpg *.bmp"), ("All", "*.*")),
        )
        if filepath:
            dest = ASSETS_DIR / os.path.basename(filepath)
            try:
                shutil.copy(filepath, dest)
                self.entries["logo_path"].delete(0, "end")
                self.entries["logo_path"].insert(0, str(dest))
            except Exception as e:
                messagebox.showerror("Error", str(e))

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
            self.winfo_toplevel().set_status("Settings saved")
            messagebox.showinfo("Saved", "Settings have been saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
