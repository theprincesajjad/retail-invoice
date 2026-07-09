import customtkinter as ctk
from tkinter import messagebox
from models import Invoice, InvoiceItem
from receipt_builder import build_receipt_text
from . import theme as T


def show_receipt_viewer(parent, invoice: Invoice, items: list[InvoiceItem]):
    dialog = ctk.CTkToplevel(parent)
    dialog.title(f"Receipt · {invoice.invoice_number}")
    dialog.geometry("440x680")
    dialog.minsize(400, 520)
    dialog.configure(fg_color=T.BG)
    dialog.transient(parent)
    dialog.grab_set()

    card = ctk.CTkFrame(dialog, **T.card_kwargs())
    card.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(20, 8))
    ctk.CTkLabel(header, text=invoice.invoice_number, font=T.FONT_HEADLINE, text_color=T.TEXT).pack(side="left")
    ctk.CTkLabel(
        header,
        text=invoice.created_at[:16] if invoice.created_at else "",
        **T.label_secondary(),
    ).pack(side="right")

    meta = ctk.CTkFrame(card, fg_color="transparent")
    meta.pack(fill="x", padx=20, pady=(0, 8))
    customer = invoice.customer_name or "Walk-in"
    if invoice.customer_phone:
        customer = f"{customer} · {invoice.customer_phone}"
    ctk.CTkLabel(meta, text=customer, **T.label_secondary()).pack(anchor="w")

    receipt = build_receipt_text(invoice, items)
    body = ctk.CTkTextbox(
        card,
        font=("Courier New", 12),
        fg_color=T.SURFACE_ALT,
        text_color=T.TEXT,
        border_color=T.BORDER,
        corner_radius=T.RADIUS_SM,
        wrap="none",
    )
    body.pack(fill="both", expand=True, padx=20, pady=(0, 12))
    body.insert("1.0", receipt)
    body.configure(state="disabled")

    def do_print():
        from printer import print_receipt
        ok, msg = print_receipt(invoice, items)
        if ok:
            parent.set_status(f"Printed {invoice.invoice_number}")
        else:
            messagebox.showerror("Print failed", msg)

    def do_email():
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
            messagebox.showinfo("Email sent", msg)
        else:
            messagebox.showerror("Email failed", msg)

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=20, pady=(0, 20))
    ctk.CTkButton(footer, text="Close", command=dialog.destroy, **T.button_kwargs(width=88)).pack(side="right")
    ctk.CTkButton(footer, text="Email", command=do_email, **T.button_kwargs(width=88)).pack(side="right", padx=(0, 8))
    ctk.CTkButton(footer, text="Print", command=do_print, **T.primary_button_kwargs(width=88)).pack(side="right", padx=(0, 8))
