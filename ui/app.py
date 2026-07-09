import customtkinter as ctk
import sys
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab
from . import theme as T

TAB_INVOICE = "Invoice (F1)"
TAB_INVENTORY = "Stock (F2)"
TAB_REPORTS = "Reports (F3)"
TAB_SETTINGS = "Settings (F4)"


def get_app_version() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    version_file = base / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "1.0.0"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Retail POS v{get_app_version()}")
        self.geometry("1150x720")
        self.minsize(950, 620)

        ctk.set_appearance_mode("dark")

        self.configure(fg_color=T.BG)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=T.BG,
            text_color=T.TEXT,
            segmented_button_fg_color=T.TAB_UNSELECTED,
            segmented_button_selected_color=T.TAB_SELECTED,
            segmented_button_selected_hover_color=T.HEADER_BG,
            segmented_button_unselected_color=T.TAB_UNSELECTED,
            segmented_button_unselected_hover_color=T.TAB_HOVER,
            corner_radius=0,
        )
        self.tabview.grid(row=0, column=0, padx=8, pady=(8, 0), sticky="nsew")

        self.tabview.add(TAB_INVOICE)
        self.tabview.add(TAB_INVENTORY)
        self.tabview.add(TAB_REPORTS)
        self.tabview.add(TAB_SETTINGS)

        self.invoice_tab = InvoiceTab(self.tabview.tab(TAB_INVOICE))
        self.invoice_tab.pack(fill="both", expand=True)

        self.inventory_tab = InventoryTab(self.tabview.tab(TAB_INVENTORY))
        self.inventory_tab.pack(fill="both", expand=True)

        self.reports_tab = ReportsTab(self.tabview.tab(TAB_REPORTS))
        self.reports_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(self.tabview.tab(TAB_SETTINGS))
        self.settings_tab.pack(fill="both", expand=True)

        self.footer_var = ctk.StringVar(
            value=(
                "F1 Invoice | F2 Stock | F3 Reports | F4 Settings | "
                "F7 Payment | F9 Clear | F11 Save | F12 Print | Enter Add Line"
            )
        )
        self.footer_bar = ctk.CTkLabel(
            self,
            textvariable=self.footer_var,
            anchor="w",
            padx=12,
            height=28,
            fg_color=T.FOOTER_BG,
            text_color=T.FOOTER_TEXT,
            corner_radius=0,
            font=T.FONT_SMALL,
        )
        self.footer_bar.grid(row=1, column=0, sticky="ew")

        self._bind_shortcuts()

    def current_tab(self) -> str:
        return self.tabview.get()

    def _bind_shortcuts(self):
        self.bind("<F1>", lambda e: self.tabview.set(TAB_INVOICE))
        self.bind("<F2>", lambda e: self.tabview.set(TAB_INVENTORY))
        self.bind("<F3>", lambda e: self.tabview.set(TAB_REPORTS))
        self.bind("<F4>", lambda e: self.tabview.set(TAB_SETTINGS))

        self.bind("<Alt-c>", lambda e: self._on_invoice_tab(self.invoice_tab.customer_name_entry.focus_set))
        self.bind("<Alt-p>", self._on_alt_p)
        self.bind("<Alt-s>", self._on_alt_s)
        self.bind("<Alt-m>", lambda e: self._on_invoice_tab(self.invoice_tab.man_desc.focus_set))
        self.bind("<Alt-a>", lambda e: self._on_invoice_tab(self.invoice_tab.add_manual_item))
        self.bind("<F7>", lambda e: self._on_invoice_tab(self.invoice_tab.cycle_payment_method))
        self.bind("<F12>", lambda e: self._on_invoice_tab(lambda: self.invoice_tab.save(print_rcpt=True)))
        self.bind("<F11>", lambda e: self._on_invoice_tab(lambda: self.invoice_tab.save(print_rcpt=False)))
        self.bind("<F9>", lambda e: self._on_invoice_tab(self.invoice_tab.clear_form))

        self.bind("<Alt-n>", lambda e: self._on_inventory_tab(self.inventory_tab.show_product_dialog))
        self.bind("<Alt-r>", lambda e: self._on_reports_tab(self.reports_tab.load_invoices))

    def _on_invoice_tab(self, action):
        if self.current_tab() == TAB_INVOICE:
            action()

    def _on_inventory_tab(self, action):
        if self.current_tab() == TAB_INVENTORY:
            action()

    def _on_reports_tab(self, action):
        if self.current_tab() == TAB_REPORTS:
            action()

    def _on_alt_p(self, event=None):
        tab = self.current_tab()
        if tab == TAB_INVOICE:
            self.invoice_tab.customer_phone_entry.focus_set()
        elif tab == TAB_REPORTS:
            self.reports_tab.period_combo.focus_set()

    def _on_alt_s(self, event=None):
        tab = self.current_tab()
        if tab == TAB_INVOICE:
            self.invoice_tab.search_entry.focus_set()
        elif tab == TAB_INVENTORY:
            self.inventory_tab.search_entry.focus_set()

    def set_status(self, message: str):
        self.footer_var.set(message)
