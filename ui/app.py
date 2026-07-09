import sys
import customtkinter as ctk
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab
from . import theme as T

TAB_INVOICE = "Invoice"
TAB_INVENTORY = "Inventory"
TAB_REPORTS = "Reports"
TAB_SETTINGS = "Settings"


def get_app_version() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "1.1.0"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Retail Invoice  {get_app_version()}")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=T.BG)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_status()
        self._bind_shortcuts()

        self.tabview.set(TAB_INVOICE)
        self.after(150, self.invoice_tab.focus_customer)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="Retail Invoice",
            font=T.FONT_TITLE,
            text_color=T.TEXT,
        ).pack(side="left", padx=24, pady=12)

        ctk.CTkLabel(
            header,
            text=f"v{get_app_version()}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_TERTIARY,
        ).pack(side="left", pady=12)

    def _build_tabs(self):
        shell = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        shell.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            shell,
            fg_color=T.SURFACE,
            text_color=T.TEXT_SECONDARY,
            segmented_button_fg_color=T.SURFACE_ALT,
            segmented_button_selected_color=T.SURFACE,
            segmented_button_selected_hover_color=T.SURFACE,
            segmented_button_unselected_color=T.SURFACE_ALT,
            segmented_button_unselected_hover_color=T.BORDER,
            corner_radius=T.RADIUS_MD,
            border_width=1,
            border_color=T.BORDER,
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")

        for name in (TAB_INVOICE, TAB_INVENTORY, TAB_REPORTS, TAB_SETTINGS):
            self.tabview.add(name)

        self.invoice_tab = InvoiceTab(self.tabview.tab(TAB_INVOICE))
        self.invoice_tab.pack(fill="both", expand=True)

        self.inventory_tab = InventoryTab(self.tabview.tab(TAB_INVENTORY))
        self.inventory_tab.pack(fill="both", expand=True)

        self.reports_tab = ReportsTab(self.tabview.tab(TAB_REPORTS))
        self.reports_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(self.tabview.tab(TAB_SETTINGS))
        self.settings_tab.pack(fill="both", expand=True)

    def _build_status(self):
        self.status_var = ctk.StringVar(value="Ready")
        bar = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=32, border_width=1, border_color=T.BORDER)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkLabel(bar, textvariable=self.status_var, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w").pack(
            side="left", padx=24, fill="x", expand=True
        )

    def current_tab(self) -> str:
        return self.tabview.get()

    def _bind_shortcuts(self):
        self.bind("<F1>", lambda e: self.tabview.set(TAB_INVOICE))
        self.bind("<F2>", lambda e: self.tabview.set(TAB_INVENTORY))
        self.bind("<F3>", lambda e: self.tabview.set(TAB_REPORTS))
        self.bind("<F4>", lambda e: self.tabview.set(TAB_SETTINGS))

        self.bind("<Alt-c>", lambda e: self._on_invoice(self.invoice_tab.focus_customer))
        self.bind("<Alt-p>", self._on_alt_p)
        self.bind("<Alt-s>", self._on_alt_s)
        self.bind("<Alt-m>", lambda e: self._on_invoice(self.invoice_tab.focus_manual_desc))
        self.bind("<Alt-a>", lambda e: self._on_invoice(self.invoice_tab.add_manual_item))
        self.bind("<Alt-d>", lambda e: self._on_invoice(self.invoice_tab.focus_discount))
        self.bind("<F7>", lambda e: self._on_invoice(self.invoice_tab.cycle_payment_method))
        self.bind("<F9>", lambda e: self._on_invoice(self.invoice_tab.clear_form))
        self.bind("<F11>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=False)))
        self.bind("<F12>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=True)))

        self.bind("<Alt-n>", lambda e: self._on_inventory(self.inventory_tab.show_product_dialog))

    def _on_invoice(self, action):
        if self.current_tab() == TAB_INVOICE:
            action()

    def _on_inventory(self, action):
        if self.current_tab() == TAB_INVENTORY:
            action()

    def _on_alt_p(self, event=None):
        if self.current_tab() == TAB_INVOICE:
            self.invoice_tab.customer_phone_entry.focus_set()
        elif self.current_tab() == TAB_REPORTS:
            self.reports_tab.period_combo.focus_set()

    def _on_alt_s(self, event=None):
        if self.current_tab() == TAB_INVOICE:
            self.invoice_tab.search_entry.focus_set()
        elif self.current_tab() == TAB_INVENTORY:
            self.inventory_tab.search_entry.focus_set()
        elif self.current_tab() == TAB_REPORTS:
            self.reports_tab.search_entry.focus_set()

    def set_status(self, message: str):
        self.status_var.set(message)
