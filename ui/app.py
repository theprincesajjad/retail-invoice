import sys
import platform
import customtkinter as ctk
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab
from . import theme as T

TAB_HOME = "Home (F1)"
TAB_INVENTORY = "Stock (F2)"
TAB_REPORTS = "Reports (F3)"
TAB_SETTINGS = "Settings (F4)"

SHORTCUT_HELP = {
    TAB_HOME: "Alt+C name · Alt+S stock · Enter add · Alt+D discount · F7 pay · F9 clear · F11 save · F12 print",
    TAB_INVENTORY: "Alt+N new product · Alt+S search · Tab moves between fields in form",
    TAB_REPORTS: "Alt+S search · Alt+P period · Alt+R refresh · View · Print · Email",
    TAB_SETTINGS: "Save settings at bottom",
}


def get_app_version() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "1.2.0"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Retail Invoice  {get_app_version()}")
        # Launch sized to the current screen and maximize where supported,
        # so action buttons are never cut off on smaller displays.
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{max(1100, sw)}x{max(720, sh)}+0+0")
        self.minsize(1020, 680)
        try:
            if platform.system() == "Windows":
                # Most reliable "full screen" behavior for desktop apps.
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            pass
        self.configure(fg_color=T.BG)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_status()
        self._bind_shortcuts()

        self.tabview.set(TAB_HOME)
        self.after(150, self.invoice_tab.focus_customer)
        self.shortcut_var.set(SHORTCUT_HELP[TAB_HOME])

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=58, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=24, pady=10)
        stripe = ctk.CTkFrame(left, fg_color=T.ACCENT_STRIPE, width=4, height=28, corner_radius=2)
        stripe.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(left, text="Retail Invoice", font=T.FONT_TITLE, text_color=T.TEXT).pack(side="left")
        ctk.CTkLabel(left, text=f"v{get_app_version()}", font=T.FONT_SMALL, text_color=T.TEXT_TERTIARY).pack(
            side="left", padx=(10, 0)
        )

    def _build_tabs(self):
        shell = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        shell.grid(row=1, column=0, sticky="nsew", padx=22, pady=(10, 10))
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
            command=self._on_tab_change,
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")

        for name in (TAB_HOME, TAB_INVENTORY, TAB_REPORTS, TAB_SETTINGS):
            self.tabview.add(name)

        self.invoice_tab = InvoiceTab(self.tabview.tab(TAB_HOME))
        self.invoice_tab.pack(fill="both", expand=True)

        self.inventory_tab = InventoryTab(self.tabview.tab(TAB_INVENTORY))
        self.inventory_tab.pack(fill="both", expand=True)

        self.reports_tab = ReportsTab(self.tabview.tab(TAB_REPORTS))
        self.reports_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(self.tabview.tab(TAB_SETTINGS))
        self.settings_tab.pack(fill="both", expand=True)

    def _build_status(self):
        bar = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=36, border_width=1, border_color=T.BORDER)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        self.status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(bar, textvariable=self.status_var, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w").pack(
            side="left", padx=24
        )
        self.shortcut_var = ctk.StringVar(value="")
        ctk.CTkLabel(bar, textvariable=self.shortcut_var, font=T.FONT_SMALL, text_color=T.TEXT_TERTIARY, anchor="e").pack(
            side="right", padx=24
        )

    def _on_tab_change(self, *args):
        tab = self.current_tab()
        self.shortcut_var.set(SHORTCUT_HELP.get(tab, ""))

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
