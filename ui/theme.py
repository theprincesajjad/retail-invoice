import platform
import customtkinter as ctk

# Warm, welcoming palette — high contrast, easy on aging eyes
BG = "#F0F4F8"
BG_DEEP = "#E2E8F0"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFC"
SURFACE_GLASS = "#FFFFFF"
BORDER = "#94A3B8"
BORDER_LIGHT = "#E2E8F0"
BORDER_FOCUS = "#2563EB"

TEXT = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_TERTIARY = "#64748B"

ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_SOFT = "#DBEAFE"
ACCENT_STRIPE = "#3B82F6"

SUCCESS = "#059669"
SUCCESS_HOVER = "#047857"
SUCCESS_SOFT = "#D1FAE5"
WARNING = "#D97706"
WARNING_SOFT = "#FEF3C7"
DANGER = "#DC2626"
DANGER_SOFT = "#FEE2E2"

if platform.system() == "Darwin":
    FONT_FAMILY = "SF Pro Text"
    FONT_DISPLAY = "SF Pro Display"
elif platform.system() == "Windows":
    FONT_FAMILY = "Segoe UI"
    FONT_DISPLAY = "Segoe UI"
else:
    FONT_FAMILY = "Helvetica Neue"
    FONT_DISPLAY = "Helvetica Neue"

# Accessible sizes — readable without squinting
FONT = (FONT_FAMILY, 14)
FONT_MEDIUM = (FONT_FAMILY, 14, "bold")
FONT_SMALL = (FONT_FAMILY, 13)
FONT_CAPTION = (FONT_FAMILY, 12)
FONT_MONO = ("Courier New", 13)
FONT_TITLE = (FONT_DISPLAY, 22, "bold")
FONT_HEADLINE = (FONT_DISPLAY, 16, "bold")
FONT_LARGE = (FONT_DISPLAY, 32, "bold")
FONT_HERO = (FONT_DISPLAY, 36, "bold")

RADIUS_SM = 10
RADIUS_MD = 14
RADIUS_LG = 18
PAD_CARD = 20

BTN_HEIGHT = 44
BTN_HEIGHT_LG = 52
BTN_HEIGHT_SM = 36


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
    stripe = ctk.CTkFrame(outer, fg_color=ACCENT_STRIPE, width=4, corner_radius=2)
    stripe.pack(side="left", fill="y")
    card = ctk.CTkFrame(outer, **glass_card_kwargs(**card_extra))
    card.pack(side="left", fill="both", expand=True)
    return outer, card


def entry_kwargs(width=200, **extra):
    return _merge(
        {
            "width": width,
            "height": BTN_HEIGHT,
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
    return entry_kwargs(width=140, **extra)


def label_kwargs(**extra):
    return _merge({"text_color": TEXT, "font": FONT}, **extra)


def label_secondary(**extra):
    return _merge({"text_color": TEXT_SECONDARY, "font": FONT_SMALL}, **extra)


def field_label(parent, text: str, hint: str = ""):
    """Plain-language field label. Optional hint shown in smaller text."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=text, font=FONT_MEDIUM, text_color=TEXT, anchor="w").pack(anchor="w")
    if hint:
        ctk.CTkLabel(frame, text=hint, font=FONT_CAPTION, text_color=TEXT_TERTIARY, anchor="w").pack(anchor="w", pady=(2, 0))
    return frame


def section_title(parent, title: str, subtitle: str = ""):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=title, font=FONT_HEADLINE, text_color=TEXT, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(frame, text=subtitle, font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(anchor="w", pady=(4, 0))
    return frame


def pill(parent, text: str, color: str = SURFACE_ALT, text_color: str = TEXT_TERTIARY):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_CAPTION,
        text_color=text_color,
        fg_color=color,
        corner_radius=20,
        height=26,
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
            "height": BTN_HEIGHT,
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
            "height": BTN_HEIGHT_LG,
            "border_width": 0,
        },
        **extra,
    )


def success_button_kwargs(**extra):
    return _merge(
        {
            "fg_color": SUCCESS,
            "hover_color": SUCCESS_HOVER,
            "text_color": "#FFFFFF",
            "corner_radius": RADIUS_SM,
            "font": FONT_MEDIUM,
            "height": BTN_HEIGHT_LG,
            "border_width": 0,
        },
        **extra,
    )


def danger_button_kwargs(**extra):
    return _merge(
        {
            "fg_color": DANGER_SOFT,
            "hover_color": "#FECACA",
            "text_color": DANGER,
            "border_width": 0,
            "corner_radius": RADIUS_SM,
            "font": FONT_MEDIUM,
            "height": BTN_HEIGHT_SM,
            "width": BTN_HEIGHT_SM,
        },
        **extra,
    )


def combo_kwargs(width=180, **extra):
    return _merge(
        {
            "width": width,
            "height": BTN_HEIGHT,
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
    return _merge({"font": FONT_SMALL, "text_color": TEXT_SECONDARY, "anchor": "w"}, **extra)


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
