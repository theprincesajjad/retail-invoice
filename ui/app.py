import sys
import platform
import customtkinter as ctk
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab
from .setup_wizard import needs_setup, show_setup_wizard
from . import theme as T

TAB_HOME = "New Sale"
TAB_INVENTORY = "Products"
TAB_REPORTS = "Sales History"
TAB_SETTINGS = "Setup"

_TAB_KEYS = {
    TAB_HOME: "F1",
    TAB_INVENTORY: "F2",
    TAB_REPORTS: "F3",
    TAB_SETTINGS: "F4",
}

SHORTCUT_HELP = {
    TAB_HOME: "F1–F4 switch tabs  ·  F12 complete sale  ·  F9 new sale",
    TAB_INVENTORY: "Add and manage your product inventory",
    TAB_REPORTS: "View past sales and reprint receipts",
    TAB_SETTINGS: "Store details, printer, and email setup",
}


def get_app_version() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "1.4.0"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Retail Invoice")
        self.geometry("1280x800")
        self.minsize(1024, 680)
        self.configure(fg_color=T.BG)
        self.after(80, self._maximize_window)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_status()
        self._bind_shortcuts()

        self.tabview.set(TAB_HOME)
        self.after(150, self.invoice_tab.focus_customer)
        self.shortcut_var.set(SHORTCUT_HELP[TAB_HOME])

        if needs_setup():
            self.after(300, self._run_setup_wizard)

    def _run_setup_wizard(self):
        show_setup_wizard(self)
        self.settings_tab.load_settings()

    def _maximize_window(self):
        try:
            if platform.system() == "Windows":
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            pass

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=56, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=10)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Retail Invoice", font=T.FONT_TITLE, text_color=T.TEXT).pack(side="left")
        T.pill(left, f"v{get_app_version()}").pack(side="left", padx=(12, 0))

        ctk.CTkFrame(inner, fg_color=T.BORDER_LIGHT, height=1, corner_radius=0).pack(side="bottom", fill="x")

    def _build_tabs(self):
        shell = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        shell.grid(row=1, column=0, sticky="nsew", padx=16, pady=10)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            shell, command=self._on_tab_change, **T.tabview_kwargs(),
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview._segmented_button.configure(font=T.FONT_MEDIUM, height=44)

        for name in (TAB_HOME, TAB_INVENTORY, TAB_REPORTS, TAB_SETTINGS):
            self.tabview.add(name)

        self.invoice_tab = InvoiceTab(self.tabview.tab(TAB_HOME))
        self.invoice_tab.pack(fill="both", expand=True, padx=4, pady=4)

        self.inventory_tab = InventoryTab(self.tabview.tab(TAB_INVENTORY))
        self.inventory_tab.pack(fill="both", expand=True, padx=4, pady=4)

        self.reports_tab = ReportsTab(self.tabview.tab(TAB_REPORTS))
        self.reports_tab.pack(fill="both", expand=True, padx=4, pady=4)

        self.settings_tab = SettingsTab(self.tabview.tab(TAB_SETTINGS))
        self.settings_tab.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_status(self):
        bar = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=36, border_width=0)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24)

        ctk.CTkFrame(inner, fg_color=T.BORDER_LIGHT, height=1, corner_radius=0).pack(side="top", fill="x")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=6)

        self.status_var = ctk.StringVar(value="Ready — go to New Sale to ring up a customer")
        ctk.CTkLabel(row, textvariable=self.status_var, font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY, anchor="w").pack(
            side="left"
        )
        self.shortcut_var = ctk.StringVar(value="")
        ctk.CTkLabel(row, textvariable=self.shortcut_var, font=T.FONT_CAPTION, text_color=T.TEXT_TERTIARY, anchor="e").pack(
            side="right"
        )

    def _on_tab_change(self, *args):
        self.shortcut_var.set(SHORTCUT_HELP.get(self.current_tab(), ""))

    def current_tab(self) -> str:
        return self.tabview.get()

    def _bind_shortcuts(self):
        self.bind("<F1>", lambda e: self._goto(TAB_HOME))
        self.bind("<F2>", lambda e: self._goto(TAB_INVENTORY))
        self.bind("<F3>", lambda e: self._goto(TAB_REPORTS))
        self.bind("<F4>", lambda e: self._goto(TAB_SETTINGS))

        self.bind("<Alt-c>", lambda e: self._on_invoice(self.invoice_tab.focus_customer))
        self.bind("<Alt-p>", self._on_alt_p)
        self.bind("<Alt-s>", self._on_alt_s)
        self.bind("<Alt-m>", lambda e: self._on_invoice(self.invoice_tab.focus_manual_desc))
        self.bind("<Alt-a>", lambda e: self._on_invoice(self.invoice_tab.add_manual_item))
        self.bind("<Alt-d>", lambda e: self._on_invoice(self.invoice_tab.focus_discount))
        self.bind("<Alt-r>", lambda e: self._on_reports(self.reports_tab.load_invoices))
        self.bind("<F7>", lambda e: self._on_invoice(self.invoice_tab.cycle_payment_method))
        self.bind("<F9>", lambda e: self._on_invoice(self.invoice_tab.clear_form))
        self.bind("<F11>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=False)))
        self.bind("<F12>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=True)))
        self.bind("<Alt-n>", lambda e: self._on_inventory(self.inventory_tab.show_product_dialog))

    def _goto(self, tab):
        self.tabview.set(tab)
        self._on_tab_change()

    def _on_invoice(self, action):
        if self.current_tab() == TAB_HOME:
            action()

    def _on_inventory(self, action):
        if self.current_tab() == TAB_INVENTORY:
            action()

    def _on_reports(self, action):
        if self.current_tab() == TAB_REPORTS:
            action()

    def _on_alt_p(self, event=None):
        if self.current_tab() == TAB_HOME:
            self.invoice_tab.customer_phone_entry.focus_set()
        elif self.current_tab() == TAB_REPORTS:
            self.reports_tab.period_combo.focus_set()

    def _on_alt_s(self, event=None):
        tab = self.current_tab()
        if tab == TAB_HOME:
            self.invoice_tab.search_entry.focus_set()
        elif tab == TAB_INVENTORY:
            self.inventory_tab.search_entry.focus_set()
        elif tab == TAB_REPORTS:
            self.reports_tab.search_entry.focus_set()

    def set_status(self, message: str):
        self.status_var.set(message)
