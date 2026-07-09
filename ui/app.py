import sys
import customtkinter as ctk
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab


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

TAB_INVOICE = "New Invoice (F1)"
TAB_INVENTORY = "Inventory (F2)"
TAB_REPORTS = "Reports (F3)"
TAB_SETTINGS = "Settings (F4)"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Retail Invoice System v{get_app_version()} (DOS Mode)")
        self.geometry("1100x700")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")

        self.bg_color = "#000000"
        self.text_color = "#00FF00"
        self.configure(fg_color=self.bg_color)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.bg_color,
            text_color=self.text_color,
            segmented_button_fg_color="#002200",
            segmented_button_selected_color="#003300",
            segmented_button_selected_hover_color="#00AA00",
            segmented_button_unselected_color="#001100",
            segmented_button_unselected_hover_color="#003300",
            corner_radius=0,
        )
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

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

        self.status_var = ctk.StringVar(value="Ready | F1-F4: Tabs | Alt+keys: Context shortcuts")
        self.status_bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            anchor="w",
            padx=10,
            height=30,
            fg_color="#002200",
            text_color=self.text_color,
            corner_radius=0,
        )
        self.status_bar.grid(row=1, column=0, sticky="ew")

        self._bind_shortcuts()

    def current_tab(self) -> str:
        return self.tabview.get()

    def _bind_shortcuts(self):
        # Global tab navigation
        self.bind("<F1>", lambda e: self.tabview.set(TAB_INVOICE))
        self.bind("<F2>", lambda e: self.tabview.set(TAB_INVENTORY))
        self.bind("<F3>", lambda e: self.tabview.set(TAB_REPORTS))
        self.bind("<F4>", lambda e: self.tabview.set(TAB_SETTINGS))

        # Invoice tab shortcuts
        self.bind("<Alt-c>", lambda e: self._on_invoice_tab(self.invoice_tab.customer_name_entry.focus_set))
        self.bind("<Alt-p>", self._on_alt_p)
        self.bind("<Alt-s>", self._on_alt_s)
        self.bind("<Alt-m>", lambda e: self._on_invoice_tab(self.invoice_tab.man_desc.focus_set))
        self.bind("<Alt-a>", lambda e: self._on_invoice_tab(self.invoice_tab.add_manual_item))
        self.bind("<F12>", lambda e: self._on_invoice_tab(lambda: self.invoice_tab.save(print_rcpt=True)))
        self.bind("<F11>", lambda e: self._on_invoice_tab(lambda: self.invoice_tab.save(print_rcpt=False)))
        self.bind("<F9>", lambda e: self._on_invoice_tab(self.invoice_tab.clear_form))

        # Inventory tab shortcuts
        self.bind("<Alt-n>", lambda e: self._on_inventory_tab(self.inventory_tab.show_product_dialog))

        # Reports tab shortcuts
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
        self.status_var.set(message)
