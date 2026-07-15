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


def compute_invoice_totals(
    items,
    tax_rate: float,
    discount_type: str = "",
    discount_value: float = 0.0,
    discount_timing: str = "before_tax",
):
    """Return subtotal, discount_amount, tax_amount, total.

    discount_timing:
      - "before_tax" (default): discount reduces the taxable amount, then tax is applied
      - "after_tax": tax on full subtotal, then discount is taken off the taxed total
    """
    subtotal = sum(item.line_total for item in items)
    timing = (discount_timing or "before_tax").strip().lower()
    if timing not in ("before_tax", "after_tax"):
        timing = "before_tax"

    def _discount_of(base: float) -> float:
        if discount_value <= 0:
            return 0.0
        if discount_type == "percent":
            return min(base, base * (discount_value / 100.0))
        if discount_type == "fixed":
            return min(base, discount_value)
        return 0.0

    if timing == "after_tax":
        tax_amount = subtotal * tax_rate
        pre_discount_total = subtotal + tax_amount
        discount_amount = _discount_of(pre_discount_total)
        total = max(0.0, pre_discount_total - discount_amount)
        return subtotal, discount_amount, tax_amount, total

    discount_amount = _discount_of(subtotal)
    taxable = max(0.0, subtotal - discount_amount)
    tax_amount = taxable * tax_rate
    total = taxable + tax_amount
    return subtotal, discount_amount, tax_amount, total
