"""Pricing and tax calculations for ShopCart."""

from decimal import Decimal, ROUND_HALF_UP

# State sales-tax rates (subset for demo).
TAX_RATES = {
    "CA": Decimal("0.0725"),
    "TX": Decimal("0.0625"),
    "NY": Decimal("0.0800"),
    "WA": Decimal("0.0650"),
}


def order_total(subtotal: Decimal, state: str) -> Decimal:
    """Return the final order total including sales tax."""
    rate = TAX_RATES.get(state, Decimal("0"))
    tax = subtotal * rate
    total = subtotal + tax
    return Decimal(str(round(float(total), 2)))
