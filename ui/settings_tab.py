import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import get_all_settings, save_setting
import os
import shutil
from datetime import datetime
from config import DATA_DIR, DB_PATH
from . import theme as T
from .toast import toast


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=T.BG, corner_radius=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.entries = {}
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
        bus_inner.pack(fill="both", expand=True, padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.section_title(bus_inner, "Your store", "This information prints on every receipt").pack(anchor="w", pady=(0, 16))
        for label, key in [
            ("Store name", "business_name"),
            ("Tagline (optional)", "business_tagline"),
            ("Address", "business_address"),
            ("Website (optional)", "business_website"),
            ("Phone number", "business_phone"),
            ("Email (optional)", "business_email"),
            ("HST / GST number", "gst_number"),
        ]:
            self._field(bus_inner, label, key, placeholder="" if key != "business_tagline" else "Your Tech, Our Passion")

        T.field_label(bus_inner, "Sales tax rate (%)", "e.g. 13 for Ontario HST").pack(anchor="w", pady=(4, 0))
        self.tax_pct_entry = ctk.CTkEntry(bus_inner, placeholder_text="13", **T.entry_kwargs(width=120))
        self.tax_pct_entry.pack(anchor="w", pady=(6, 12))

        T.field_label(bus_inner, "Return policy", "Printed at the bottom of receipts").pack(anchor="w", pady=(4, 4))
        self.receipt_footer = ctk.CTkTextbox(
            bus_inner, height=80, fg_color=T.SURFACE_ALT, border_color=T.BORDER,
            corner_radius=T.RADIUS_SM, font=T.FONT,
        )
        self.receipt_footer.pack(fill="x", pady=(0, 12))

        print_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        print_frame.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="nsew")
        pr_inner = ctk.CTkFrame(print_frame, fg_color="transparent")
        pr_inner.pack(fill="both", expand=True, padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.section_title(pr_inner, "Receipt printer", "Works with Epson TM-T20 and most thermal printers").pack(anchor="w", pady=(0, 16))

        T.field_label(pr_inner, "Store logo (optional)").pack(anchor="w")
        logo_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        logo_row.pack(fill="x", pady=(6, 14))
        self.entries["logo_path"] = ctk.CTkEntry(logo_row, **T.entry_kwargs())
        self.entries["logo_path"].pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(logo_row, text="Choose file", command=self.browse_logo, **T.button_kwargs(width=110)).pack(side="left")

        T.field_label(pr_inner, "Select your printer").pack(anchor="w", pady=(0, 4))
        pr_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        pr_row.pack(fill="x", pady=(0, 10))
        pr_row.grid_columnconfigure(0, weight=1)

        self.printer_var = ctk.StringVar(value="")
        self.printer_combo = ctk.CTkComboBox(pr_row, variable=self.printer_var, values=[], **T.combo_kwargs(width=260))
        self.printer_combo.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(pr_row, text="Refresh list", command=self.refresh_printers, **T.button_kwargs(width=110)).grid(
            row=0, column=1, sticky="e"
        )

        self.entries["printer_name"] = ctk.CTkEntry(
            pr_inner, placeholder_text="Or type your printer name here", **T.entry_kwargs()
        )
        self.entries["printer_name"].pack(fill="x", pady=(0, 14))

        T.field_label(pr_inner, "Receipt paper size").pack(anchor="w", pady=(0, 6))
        self.width_var = ctk.StringVar(value="80mm")
        w_row = ctk.CTkFrame(pr_inner, fg_color="transparent")
        w_row.pack(anchor="w", pady=(0, 14))
        for val, label in (("80mm", "Standard (80 mm)"), ("58mm", "Small (58 mm)")):
            ctk.CTkRadioButton(
                w_row, text=label, variable=self.width_var, value=val,
                command=self.refresh_receipt_preview,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
                radiobutton_width=20, radiobutton_height=20,
            ).pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            pr_inner, text="Print test receipt", command=self.test_print,
            **T.primary_button_kwargs(width=180),
        ).pack(anchor="w", pady=(4, 0))

        design_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        design_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
        d_inner = ctk.CTkFrame(design_frame, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.section_title(
            d_inner,
            "Receipt design",
            "Preview how receipts look and choose what to print",
        ).pack(anchor="w", pady=(0, 12))

        opts = ctk.CTkFrame(d_inner, fg_color="transparent")
        opts.pack(fill="x")
        opts.grid_columnconfigure(0, weight=1)
        opts.grid_columnconfigure(1, weight=1)

        left_opts = ctk.CTkFrame(opts, fg_color="transparent")
        left_opts.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        right_opts = ctk.CTkFrame(opts, fg_color="transparent")
        right_opts.grid(row=0, column=1, sticky="nw")

        T.field_label(left_opts, "Title size").pack(anchor="w", pady=(0, 6))
        self.font_size_var = ctk.StringVar(value="normal")
        font_row = ctk.CTkFrame(left_opts, fg_color="transparent")
        font_row.pack(anchor="w", pady=(0, 12))
        for val, label in (("normal", "Normal (recommended)"), ("large", "Large titles only")):
            ctk.CTkRadioButton(
                font_row, text=label, variable=self.font_size_var, value=val,
                command=self.refresh_receipt_preview,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
                radiobutton_width=20, radiobutton_height=20,
            ).pack(side="left", padx=(0, 16))

        T.field_label(left_opts, "Header spacing").pack(anchor="w", pady=(0, 6))
        self.header_spacing_var = ctk.StringVar(value="normal")
        space_row = ctk.CTkFrame(left_opts, fg_color="transparent")
        space_row.pack(anchor="w", pady=(0, 12))
        for val, label in (("compact", "Compact"), ("normal", "Normal"), ("roomy", "Roomy")):
            ctk.CTkRadioButton(
                space_row, text=label, variable=self.header_spacing_var, value=val,
                command=self.refresh_receipt_preview,
                font=T.FONT, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
                radiobutton_width=20, radiobutton_height=20,
            ).pack(side="left", padx=(0, 14))

        T.field_label(right_opts, "Show on receipt").pack(anchor="w", pady=(0, 8))
        self.design_toggles: dict[str, ctk.BooleanVar] = {}
        toggle_defs = [
            ("receipt_show_logo", "Logo"),
            ("receipt_show_business_name", "Store name"),
            ("receipt_show_tagline", "Tagline"),
            ("receipt_show_address", "Address"),
            ("receipt_show_phone", "Phone"),
            ("receipt_show_website", "Website"),
            ("receipt_show_email", "Email"),
            ("receipt_show_customer", "Customer / phone"),
            ("receipt_show_details", "Item details"),
            ("receipt_show_notes", "Sale notes"),
            ("receipt_show_thanks", "Thank-you line"),
            ("receipt_show_footer", "Return policy"),
            ("receipt_show_gst", "HST / GST number"),
        ]
        toggle_grid = ctk.CTkFrame(right_opts, fg_color="transparent")
        toggle_grid.pack(anchor="w")
        for i, (key, label) in enumerate(toggle_defs):
            var = ctk.BooleanVar(value=True)
            self.design_toggles[key] = var
            ctk.CTkCheckBox(
                toggle_grid, text=label, variable=var, command=self.refresh_receipt_preview,
                font=T.FONT_SMALL, text_color=T.TEXT, fg_color=T.ACCENT, border_color=T.BORDER,
                checkbox_width=18, checkbox_height=18,
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 18), pady=3)

        preview_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        preview_row.pack(fill="both", expand=True, pady=(16, 0))
        T.field_label(preview_row, "Live preview").pack(anchor="w", pady=(0, 6))
        self.receipt_preview = ctk.CTkTextbox(
            preview_row,
            height=320,
            fg_color=T.SURFACE_ALT,
            border_color=T.BORDER,
            corner_radius=T.RADIUS_SM,
            font=("Courier New", 12),
            text_color=T.TEXT,
            wrap="none",
        )
        self.receipt_preview.pack(fill="both", expand=True)
        self.receipt_preview.configure(state="disabled")

        btn_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(
            btn_row, text="Refresh preview", command=self.refresh_receipt_preview,
            **T.button_kwargs(width=150),
        ).pack(side="left")

        email_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        email_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        em_inner = ctk.CTkFrame(email_frame, fg_color="transparent")
        em_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.section_title(
            em_inner,
            "Email receipts (optional)",
            "Send receipts to customers by email — requires a Gmail app password",
        ).pack(anchor="w", pady=(0, 16))

        row1 = ctk.CTkFrame(em_inner, fg_color="transparent")
        row1.pack(fill="x")
        row1.grid_columnconfigure((0, 1, 2), weight=1)

        for col, (label, key, ph) in enumerate([
            ("Email server", "smtp_host", "smtp.gmail.com"),
            ("Port", "smtp_port", "587"),
            ("Your name on emails", "smtp_from_name", "My Business"),
        ]):
            colf = ctk.CTkFrame(row1, fg_color="transparent")
            colf.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 10, 0))
            T.field_label(colf, label).pack(anchor="w", pady=(0, 4))
            e = ctk.CTkEntry(colf, placeholder_text=ph, **T.entry_kwargs())
            e.pack(fill="x")
            self.entries[key] = e

        row2 = ctk.CTkFrame(em_inner, fg_color="transparent")
        row2.pack(fill="x", pady=(14, 0))
        row2.grid_columnconfigure((0, 1), weight=1)

        for col, (label, key, secret) in enumerate([
            ("Your Gmail address", "smtp_email", False),
            ("Gmail app password", "smtp_password", True),
        ]):
            colf = ctk.CTkFrame(row2, fg_color="transparent")
            colf.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 10, 0))
            T.field_label(colf, label).pack(anchor="w", pady=(0, 4))
            e = ctk.CTkEntry(
                colf,
                placeholder_text="you@gmail.com" if not secret else "16-character app password",
                show="*" if secret else None,
                **T.entry_kwargs(),
            )
            e.pack(fill="x")
            self.entries[key] = e

        backup_frame = ctk.CTkFrame(grid, **T.card_kwargs())
        backup_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        bk_inner = ctk.CTkFrame(backup_frame, fg_color="transparent")
        bk_inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)
        T.section_title(bk_inner, "Backup your data", "Save a copy of your sales and inventory to a safe place").pack(anchor="w", pady=(0, 12))
        ctk.CTkButton(bk_inner, text="Save backup to file…", command=self.backup_data, **T.button_kwargs(width=200)).pack(anchor="w")

        save_f = ctk.CTkFrame(scroll, fg_color="transparent")
        save_f.pack(fill="x", pady=16)
        ctk.CTkButton(save_f, text="Save all settings", command=self.save_settings, **T.success_button_kwargs(width=200)).pack()

        self.refresh_printers()

        self.refresh_printers()
        self.after(100, self.refresh_receipt_preview)

    def _collect_design_settings(self) -> dict:
        """Merge form values into a settings dict for live preview."""
        settings = get_all_settings()
        for key, entry in self.entries.items():
            settings[key] = entry.get().strip()
        settings["receipt_width"] = self.width_var.get()
        settings["receipt_font_size"] = self.font_size_var.get()
        settings["receipt_header_spacing"] = self.header_spacing_var.get()
        settings["receipt_footer"] = self.receipt_footer.get("1.0", "end").strip()
        try:
            pct = float(self.tax_pct_entry.get().strip() or "13")
            settings["tax_rate"] = str(pct / 100)
        except ValueError:
            pass
        for key, var in self.design_toggles.items():
            settings[key] = "1" if var.get() else "0"
        return settings

    def refresh_receipt_preview(self, *_args):
        from receipt_builder import build_receipt_text, sample_receipt_invoice

        settings = self._collect_design_settings()
        invoice, items = sample_receipt_invoice(settings)
        text = build_receipt_text(invoice, items, settings)
        self.receipt_preview.configure(state="normal")
        self.receipt_preview.delete("1.0", "end")
        self.receipt_preview.insert("1.0", text)
        self.receipt_preview.configure(state="disabled")

    def _field(self, parent, label, key, placeholder=""):
        T.field_label(parent, label).pack(anchor="w", pady=(0, 4))
        kw = T.entry_kwargs()
        if placeholder:
            kw["placeholder_text"] = placeholder
        entry = ctk.CTkEntry(parent, **kw)
        entry.pack(fill="x", pady=(0, 12))
        self.entries[key] = entry

    def browse_logo(self):
        filepath = filedialog.askopenfilename(
            title="Choose your store logo",
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

    def test_print(self):
        from printer import print_test_receipt
        ok, msg = print_test_receipt()
        if ok:
            toast(self, "Check your printer — a test receipt was sent.", kind="success", title="Test sent")
        else:
            toast(self, msg, kind="error", title="Print failed")
            messagebox.showerror("Print failed", msg)

    def backup_data(self):
        default_name = f"retail-invoice-backup-{datetime.now().strftime('%Y-%m-%d')}.db"
        dest = filedialog.asksaveasfilename(
            title="Save backup",
            defaultextension=".db",
            initialfile=default_name,
            filetypes=(("Database backup", "*.db"), ("All files", "*.*")),
        )
        if dest:
            try:
                shutil.copy2(DB_PATH, dest)
                toast(self, dest, kind="success", title="Backup saved")
                self.winfo_toplevel().set_status("Backup saved")
            except Exception as e:
                toast(self, str(e), kind="error", title="Backup failed")
                messagebox.showerror("Backup failed", str(e))

    def refresh_printers(self):
        printers: list[str] = []
        try:
            import platform

            if platform.system() == "Windows":
                import win32print  # type: ignore

                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                for p in win32print.EnumPrinters(flags):
                    printers.append(p[2])
        except Exception:
            printers = []

        printers = sorted(set([p for p in printers if p]))
        self.printer_combo.configure(values=printers)

        preferred = ""
        saved = self.entries["printer_name"].get().strip() or self.printer_var.get().strip()
        if saved:
            preferred = next((p for p in printers if p.lower() == saved.lower()), "")
            if not preferred:
                preferred = next((p for p in printers if saved.lower() in p.lower() or p.lower() in saved.lower()), "")
        if not preferred:
            preferred = next((p for p in printers if "tm-t20" in p.lower()), "")
        if not preferred and printers:
            preferred = printers[0]

        if preferred:
            self.printer_var.set(preferred)
            self.entries["printer_name"].delete(0, "end")
            self.entries["printer_name"].insert(0, preferred)

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
        try:
            rate = float(settings.get("tax_rate", "0.13"))
            pct = int(rate * 100) if rate * 100 == int(rate * 100) else rate * 100
            self.tax_pct_entry.delete(0, "end")
            self.tax_pct_entry.insert(0, str(pct))
        except ValueError:
            self.tax_pct_entry.delete(0, "end")
            self.tax_pct_entry.insert(0, "13")
        if "receipt_width" in settings:
            self.width_var.set(settings["receipt_width"])
        if "printer_name" in settings:
            self.printer_var.set(settings["printer_name"])
        if "receipt_footer" in settings:
            self.receipt_footer.delete("1.0", "end")
            self.receipt_footer.insert("1.0", settings["receipt_footer"])
        self.font_size_var.set(settings.get("receipt_font_size", "normal") or "normal")
        self.header_spacing_var.set(settings.get("receipt_header_spacing", "normal") or "normal")
        for key, var in self.design_toggles.items():
            var.set(str(settings.get(key, "1")).strip() not in ("0", "false", "False", ""))
        self.refresh_receipt_preview()

    def save_settings(self):
        try:
            for key, entry in self.entries.items():
                if key == "printer_name":
                    continue
                save_setting(key, entry.get().strip())
            try:
                pct = float(self.tax_pct_entry.get().strip() or "13")
                save_setting("tax_rate", str(pct / 100))
            except ValueError:
                save_setting("tax_rate", "0.13")
            printer = self.printer_var.get().strip() or self.entries["printer_name"].get().strip()
            save_setting("printer_name", printer)
            self.entries["printer_name"].delete(0, "end")
            self.entries["printer_name"].insert(0, printer)
            save_setting("receipt_width", self.width_var.get())
            save_setting("receipt_footer", self.receipt_footer.get("1.0", "end").strip())
            save_setting("receipt_font_size", self.font_size_var.get())
            save_setting("receipt_header_spacing", self.header_spacing_var.get())
            for key, var in self.design_toggles.items():
                save_setting(key, "1" if var.get() else "0")
            self.refresh_receipt_preview()
            self.winfo_toplevel().set_status("Settings saved")
            toast(self, "Your changes have been saved.", kind="success", title="Settings saved")
        except Exception as e:
            toast(self, str(e), kind="error", title="Could not save")
            messagebox.showerror("Error", str(e))
