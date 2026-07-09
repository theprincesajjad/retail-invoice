import platform
import customtkinter as ctk

# 2026 retail desk — cool paper, slate ink, one confident blue accent
BG = "#F4F6F9"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F0F3F8"
BORDER = "#DDE3EC"
BORDER_FOCUS = "#1D4ED8"

TEXT = "#0F172A"
TEXT_SECONDARY = "#64748B"
TEXT_TERTIARY = "#94A3B8"

ACCENT = "#1D4ED8"
ACCENT_HOVER = "#1E40AF"
ACCENT_SOFT = "#DBEAFE"
ACCENT_STRIPE = "#1D4ED8"

SUCCESS = "#059669"
WARNING = "#D97706"
DANGER = "#DC2626"
DANGER_SOFT = "#FEF2F2"

if platform.system() == "Darwin":
    FONT_FAMILY = "SF Pro Text"
    FONT_DISPLAY = "SF Pro Display"
elif platform.system() == "Windows":
    FONT_FAMILY = "Segoe UI"
    FONT_DISPLAY = "Segoe UI"
else:
    FONT_FAMILY = "Helvetica Neue"
    FONT_DISPLAY = "Helvetica Neue"

FONT = (FONT_FAMILY, 13)
FONT_MEDIUM = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 12)
FONT_TITLE = (FONT_DISPLAY, 24)
FONT_HEADLINE = (FONT_DISPLAY, 16, "bold")
FONT_LARGE = (FONT_DISPLAY, 30, "bold")

RADIUS_SM = 10
RADIUS_MD = 14
RADIUS_LG = 18


def _merge(defaults, **extra):
    merged = dict(defaults)
    merged.update(extra)
    return merged


def with_shortcut(label: str, key: str) -> str:
    """Button label with visible shortcut."""
    return f"{label}  ·  {key}"


def card_kwargs(**extra):
    return _merge(
        {"fg_color": SURFACE, "corner_radius": RADIUS_MD, "border_width": 1, "border_color": BORDER},
        **extra,
    )


def card_with_stripe(parent, **card_extra):
    """Card frame with left accent stripe."""
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    stripe = ctk.CTkFrame(outer, fg_color=ACCENT_STRIPE, width=4, corner_radius=2)
    stripe.pack(side="left", fill="y", padx=(0, 0))
    card = ctk.CTkFrame(outer, **card_kwargs(**card_extra))
    card.pack(side="left", fill="both", expand=True)
    return outer, card


def entry_kwargs(width=200, **extra):
    return _merge(
        {
            "width": width,
            "height": 38,
            "fg_color": SURFACE_ALT,
            "text_color": TEXT,
            "border_color": BORDER,
            "border_width": 1,
            "corner_radius": RADIUS_SM,
            "font": FONT,
        },
        **extra,
    )


def entry_compact(**extra):
    return entry_kwargs(width=132, **extra)


def label_kwargs(**extra):
    return _merge({"text_color": TEXT, "font": FONT}, **extra)


def label_secondary(**extra):
    return _merge({"text_color": TEXT_SECONDARY, "font": FONT_SMALL}, **extra)


def section_title(parent, title: str, subtitle: str = ""):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=title, font=FONT_HEADLINE, text_color=TEXT, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(frame, text=subtitle, **label_secondary()).pack(anchor="w", pady=(3, 0))
    return frame


def shortcut_chip(parent, text: str):
    """Small shortcut badge for toolbars."""
    return ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_SMALL,
        text_color=TEXT_TERTIARY,
        fg_color=SURFACE_ALT,
        corner_radius=6,
        width=36,
        height=22,
    )


def button_kwargs(**extra):
    return _merge(
        {
            "fg_color": SURFACE,
            "hover_color": SURFACE_ALT,
            "text_color": TEXT,
            "border_width": 1,
            "border_color": BORDER,
            "corner_radius": RADIUS_SM,
            "font": FONT,
            "height": 38,
        },
        **extra,
    )


def primary_button_kwargs(**extra):
    return _merge(
        {
            "fg_color": ACCENT,
            "hover_color": ACCENT_HOVER,
            "text_color": "#FFFFFF",
            "corner_radius": RADIUS_SM,
            "font": FONT_MEDIUM,
            "height": 40,
            "border_width": 0,
        },
        **extra,
    )


def danger_button_kwargs(**extra):
    return _merge(
        {
            "fg_color": DANGER_SOFT,
            "hover_color": "#FEE2E2",
            "text_color": DANGER,
            "border_width": 0,
            "corner_radius": RADIUS_SM,
            "font": FONT,
            "height": 32,
            "width": 32,
        },
        **extra,
    )


def combo_kwargs(width=180, **extra):
    return _merge(
        {
            "width": width,
            "height": 38,
            "fg_color": SURFACE_ALT,
            "text_color": TEXT,
            "border_color": BORDER,
            "button_color": BORDER,
            "button_hover_color": TEXT_TERTIARY,
            "dropdown_fg_color": SURFACE,
            "dropdown_text_color": TEXT,
            "dropdown_hover_color": ACCENT_SOFT,
            "corner_radius": RADIUS_SM,
            "font": FONT,
            "dropdown_font": FONT,
        },
        **extra,
    )


def table_header_kwargs(**extra):
    return _merge({"font": FONT_SMALL, "text_color": TEXT_SECONDARY, "anchor": "w"}, **extra)
