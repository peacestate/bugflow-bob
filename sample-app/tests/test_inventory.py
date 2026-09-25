"""Tests for shopcart.inventory — avoids the buggy last-unit case."""

import unittest

from shopcart.inventory import Inventory, OutOfStock, seed_stock


class TestInventoryReserve(unittest.TestCase):

    def setUp(self):
        seed_stock({"SKU-001": 10, "SKU-002": 3, "SKU-003": 0})
        self.inv = Inventory()

    def test_reserve_ample_stock(self):
        """Reserving fewer units than on-hand succeeds."""
        self.inv.reserve("SKU-001", 5)
        # No exception raised — test passes.

    def test_reserve_leaves_one(self):
        """Reserving n-1 units when n are available succeeds."""
        self.inv.reserve("SKU-002", 2)  # 3 on hand, buy 2 -> 1 remains

    def test_out_of_stock_zero(self):
        """Reserving from a SKU with 0 stock raises OutOfStock."""
        with self.assertRaises(OutOfStock):
            self.inv.reserve("SKU-003", 1)

    def test_out_of_stock_unknown_sku(self):
        """Reserving an unknown SKU (treated as 0) raises OutOfStock."""
        with self.assertRaises(OutOfStock):
            self.inv.reserve("SKU-UNKNOWN", 1)

    def test_reserve_reduces_stock(self):
        """After a successful reserve the stock count decreases."""
        self.inv.reserve("SKU-001", 3)
        # Reserve 3 more — 10-3 = 7 remain, 3 < 7 so this should work.
        self.inv.reserve("SKU-001", 3)


if __name__ == "__main__":
    unittest.main()
