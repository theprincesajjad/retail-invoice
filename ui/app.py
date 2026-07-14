import sys
import platform
import customtkinter as ctk
from pathlib import Path
from .invoice_tab import InvoiceTab
from .inventory_tab import InventoryTab
from .reports_tab import ReportsTab
from .settings_tab import SettingsTab
from .setup_wizard import needs_setup, show_setup_wizard
from .toast import ToastHost
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
    TAB_HOME: "F1 New  ·  F10 Save  ·  F11 Preview  ·  F12 Complete + Print",
    TAB_INVENTORY: "Alt+N add product  ·  F5 Save Next  ·  F6 Save Close  ·  F1–F4 tabs",
    TAB_REPORTS: "Alt+S search  ·  Alt+R refresh  ·  F1–F4 tabs",
    TAB_SETTINGS: "Store details, printer, and receipt design",
}


def get_app_version() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "1.5.0"


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

        self.toast_host = ToastHost(self)

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
        # Wireframe: RETAIL INVOICE | logo + store name | tabs — one chrome bar
        header = ctk.CTkFrame(self, fg_color=T.SURFACE, corner_radius=0, height=64, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(18, 8), pady=8)
        ctk.CTkLabel(left, text="RETAIL INVOICE", font=T.FONT_TITLE, text_color=T.TEXT).pack(side="left")
        version = get_app_version()
        pill_color = T.WARNING_SOFT if "beta" in version.lower() else T.SURFACE_ALT
        pill_text = T.WARNING if "beta" in version.lower() else T.TEXT_TERTIARY
        T.pill(left, f"v{version}", color=pill_color, text_color=pill_text).pack(side="left", padx=(10, 0))

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=1, sticky="w", padx=8, pady=6)
        self.header_logo = ctk.CTkLabel(brand, text="", width=40, height=40)
        self.header_logo.pack(side="left", padx=(0, 10))
        self.header_business = ctk.CTkLabel(
            brand, text="", font=T.FONT_HEADLINE, text_color=T.TEXT,
        )
        self.header_business.pack(side="left")
        self.refresh_header_brand()

        ctk.CTkFrame(header, fg_color=T.BORDER_LIGHT, height=1, corner_radius=0).grid(
            row=1, column=0, columnspan=2, sticky="ew"
        )

    def refresh_header_brand(self):
        """Load store logo + name into the header (wireframe center brand)."""
        from database import get_all_settings
        from receipt_builder import resolve_logo_path

        settings = get_all_settings()
        name = (settings.get("business_name") or "My Business").strip()
        self.header_business.configure(text=f"—  {name.upper()}  —")

        logo_path = resolve_logo_path(settings)
        if logo_path:
            try:
                from PIL import Image
                img = Image.open(logo_path)
                img.thumbnail((40, 40))
                self._header_logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.header_logo.configure(image=self._header_logo_img, text="")
                return
            except Exception:
                pass
        self.header_logo.configure(image=None, text="◆", font=T.FONT_HEADLINE, text_color=T.ACCENT)

    def _build_tabs(self):
        shell = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        shell.grid(row=1, column=0, sticky="nsew", padx=16, pady=(6, 10))
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(
            shell, command=self._on_tab_change, **T.tabview_kwargs(),
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")

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

        self.tabview.set(TAB_HOME)

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
        current = self.current_tab()
        self.shortcut_var.set(SHORTCUT_HELP.get(current, ""))

    def current_tab(self) -> str:
        return self.tabview.get()

    def _bind_shortcuts(self):
        # Wireframe hotkeys
        self.bind("<F1>", lambda e: self._on_f1_new())
        self.bind("<F2>", lambda e: self._goto(TAB_INVENTORY))
        self.bind("<F3>", lambda e: self._goto(TAB_REPORTS))
        self.bind("<F4>", lambda e: self._goto(TAB_SETTINGS))
        self.bind("<F10>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=False)))
        self.bind("<F11>", lambda e: self._on_invoice(self.invoice_tab.preview_receipt))
        self.bind("<F12>", lambda e: self._on_invoice(lambda: self.invoice_tab.save(print_rcpt=True)))

        self.bind("<Alt-c>", lambda e: self._on_invoice(self.invoice_tab.focus_customer))
        self.bind("<Alt-p>", self._on_alt_p)
        self.bind("<Alt-s>", self._on_alt_s)
        self.bind("<Alt-m>", lambda e: self._on_invoice(self.invoice_tab.focus_manual_desc))
        self.bind("<Alt-a>", lambda e: self._on_invoice(self.invoice_tab.add_manual_item))
        self.bind("<Alt-d>", lambda e: self._on_invoice(self.invoice_tab.focus_discount))
        self.bind("<Alt-r>", lambda e: self._on_reports(self.reports_tab.load_invoices))
        self.bind("<Alt-n>", lambda e: self._on_inventory(self.inventory_tab.show_product_dialog))

    def _on_f1_new(self):
        self._goto(TAB_HOME)
        self.invoice_tab.clear_form()

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

    def set_status(self, message: str, *, toast_kind: str | None = None):
        self.status_var.set(message)
        if toast_kind:
            self.toast_host.show(message, kind=toast_kind)
