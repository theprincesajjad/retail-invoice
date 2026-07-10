"""First-run setup wizard — guides new users through essential configuration."""

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
    """Show welcome wizard. Returns True when completed."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Welcome!")
    dialog.configure(fg_color=T.BG)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

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
            text="Let's set up your store in just a few steps. "
                 "This only takes a minute — you can change everything later in Setup."
        )
        ctk.CTkLabel(
            body, text="✓  Ring up sales and print receipts\n"
                       "✓  Track your inventory\n"
                       "✓  View sales history and reports",
            font=T.FONT, text_color=T.TEXT, justify="left", anchor="w",
        ).pack(anchor="w", pady=12)

    def show_step_1():
        clear_body()
        title_lbl.configure(text="Your store details")
        subtitle_lbl.configure(text="This information appears at the top of every receipt.")

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
        subtitle_lbl.configure(text="Enter your sales tax percentage. In Ontario, HST is 13%.")

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
        title_lbl.configure(text="You're all set!")
        subtitle_lbl.configure(
            text="Head to the New Sale tab to ring up your first sale. "
                 "You can set up your receipt printer anytime in Setup."
        )
        ctk.CTkLabel(
            body,
            text="Tip: The big green button at the bottom saves your sale and prints the receipt.",
            font=T.FONT, text_color=T.ACCENT, wraplength=480, justify="left",
        ).pack(anchor="w", pady=12)

    steps = [show_step_0, show_step_1, show_step_2, show_step_3]
    steps[0]()

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=28, pady=(0, 28))

    def save_step_data():
        if step["n"] == 1:
            for key in ("business_name", "business_address", "business_phone"):
                if key in entries:
                    save_setting(key, entries[key].get().strip())
        elif step["n"] == 2:
            try:
                pct = float(entries["tax_pct"].get().strip() or "13")
                save_setting("tax_rate", str(pct / 100))
            except ValueError:
                save_setting("tax_rate", "0.13")
            if "gst_number" in entries:
                save_setting("gst_number", entries["gst_number"].get().strip())

    def next_step():
        if step["n"] > 0 and step["n"] < 3:
            save_step_data()
        if step["n"] < 3:
            step["n"] += 1
            steps[step["n"]]()
            update_buttons()
        else:
            save_step_data()
            mark_setup_complete()
            completed["value"] = True
            dialog.destroy()

    def prev_step():
        if step["n"] > 0:
            step["n"] -= 1
            steps[step["n"]]()
            update_buttons()

    back_btn = ctk.CTkButton(footer, text="Back", command=prev_step, **T.button_kwargs(width=100))
    back_btn.pack(side="left")
    next_btn = ctk.CTkButton(footer, text="Next", command=next_step, **T.primary_button_kwargs(width=140))
    next_btn.pack(side="right")

    def update_buttons():
        back_btn.configure(state="normal" if step["n"] > 0 else "disabled")
        labels = ["Get started", "Next", "Next", "Start selling"]
        next_btn.configure(text=labels[step["n"]])
        if step["n"] == 3:
            next_btn.configure(**T.success_button_kwargs(width=160))

    update_buttons()

    dialog.update_idletasks()
    w, h = 560, 520
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
    dialog.geometry(f"{w}x{h}+{px}+{py}")

    dialog.wait_window()
    return completed["value"]
