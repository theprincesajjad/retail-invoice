"""First-run setup wizard — optional, skippable at any time."""

from __future__ import annotations

import customtkinter as ctk
from database import get_setting, save_setting
from . import theme as T


def needs_setup() -> bool:
    """True when the app has never been configured."""
    return get_setting("setup_complete", "") != "1"


def mark_setup_complete():
    save_setting("setup_complete", "1")


def show_setup_wizard(parent) -> bool:
    """Show welcome wizard. Everything is optional — Skip anytime."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Welcome!")
    dialog.configure(fg_color=T.BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(skipped=True))

    completed = {"value": False}
    step = {"n": 0}

    card = ctk.CTkFrame(dialog, **T.card_kwargs())
    card.pack(fill="both", expand=True, padx=28, pady=28)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(28, 8))
    title_lbl = ctk.CTkLabel(header, text="", font=T.FONT_TITLE, text_color=T.TEXT, anchor="w")
    title_lbl.pack(anchor="w")
    subtitle_lbl = ctk.CTkLabel(
        header, text="", font=T.FONT, text_color=T.TEXT_SECONDARY,
        anchor="w", justify="left", wraplength=500,
    )
    subtitle_lbl.pack(anchor="w", pady=(8, 0))

    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=28, pady=16)

    entries: dict[str, ctk.CTkEntry] = {}

    def clear_body():
        for w in body.winfo_children():
            w.destroy()

    def show_step_0():
        clear_body()
        title_lbl.configure(text="Welcome to Retail Invoice")
        subtitle_lbl.configure(
            text="A quick optional setup — fill in what you know, or skip and start selling right away. "
                 "You can change everything later in the Setup tab."
        )
        ctk.CTkLabel(
            body,
            text="✓  Ring up sales and print receipts\n"
                 "✓  Track your inventory\n"
                 "✓  View sales history and reports\n\n"
                 "Nothing is required. Skip anytime.",
            font=T.FONT, text_color=T.TEXT, justify="left", anchor="w",
        ).pack(anchor="w", pady=12)

    def show_step_1():
        clear_body()
        title_lbl.configure(text="Your store details")
        subtitle_lbl.configure(
            text="Optional — this appears on receipts. Leave blank and edit later in Setup."
        )

        for label, key, placeholder in [
            ("Store name", "business_name", "e.g. Main Street Electronics"),
            ("Address", "business_address", "123 Main St, Toronto, ON"),
            ("Phone number", "business_phone", "(416) 555-0123"),
        ]:
            T.field_label(body, label).pack(anchor="w", pady=(8, 0))
            e = ctk.CTkEntry(body, placeholder_text=placeholder, **T.entry_kwargs())
            e.pack(fill="x", pady=(4, 4))
            val = get_setting(key, "")
            if val:
                e.insert(0, val)
            entries[key] = e

    def show_step_2():
        clear_body()
        title_lbl.configure(text="Tax rate")
        subtitle_lbl.configure(
            text="Optional — defaults to 13% (Ontario HST). Change anytime in Setup."
        )

        T.field_label(body, "Tax rate (%)").pack(anchor="w", pady=(8, 0))
        tax_entry = ctk.CTkEntry(body, placeholder_text="13", **T.entry_kwargs(width=120))
        tax_entry.pack(anchor="w", pady=(4, 4))
        try:
            rate = float(get_setting("tax_rate", "0.13"))
            tax_entry.insert(0, str(int(rate * 100) if rate * 100 == int(rate * 100) else rate * 100))
        except ValueError:
            tax_entry.insert(0, "13")
        entries["tax_pct"] = tax_entry

        T.field_label(body, "HST / GST number (optional)").pack(anchor="w", pady=(12, 0))
        gst_entry = ctk.CTkEntry(body, placeholder_text="123456789RT0001", **T.entry_kwargs())
        gst_entry.pack(fill="x", pady=(4, 4))
        gst_val = get_setting("gst_number", "")
        if gst_val:
            gst_entry.insert(0, gst_val)
        entries["gst_number"] = gst_entry

    def show_step_3():
        clear_body()
        title_lbl.configure(text="You're ready!")
        subtitle_lbl.configure(
            text="Head to New Sale to ring up a customer. "
                 "Set up your receipt printer anytime in Setup — nothing else is required."
        )
        ctk.CTkLabel(
            body,
            text="Tip: The big green button at the bottom completes the sale and prints the receipt.",
            font=T.FONT, text_color=T.ACCENT, wraplength=480, justify="left",
        ).pack(anchor="w", pady=12)

    steps = [show_step_0, show_step_1, show_step_2, show_step_3]
    steps[0]()

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=28, pady=(0, 28))

    def save_step_data():
        """Save only non-empty values — never blocks on missing fields."""
        if step["n"] == 1:
            for key in ("business_name", "business_address", "business_phone"):
                if key in entries:
                    val = entries[key].get().strip()
                    if val:
                        save_setting(key, val)
        elif step["n"] == 2:
            raw = entries.get("tax_pct")
            if raw is not None:
                text = raw.get().strip()
                if text:
                    try:
                        pct = float(text)
                        save_setting("tax_rate", str(pct / 100))
                    except ValueError:
                        pass
            if "gst_number" in entries:
                gst = entries["gst_number"].get().strip()
                if gst:
                    save_setting("gst_number", gst)

    def finish(skipped: bool = False):
        if not skipped and step["n"] > 0:
            save_step_data()
        mark_setup_complete()
        completed["value"] = not skipped
        dialog.destroy()

    def next_step():
        if step["n"] > 0 and step["n"] < 3:
            save_step_data()
        if step["n"] < 3:
            step["n"] += 1
            steps[step["n"]]()
            update_buttons()
        else:
            finish(skipped=False)

    def prev_step():
        if step["n"] > 0:
            step["n"] -= 1
            steps[step["n"]]()
            update_buttons()

    back_btn = ctk.CTkButton(footer, text="Back", command=prev_step, **T.button_kwargs(width=100))
    back_btn.pack(side="left")

    skip_btn = ctk.CTkButton(
        footer, text="Skip for now", command=lambda: finish(skipped=True),
        **T.button_kwargs(width=130),
    )
    skip_btn.pack(side="left", padx=(10, 0))

    next_btn = ctk.CTkButton(footer, text="Next", command=next_step, **T.primary_button_kwargs(width=140))
    next_btn.pack(side="right")

    def update_buttons():
        back_btn.configure(state="normal" if step["n"] > 0 else "disabled")
        labels = ["Get started", "Next", "Next", "Start selling"]
        next_btn.configure(text=labels[step["n"]])
        if step["n"] == 3:
            next_btn.configure(**{**T.success_button_kwargs(width=160), "text": "Start selling"})
            skip_btn.configure(text="Close")
        else:
            skip_btn.configure(text="Skip for now")

    update_buttons()

    dialog.update_idletasks()
    w, h = 560, 540
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
    dialog.geometry(f"{w}x{h}+{px}+{py}")

    dialog.wait_window()
    return completed["value"]
