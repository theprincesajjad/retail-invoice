"""Send receipt PDF via SMTP (Gmail-compatible)."""

import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import get_all_settings
from models import Invoice, InvoiceItem
from receipt_pdf import build_receipt_pdf


def send_receipt_email(to_address: str, invoice: Invoice, items: list[InvoiceItem]) -> tuple[bool, str]:
    settings = get_all_settings()
    host = settings.get("smtp_host", "smtp.gmail.com").strip()
    port = int(settings.get("smtp_port", "587") or "587")
    email = settings.get("smtp_email", "").strip()
    password = settings.get("smtp_password", "").strip()
    from_name = settings.get("smtp_from_name", settings.get("business_name", "Retail Invoice")).strip()

    if not email or not password:
        return False, "Configure SMTP email and app password in Settings → Email."

    to_address = to_address.strip()
    if not to_address or "@" not in to_address:
        return False, "Enter a valid customer email address."

    try:
        pdf_bytes = build_receipt_pdf(invoice, items)
        business = settings.get("business_name", "My Business")

        msg = MIMEMultipart()
        msg["Subject"] = f"Receipt {invoice.invoice_number} from {business}"
        msg["From"] = f"{from_name} <{email}>"
        msg["To"] = to_address

        body = (
            f"Hello,\n\n"
            f"Please find your receipt for invoice {invoice.invoice_number} attached.\n\n"
            f"Total: ${invoice.total:.2f}\n\n"
            f"Thank you,\n{business}"
        )
        msg.attach(MIMEText(body, "plain"))

        attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=f"{invoice.invoice_number}.pdf")
        msg.attach(attachment)

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(email, password)
            server.sendmail(email, [to_address], msg.as_string())

        return True, f"Sent to {to_address}"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP login failed. Use a Gmail App Password, not your regular password."
    except Exception as e:
        logging.error(f"Email failed: {e}")
        return False, str(e)
