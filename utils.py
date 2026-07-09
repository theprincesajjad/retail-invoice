def format_currency(amount: float) -> str:
    """Format float to currency string."""
    try:
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def parse_currency(amount_str: str) -> float:
    """Parse currency string to float."""
    try:
        clean_str = amount_str.replace('$', '').replace(',', '').strip()
        return float(clean_str) if clean_str else 0.0
    except ValueError:
        return 0.0


def compute_invoice_totals(items, tax_rate: float, discount_type: str = "", discount_value: float = 0.0):
    """Return subtotal, discount_amount, tax_amount, total."""
    subtotal = sum(item.line_total for item in items)
    discount_amount = 0.0
    if discount_type == "percent" and discount_value > 0:
        discount_amount = min(subtotal, subtotal * (discount_value / 100.0))
    elif discount_type == "fixed" and discount_value > 0:
        discount_amount = min(subtotal, discount_value)
    taxable = subtotal - discount_amount
    tax_amount = taxable * tax_rate
    total = taxable + tax_amount
    return subtotal, discount_amount, tax_amount, total
