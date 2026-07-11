"""Friendly, large dialogs for confirmations and simple input."""

from __future__ import annotations

import customtkinter as ctk
from . import theme as T


class FriendlyDialog(ctk.CTkToplevel):
    """Base modal with large text and clear Yes/No buttons."""

    def __init__(self, parent, title: str, message: str, width: int = 480):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.configure(fg_color=T.BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        card = ctk.CTkFrame(self, **T.card_kwargs())
        card.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(card, text=title, font=T.FONT_HEADLINE, text_color=T.TEXT, anchor="w").pack(
            anchor="w", padx=24, pady=(24, 8)
        )
        ctk.CTkLabel(
            card, text=message, font=T.FONT, text_color=T.TEXT_SECONDARY,
            anchor="w", justify="left", wraplength=width - 80,
        ).pack(anchor="w", padx=24, pady=(0, 20))

        self._btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._btn_frame.pack(fill="x", padx=24, pady=(0, 24))

        self._center_on(parent, width)

    def _center_on(self, parent, width: int):
        self.update_idletasks()
        h = self.winfo_reqheight()
        px = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{width}x{h}+{px}+{py}")


def ask_yes_no(
    parent,
    title: str,
    message: str,
    *,
    confirm_label: str = "Yes, continue",
    cancel_label: str = "No, go back",
    destructive: bool = False,
) -> bool:
    """Confirm only for meaningful actions. Specific labels beat generic Yes/No."""
    dialog = FriendlyDialog(parent, title, message)
    result = {"value": False}

    def yes():
        result["value"] = True
        dialog.destroy()

    def no():
        dialog.destroy()

    ctk.CTkButton(
        dialog._btn_frame, text=cancel_label, command=no,
        **T.button_kwargs(width=150),
    ).pack(side="left")

    confirm_kw = T.danger_button_kwargs(width=180, height=T.BTN_HEIGHT_LG) if destructive else T.success_button_kwargs(width=180)
    if destructive:
        confirm_kw = {
            "fg_color": T.DANGER,
            "hover_color": "#991B1B",
            "text_color": "#FFFFFF",
            "corner_radius": T.RADIUS_SM,
            "font": T.FONT_MEDIUM,
            "height": T.BTN_HEIGHT_LG,
            "border_width": 0,
            "width": 180,
        }
    ctk.CTkButton(
        dialog._btn_frame, text=confirm_label, command=yes, **confirm_kw,
    ).pack(side="right")

    dialog.wait_window()
    return result["value"]


def show_info(parent, title: str, message: str, *, button_label: str = "Got it"):
    dialog = FriendlyDialog(parent, title, message)
    ctk.CTkButton(
        dialog._btn_frame, text=button_label, command=dialog.destroy,
        **T.primary_button_kwargs(width=140),
    ).pack(side="right")
    dialog.wait_window()


def ask_payment_method(parent, default: str = "Cash") -> str | None:
    """Ask Cash or Card before printing. Returns None if cancelled."""
    dialog = FriendlyDialog(
        parent,
        "How did they pay?",
        "Choose Cash or Card before the receipt is printed.",
        width=480,
    )
    result = {"value": None}

    def choose(method: str):
        result["value"] = method
        dialog.destroy()

    def cancel():
        dialog.destroy()

    ctk.CTkButton(
        dialog._btn_frame, text="Cancel", command=cancel,
        **T.button_kwargs(width=120),
    ).pack(side="left")

    cash_kw = T.success_button_kwargs(width=120) if default == "Cash" else T.button_kwargs(width=120)
    card_kw = T.success_button_kwargs(width=120) if default == "Card" else T.button_kwargs(width=120)

    ctk.CTkButton(
        dialog._btn_frame, text="Card", command=lambda: choose("Card"), **card_kw,
    ).pack(side="right", padx=(10, 0))
    ctk.CTkButton(
        dialog._btn_frame, text="Cash", command=lambda: choose("Cash"), **cash_kw,
    ).pack(side="right")

    dialog.wait_window()
    return result["value"]


def ask_quantity(parent, product_name: str, max_qty: int = 999) -> int | None:
    """Ask how many of a product to add. Returns None if cancelled."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("How many?")
    dialog.configure(fg_color=T.BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    result = {"qty": None}

    card = ctk.CTkFrame(dialog, **T.card_kwargs())
    card.pack(fill="both", expand=True, padx=24, pady=24)

    ctk.CTkLabel(card, text="How many would you like?", font=T.FONT_HEADLINE, text_color=T.TEXT).pack(
        anchor="w", padx=24, pady=(24, 4)
    )
    ctk.CTkLabel(
        card, text=product_name, font=T.FONT, text_color=T.TEXT_SECONDARY,
        wraplength=400, justify="left",
    ).pack(anchor="w", padx=24, pady=(0, 16))

    qty_frame = ctk.CTkFrame(card, fg_color="transparent")
    qty_frame.pack(padx=24, pady=(0, 20))

    qty_var = ctk.IntVar(value=1)

    def dec():
        qty_var.set(max(1, qty_var.get() - 1))
        qty_label.configure(text=str(qty_var.get()))

    def inc():
        qty_var.set(min(max_qty, qty_var.get() + 1))
        qty_label.configure(text=str(qty_var.get()))

    ctk.CTkButton(qty_frame, text="−", width=52, command=dec, **T.button_kwargs()).pack(side="left", padx=(0, 12))
    qty_label = ctk.CTkLabel(qty_frame, text="1", font=T.FONT_HERO, text_color=T.TEXT, width=80)
    qty_label.pack(side="left")
    ctk.CTkButton(qty_frame, text="+", width=52, command=inc, **T.button_kwargs()).pack(side="left", padx=(12, 0))

    if max_qty < 999:
        ctk.CTkLabel(
            card, text=f"Available in stock: {max_qty}", font=T.FONT_CAPTION, text_color=T.TEXT_TERTIARY,
        ).pack(padx=24, pady=(0, 8))

    btn_frame = ctk.CTkFrame(card, fg_color="transparent")
    btn_frame.pack(fill="x", padx=24, pady=(0, 24))

    def confirm():
        result["qty"] = qty_var.get()
        dialog.destroy()

    ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, **T.button_kwargs(width=120)).pack(side="left")
    ctk.CTkButton(btn_frame, text="Add to sale", command=confirm, **T.success_button_kwargs(width=160)).pack(side="right")

    dialog.update_idletasks()
    w, h = 440, dialog.winfo_reqheight()
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
    dialog.geometry(f"{w}x{h}+{px}+{py}")

    dialog.wait_window()
    return result["qty"]
