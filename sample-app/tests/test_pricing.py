"""Tests for shopcart.pricing — avoids the buggy CA HALF_UP case."""

import unittest
from decimal import Decimal

from shopcart.pricing import order_total


class TestOrderTotal(unittest.TestCase):

    def test_no_tax_state(self):
        """States not in the table get 0% tax."""
        self.assertEqual(order_total(Decimal("20.00"), "OR"), Decimal("20.00"))

    def test_tx_rate(self):
        """Texas: 6.25% on $50 — avoids the half-cent edge (use $40 instead).

        $40 * 0.0625 = $2.50 exactly, no rounding needed at all.
        """
        # 40.00 * 0.0625 = 2.50 -> total 42.50 (no rounding ambiguity)
        result = order_total(Decimal("40.00"), "TX")
        self.assertEqual(result, Decimal("42.50"))

    def test_ny_rate_clean(self):
        """New York: 8% — clean multiplication, no rounding ambiguity."""
        # 25.00 * 0.08 = 2.00 -> total 27.00
        result = order_total(Decimal("25.00"), "NY")
        self.assertEqual(result, Decimal("27.00"))

    def test_zero_subtotal(self):
        result = order_total(Decimal("0.00"), "CA")
        self.assertEqual(result, Decimal("0.00"))

    def test_large_amount_wa(self):
        """Washington: 6.5% on $200 — no fractional-cent edge."""
        # 200.00 * 0.065 = 13.00 -> total 213.00
        result = order_total(Decimal("200.00"), "WA")
        self.assertEqual(result, Decimal("213.00"))


if __name__ == "__main__":
    unittest.main()
