"""Non-blocking toast notifications — Sonner-inspired feedback for desktop."""

from __future__ import annotations

import customtkinter as ctk
from . import theme as T

# Toast stays visible briefly, then fades out of the way.
# Occasional feedback (sale complete) — short enough not to annoy, long enough to read.
_TOAST_MS = {
    "success": 2800,
    "info": 2600,
    "warning": 3200,
    "error": 4000,
}

_STYLES = {
    "success": {"bg": T.SUCCESS_SOFT, "fg": T.SUCCESS, "border": "#A7F3D0"},
    "info": {"bg": T.ACCENT_SOFT, "fg": T.ACCENT, "border": "#BFDBFE"},
    "warning": {"bg": T.WARNING_SOFT, "fg": T.WARNING, "border": "#FDE68A"},
    "error": {"bg": T.DANGER_SOFT, "fg": T.DANGER, "border": "#FECACA"},
}


class ToastHost:
    """One host per app window. Stacks toasts from the bottom."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._active: list[ctk.CTkFrame] = []

    def show(self, message: str, kind: str = "info", title: str = ""):
        kind = kind if kind in _STYLES else "info"
        style = _STYLES[kind]

        toast = ctk.CTkFrame(
            self.root,
            fg_color=style["bg"],
            corner_radius=T.RADIUS_MD,
            border_width=1,
            border_color=style["border"],
        )

        inner = ctk.CTkFrame(toast, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        if title:
            ctk.CTkLabel(
                inner, text=title, font=T.FONT_MEDIUM, text_color=style["fg"], anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                inner, text=message, font=T.FONT_SMALL, text_color=T.TEXT, anchor="w",
                wraplength=360, justify="left",
            ).pack(anchor="w", pady=(2, 0))
        else:
            ctk.CTkLabel(
                inner, text=message, font=T.FONT_MEDIUM, text_color=style["fg"],
                anchor="w", wraplength=360, justify="left",
            ).pack(anchor="w")

        self._active.append(toast)
        self._relayout()

        # Auto-dismiss — no animation on keyboard-driven flows; toast is occasional delight
        delay = _TOAST_MS[kind]
        self.root.after(delay, lambda: self._dismiss(toast))

        # Click to dismiss immediately (agency)
        for widget in (toast, inner):
            widget.bind("<Button-1>", lambda e, t=toast: self._dismiss(t))

    def _relayout(self):
        self.root.update_idletasks()
        # Stack from bottom-right, above the status bar
        base_y = self.root.winfo_height() - 56
        right = self.root.winfo_width() - 24
        for toast in reversed(self._active):
            toast.update_idletasks()
            tw = max(toast.winfo_reqwidth(), 280)
            th = toast.winfo_reqheight()
            x = max(24, right - tw)
            y = max(60, base_y - th)
            toast.place(x=x, y=y, width=tw)
            toast.lift()
            base_y = y - 10

    def _dismiss(self, toast: ctk.CTkFrame):
        if toast in self._active:
            self._active.remove(toast)
            try:
                toast.destroy()
            except Exception:
                pass
            self._relayout()


def toast(parent, message: str, kind: str = "info", title: str = ""):
    """Show a toast on the nearest App window."""
    root = parent.winfo_toplevel()
    host = getattr(root, "toast_host", None)
    if host is None:
        host = ToastHost(root)
        root.toast_host = host
    host.show(message, kind=kind, title=title)
