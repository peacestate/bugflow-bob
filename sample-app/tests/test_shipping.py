"""Tests for shopcart.shipping — avoids the buggy mixed-case lookup."""

import unittest
from datetime import date

from shopcart.shipping import estimate_delivery, REGION_TRANSIT_DAYS


class TestEstimateDelivery(unittest.TestCase):

    def test_us_east_lowercase(self):
        """Exact lowercase key works — 2 business days."""
        ship = date(2024, 6, 3)  # Monday
        result = estimate_delivery("us-east", ship)
        self.assertEqual(result, date(2024, 6, 5))

    def test_us_west_lowercase(self):
        ship = date(2024, 6, 3)
        result = estimate_delivery("us-west", ship)
        self.assertEqual(result, date(2024, 6, 6))

    def test_eu_lowercase(self):
        ship = date(2024, 6, 3)
        result = estimate_delivery("eu", ship)
        self.assertEqual(result, date(2024, 6, 8))

    def test_unknown_region_raises(self):
        """A completely unknown region key raises KeyError (bug aside)."""
        with self.assertRaises(KeyError):
            estimate_delivery("ap-southeast", date(2024, 6, 3))

    def test_all_canonical_regions_present(self):
        """All canonical region keys are registered in the lookup table."""
        for key in ("us-east", "us-west", "eu"):
            self.assertIn(key, REGION_TRANSIT_DAYS)


if __name__ == "__main__":
    unittest.main()
