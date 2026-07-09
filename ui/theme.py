import customtkinter as ctk
import sys
import platform

# Refined, calm palette — light surfaces, one accent, no decorative noise
BG = "#F2F2F7"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#FAFAFC"
BORDER = "#E5E5EA"
BORDER_FOCUS = "#0071E3"

TEXT = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
TEXT_TERTIARY = "#AEAEB2"

ACCENT = "#0071E3"
ACCENT_HOVER = "#0077ED"
ACCENT_SOFT = "#E8F1FC"

SUCCESS = "#34C759"
WARNING = "#FF9500"
DANGER = "#FF3B30"
DANGER_SOFT = "#FFF0EF"

TAB_BAR = "#FFFFFF"
TAB_SELECTED = "#F2F2F7"

# System-native UI font on each platform
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
FONT_CAPTION = (FONT_FAMILY, 11)
FONT_TITLE = (FONT_DISPLAY, 22)
FONT_HEADLINE = (FONT_DISPLAY, 17, "bold")
FONT_LARGE = (FONT_DISPLAY, 28, "bold")

RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16


def _merge(defaults, **extra):
    merged = dict(defaults)
    merged.update(extra)
    return merged


def card_kwargs(**extra):
    return _merge(
        {"fg_color": SURFACE, "corner_radius": RADIUS_MD, "border_width": 1, "border_color": BORDER},
        **extra,
    )


def entry_kwargs(width=200, **extra):
    return _merge(
        {
            "width": width,
            "height": 36,
            "fg_color": SURFACE_ALT,
            "text_color": TEXT,
            "border_color": BORDER,
            "border_width": 1,
            "corner_radius": RADIUS_SM,
            "font": FONT,
        },
        **extra,
    )


def label_kwargs(**extra):
    return _merge({"text_color": TEXT, "font": FONT}, **extra)


def label_secondary(**extra):
    return _merge({"text_color": TEXT_SECONDARY, "font": FONT_SMALL}, **extra)


def section_title(text_widget_parent, title: str, subtitle: str = ""):
    """Return a frame with section header — caller packs it."""
    frame = ctk.CTkFrame(text_widget_parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=title, font=FONT_HEADLINE, text_color=TEXT, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(frame, text=subtitle, **label_secondary()).pack(anchor="w", pady=(2, 0))
    return frame


def button_kwargs(**extra):
    return _merge(
        {
            "fg_color": SURFACE_ALT,
            "hover_color": BORDER,
            "text_color": TEXT,
            "border_width": 1,
            "border_color": BORDER,
            "corner_radius": RADIUS_SM,
            "font": FONT_MEDIUM,
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
            "height": 40,
            "border_width": 0,
        },
        **extra,
    )


def danger_button_kwargs(**extra):
    return _merge(
        {
            "fg_color": DANGER_SOFT,
            "hover_color": "#FFE2E0",
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
            "height": 36,
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
        },
        **extra,
    )


def table_header_kwargs(**extra):
    return _merge(
        {"font": FONT_SMALL, "text_color": TEXT_SECONDARY, "anchor": "w"},
        **extra,
    )


def segmented_kwargs(**extra):
    return _merge(
        {
            "fg_color": SURFACE_ALT,
            "selected_color": SURFACE,
            "selected_hover_color": SURFACE,
            "unselected_color": SURFACE_ALT,
            "unselected_hover_color": BORDER,
            "text_color": TEXT,
            "font": FONT_SMALL,
            "corner_radius": RADIUS_SM,
        },
        **extra,
    )
