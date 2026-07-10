import platform
import customtkinter as ctk

# Liquid glass desk — soft cool backdrop, frosted panels, precise blue accent
BG = "#E6EBF2"
BG_DEEP = "#DDE4EE"
SURFACE = "#FAFCFE"
SURFACE_ALT = "#F3F6FA"
SURFACE_GLASS = "#F8FAFC"
BORDER = "#CBD5E1"
BORDER_LIGHT = "#E2E8F0"
BORDER_FOCUS = "#3B82F6"

TEXT = "#0F172A"
TEXT_SECONDARY = "#64748B"
TEXT_TERTIARY = "#94A3B8"

ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_SOFT = "#DBEAFE"
ACCENT_STRIPE = "#3B82F6"

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

FONT = (FONT_FAMILY, 12)
FONT_MEDIUM = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_CAPTION = (FONT_FAMILY, 10)
FONT_MONO = ("Consolas", 11)
FONT_TITLE = (FONT_DISPLAY, 20, "bold")
FONT_HEADLINE = (FONT_DISPLAY, 14, "bold")
FONT_LARGE = (FONT_DISPLAY, 28, "bold")

RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16
PAD_CARD = 16


def _merge(defaults, **extra):
    merged = dict(defaults)
    merged.update(extra)
    return merged


def with_shortcut(label: str, key: str) -> str:
    return f"{label}  ·  {key}"


def card_kwargs(**extra):
    return glass_card_kwargs(**extra)


def glass_card_kwargs(**extra):
    return _merge(
        {
            "fg_color": SURFACE,
            "corner_radius": RADIUS_LG,
            "border_width": 1,
            "border_color": BORDER_LIGHT,
        },
        **extra,
    )


def card_with_stripe(parent, **card_extra):
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    stripe = ctk.CTkFrame(outer, fg_color=ACCENT_STRIPE, width=3, corner_radius=2)
    stripe.pack(side="left", fill="y")
    card = ctk.CTkFrame(outer, **glass_card_kwargs(**card_extra))
    card.pack(side="left", fill="both", expand=True)
    return outer, card


def entry_kwargs(width=200, **extra):
    return _merge(
        {
            "width": width,
            "height": 36,
            "fg_color": SURFACE_GLASS,
            "text_color": TEXT,
            "border_color": BORDER,
            "border_width": 1,
            "corner_radius": RADIUS_SM,
            "font": FONT,
        },
        **extra,
    )


def entry_compact(**extra):
    return entry_kwargs(width=120, **extra)


def label_kwargs(**extra):
    return _merge({"text_color": TEXT, "font": FONT}, **extra)


def label_secondary(**extra):
    return _merge({"text_color": TEXT_SECONDARY, "font": FONT_SMALL}, **extra)


def field_label(parent, text: str, shortcut: str = ""):
    label = f"{text}  ·  {shortcut}" if shortcut else text
    return ctk.CTkLabel(parent, text=label, **label_secondary())


def section_title(parent, title: str, subtitle: str = ""):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=title, font=FONT_HEADLINE, text_color=TEXT, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(frame, text=subtitle, font=FONT_SMALL, text_color=TEXT_TERTIARY).pack(anchor="w", pady=(2, 0))
    return frame


def pill(parent, text: str):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_CAPTION,
        text_color=TEXT_TERTIARY,
        fg_color=SURFACE_ALT,
        corner_radius=20,
        height=22,
    )


def button_kwargs(**extra):
    return _merge(
        {
            "fg_color": SURFACE_GLASS,
            "hover_color": SURFACE_ALT,
            "text_color": TEXT,
            "border_width": 1,
            "border_color": BORDER,
            "corner_radius": RADIUS_SM,
            "font": FONT,
            "height": 36,
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
            "height": 38,
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
            "height": 28,
            "width": 28,
        },
        **extra,
    )


def combo_kwargs(width=180, **extra):
    return _merge(
        {
            "width": width,
            "height": 36,
            "fg_color": SURFACE_GLASS,
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
    return _merge({"font": FONT_CAPTION, "text_color": TEXT_TERTIARY, "anchor": "w"}, **extra)


def tabview_kwargs():
    return {
        "fg_color": SURFACE,
        "text_color": TEXT_SECONDARY,
        "segmented_button_fg_color": BG_DEEP,
        "segmented_button_selected_color": SURFACE,
        "segmented_button_selected_hover_color": SURFACE,
        "segmented_button_unselected_color": BG_DEEP,
        "segmented_button_unselected_hover_color": BORDER_LIGHT,
        "corner_radius": RADIUS_LG,
        "border_width": 1,
        "border_color": BORDER_LIGHT,
    }
