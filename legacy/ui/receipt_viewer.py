import customtkinter as ctk
from tkinter import messagebox
from models import Invoice, InvoiceItem
from receipt_builder import build_receipt_text
from database import get_all_settings
from . import theme as T
from .toast import toast


def show_receipt_viewer(parent, invoice: Invoice, items: list[InvoiceItem], is_preview: bool = False):
    dialog = ctk.CTkToplevel(parent)
    title = "Receipt Preview" if is_preview else f"Receipt — {invoice.invoice_number}"
    dialog.title(title)
    dialog.geometry("480x720")
    dialog.minsize(420, 560)
    dialog.configure(fg_color=T.BG)
    dialog.transient(parent)
    dialog.grab_set()

    card = ctk.CTkFrame(dialog, **T.card_kwargs())
    card.pack(fill="both", expand=True, padx=24, pady=24)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(24, 8))

    settings = get_all_settings()
    biz_name = settings.get("business_name", "My Business")
    ctk.CTkLabel(header, text=biz_name, font=T.FONT_HEADLINE, text_color=T.TEXT).pack(anchor="w")
    if is_preview:
        ctk.CTkLabel(header, text="Preview — this is what your customer will see", font=T.FONT_CAPTION, text_color=T.WARNING).pack(anchor="w", pady=(4, 0))
    else:
        ctk.CTkLabel(
            header,
            text=f"{invoice.invoice_number}  ·  {invoice.created_at[:16] if invoice.created_at else ''}",
            font=T.FONT_CAPTION, text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

    customer = invoice.customer_name or "Walk-in customer"
    if invoice.customer_phone:
        customer = f"{customer}  ·  {invoice.customer_phone}"
    ctk.CTkLabel(card, text=customer, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY).pack(anchor="w", padx=24, pady=(0, 8))

    receipt_frame = ctk.CTkFrame(card, fg_color="#FFFEF9", corner_radius=T.RADIUS_SM, border_width=1, border_color=T.BORDER_LIGHT)
    receipt_frame.pack(fill="both", expand=True, padx=24, pady=(0, 12))

    receipt = build_receipt_text(invoice, items)
    body = ctk.CTkTextbox(
        receipt_frame,
        font=("Courier New", 15),
        fg_color="#FFFEF9",
        text_color=T.TEXT,
        border_width=0,
        corner_radius=T.RADIUS_SM,
        wrap="none",
    )
    body.pack(fill="both", expand=True, padx=12, pady=12)
    body.insert("1.0", receipt)
    body.configure(state="disabled")

    def do_print():
        if is_preview:
            messagebox.showinfo("Preview only", "Save the sale first to print the receipt.")
            return
        from printer import print_receipt
        ok, msg = print_receipt(invoice, items)
        if ok:
            parent.set_status(f"Printed {invoice.invoice_number}")
            toast(parent, f"Printed {invoice.invoice_number}", kind="success")
        else:
            toast(parent, msg, kind="error", title="Print failed")
            messagebox.showerror("Print failed", msg)

    def do_email():
        if is_preview:
            messagebox.showinfo("Preview only", "Save the sale first to email the receipt.")
            return
        from email_service import send_receipt_email
        addr_dialog = ctk.CTkInputDialog(
            text=f"Send receipt for {invoice.invoice_number} to:",
            title="Email receipt",
        )
        to_addr = addr_dialog.get_input()
        if not to_addr:
            return
        ok, msg = send_receipt_email(to_addr, invoice, items)
        if ok:
            parent.set_status(msg)
            toast(parent, msg, kind="success", title="Email sent")
        else:
            toast(parent, msg, kind="error", title="Email failed")
            messagebox.showerror("Email failed", msg)

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=24, pady=(0, 24))

    ctk.CTkButton(footer, text="Close", command=dialog.destroy, **T.button_kwargs(width=100)).pack(side="right")
    if not is_preview:
        ctk.CTkButton(footer, text="Email", command=do_email, **T.button_kwargs(width=100)).pack(side="right", padx=(0, 10))
        ctk.CTkButton(footer, text="Print Receipt", command=do_print, **T.success_button_kwargs(width=150)).pack(side="right", padx=(0, 10))

    dialog.update_idletasks()
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - 480) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - 720) // 2)
    dialog.geometry(f"480x720+{px}+{py}")
