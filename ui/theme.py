"""Classic POS terminal theme inspired by retro retail systems."""

FONT = ("Courier New", 12)
FONT_BOLD = ("Courier New", 12, "bold")
FONT_HEADER = ("Courier New", 11, "bold")
FONT_TOTAL = ("Courier New", 18, "bold")
FONT_SMALL = ("Courier New", 10)

BG = "#000080"
BG_PANEL = "#000066"
TEXT = "#FFFFFF"
HEADER_BG = "#AA00AA"
HEADER_TEXT = "#FFFFFF"
INPUT_BG = "#008080"
INPUT_TEXT = "#FFFFFF"
INPUT_BORDER = "#FFFFFF"
LABEL_ACCENT = "#00FFFF"
FOOTER_BG = "#AA00AA"
FOOTER_TEXT = "#FFFFFF"
BTN_BG = "#006666"
BTN_HOVER = "#00AAAA"
BTN_TEXT = "#FFFFFF"
BTN_PRIMARY_BG = "#008800"
BTN_PRIMARY_HOVER = "#00AA00"
BTN_PRIMARY_TEXT = "#FFFFFF"
BTN_DANGER_BG = "#880000"
BTN_DANGER_HOVER = "#AA0000"
BTN_DANGER_TEXT = "#FFAAAA"
WARN = "#FF6666"
TAB_SELECTED = "#AA00AA"
TAB_UNSELECTED = "#000066"
TAB_HOVER = "#660066"
BORDER = "#FFFFFF"


def entry_kwargs(width=200):
    return dict(
        width=width,
        fg_color=INPUT_BG,
        text_color=INPUT_TEXT,
        border_color=INPUT_BORDER,
        corner_radius=0,
        font=FONT,
    )


def _merge_kwargs(defaults, **extra):
    merged = dict(defaults)
    merged.update(extra)
    return merged


def label_kwargs(**extra):
    return _merge_kwargs({"text_color": TEXT, "font": FONT}, **extra)


def header_label_kwargs(width=100, **extra):
    return _merge_kwargs(
        {
            "width": width,
            "anchor": "w",
            "font": FONT_HEADER,
            "text_color": HEADER_TEXT,
            "fg_color": HEADER_BG,
        },
        **extra,
    )


def button_kwargs(**extra):
    return _merge_kwargs(
        {
            "fg_color": BTN_BG,
            "hover_color": BTN_HOVER,
            "text_color": BTN_TEXT,
            "corner_radius": 0,
            "font": FONT,
        },
        **extra,
    )


def primary_button_kwargs(**extra):
    return _merge_kwargs(
        {
            "fg_color": BTN_PRIMARY_BG,
            "hover_color": BTN_PRIMARY_HOVER,
            "text_color": BTN_PRIMARY_TEXT,
            "corner_radius": 0,
            "font": FONT_BOLD,
        },
        **extra,
    )


def danger_button_kwargs(**extra):
    return _merge_kwargs(
        {
            "fg_color": BTN_DANGER_BG,
            "hover_color": BTN_DANGER_HOVER,
            "text_color": BTN_DANGER_TEXT,
            "corner_radius": 0,
            "font": FONT,
        },
        **extra,
    )


def panel_kwargs(**extra):
    return _merge_kwargs(
        {"fg_color": BG_PANEL, "corner_radius": 0, "border_width": 1, "border_color": BORDER},
        **extra,
    )


def combo_kwargs(width=160):
    return dict(
        width=width,
        fg_color=INPUT_BG,
        text_color=INPUT_TEXT,
        border_color=INPUT_BORDER,
        button_color=BTN_BG,
        button_hover_color=BTN_HOVER,
        corner_radius=0,
        font=FONT,
    )
