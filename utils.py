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
