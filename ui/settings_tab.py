import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import get_all_settings, save_setting
import os
import shutil
from config import DATA_DIR
from . import theme as T


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.entries = {}
        self.password_entries = {}
        self.load_ui()
        self.load_settings()

    def load_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        bus_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        bus_frame.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="nsew")
        bus_inner = ctk.CTkFrame(bus_frame, fg_color="transparent")
        bus_inner.pack(fill="both", expand=True, padx=24, pady=24)
        T.section_title(bus_inner, "Business", "Shown on receipts and emails").pack(anchor="w", pady=(0, 16))
        for label, key in [
            ("Business name", "business_name"),
            ("Address", "business_address"),
            ("Phone", "business_phone"),
            ("GST/HST number", "gst_number"),
            ("Tax rate (0.13 = 13%)", "tax_rate"),
        ]:
            self._field(bus_inner, label, key)

        print_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        print_frame.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="nsew")
        pr_inner = ctk.CTkFrame(print_frame, fg_color="transparent")
        pr_inner.pack(fill="both", expand=True, padx=24, pady=24)
        T.section_title(pr_inner, "Printer", "Windows shared printer").pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(pr_inner, text="Logo", **T.label_secondary()).pack(anchor="w")
        logo_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        logo_row.pack(fill="x", pady=(4, 12))
        self.entries["logo_path"] = ctk.CTkEntry(logo_row, **T.entry_kwargs())
        self.entries["logo_path"].pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(logo_row, text="Browse", command=self.browse_logo, **T.button_kwargs(width=72)).pack(side="left")

        ctk.CTkLabel(pr_inner, text="Printer", **T.label_secondary()).pack(anchor="w", pady=(0, 4))
        pr_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        pr_row.pack(fill="x", pady=(0, 12))
        pr_row.grid_columnconfigure(0, weight=1)

        self.printer_var = ctk.StringVar(value="")
        self.printer_combo = ctk.CTkComboBox(pr_row, variable=self.printer_var, values=[], **T.combo_kwargs(width=260))
        self.printer_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(pr_row, text="Refresh", command=self.refresh_printers, **T.button_kwargs(width=84)).grid(
            row=0, column=1, sticky="e"
        )

        # Backing setting field (also supports manual typing in case printer enumeration fails)
        self.entries["printer_name"] = ctk.CTkEntry(pr_inner, placeholder_text="Type printer name if not listed", **T.entry_kwargs())
        self.entries["printer_name"].pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(pr_inner, text="Receipt width", **T.label_secondary()).pack(anchor="w", pady=(0, 4))
        self.width_var = ctk.StringVar(value="80mm")
        w_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        w_row.pack(anchor="w", pady=(0, 8))
        for val in ("80mm", "58mm"):
            ctk.CTkRadioButton(
                w_row, text=val, variable=self.width_var, value=val,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
            ).pack(side="left", padx=(0, 16))

        email_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        email_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
        em_inner = ctk.CTkFrame(email_frame, fg_color="transparent")
        em_inner.pack(fill="x", padx=24, pady=24)
        T.section_title(
            em_inner,
            "Email (Gmail SMTP)",
            "Use a Google App Password — not your regular Gmail password",
        ).pack(anchor="w", pady=(0, 16))

        row1 = ctk.CTkFrame(em_inner, fg_color="transparent")
        row1.pack(fill="x")
        row1.grid_columnconfigure((0, 1, 2), weight=1)

        for col, (label, key, ph) in enumerate([
            ("SMTP host", "smtp_host", "smtp.gmail.com"),
            ("Port", "smtp_port", "587"),
            ("From name", "smtp_from_name", "My Business"),
        ]):
            colf = ctk.CTkFrame(row1, fg_color="transparent")
            colf.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
            ctk.CTkLabel(colf, text=label, **T.label_secondary()).pack(anchor="w", pady=(0, 4))
            e = ctk.CTkEntry(colf, placeholder_text=ph, **T.entry_kwargs())
            e.pack(fill="x")
            self.entries[key] = e

        row2 = ctk.CTkFrame(em_inner, fg_color="transparent")
        row2.pack(fill="x", pady=(12, 0))
        row2.grid_columnconfigure((0, 1), weight=1)

        for col, (label, key, secret) in enumerate([
            ("Gmail address", "smtp_email", False),
            ("App password", "smtp_password", True),
        ]):
            colf = ctk.CTkFrame(row2, fg_color="transparent")
            colf.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
            ctk.CTkLabel(colf, text=label, **T.label_secondary()).pack(anchor="w", pady=(0, 4))
            e = ctk.CTkEntry(colf, placeholder_text="you@gmail.com" if not secret else "16-character app password", show="*" if secret else None, **T.entry_kwargs())
            e.pack(fill="x")
            self.entries[key] = e

        save_f = ctk.CTkFrame(scroll, fg_color="transparent")
        save_f.pack(fill="x", pady=12)
        ctk.CTkButton(save_f, text="Save settings", command=self.save_settings, **T.primary_button_kwargs(width=180)).pack()

        self.refresh_printers()

    def _field(self, parent, label, key, placeholder=""):
        ctk.CTkLabel(parent, text=label, **T.label_secondary()).pack(anchor="w", pady=(0, 4))
        kw = T.entry_kwargs()
        if placeholder:
            kw["placeholder_text"] = placeholder
        entry = ctk.CTkEntry(parent, **kw)
        entry.pack(fill="x", pady=(0, 12))
        self.entries[key] = entry

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Select logo",
            filetypes=(("Images", "*.png *.jpg *.bmp"), ("All", "*.*")),
        )
        if filepath:
            ext = os.path.splitext(filepath)[1].lower() or ".png"
            dest = DATA_DIR / f"logo{ext}"
            try:
                shutil.copy(filepath, dest)
                self.entries["logo_path"].delete(0, "end")
                self.entries["logo_path"].insert(0, str(dest))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def refresh_printers(self):
        printers: list[str] = []
        try:
            import platform

            if platform.system() == "Windows":
                import win32print  # type: ignore

                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                for p in win32print.EnumPrinters(flags):
                    # Tuple shape: (flags, description, name, comment)
                    printers.append(p[2])
        except Exception:
            printers = []

        printers = sorted(set([p for p in printers if p]))
        self.printer_combo.configure(values=printers)
        if printers and not self.printer_var.get():
            self.printer_var.set(printers[0])
            self.entries["printer_name"].delete(0, "end")
            self.entries["printer_name"].insert(0, printers[0])

        # Keep manual field in sync when selecting from combo
        def _sync(*_):
            val = self.printer_var.get().strip()
            if val:
                self.entries["printer_name"].delete(0, "end")
                self.entries["printer_name"].insert(0, val)

        self.printer_combo.configure(command=lambda _: _sync())

    def load_settings(self):
        settings = get_all_settings()
        for key, entry in self.entries.items():
            if key in settings:
                entry.delete(0, "end")
                entry.insert(0, settings[key])
        if "receipt_width" in settings:
            self.width_var.set(settings["receipt_width"])
        if "printer_name" in settings:
            self.printer_var.set(settings["printer_name"])

    def save_settings(self):
        try:
            for key, entry in self.entries.items():
                save_setting(key, entry.get().strip())
            save_setting("receipt_width", self.width_var.get())
            self.winfo_toplevel().set_status("Settings saved")
            messagebox.showinfo("Saved", "Settings have been saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
