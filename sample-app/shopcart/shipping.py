"""Shipping estimates for ShopCart."""

from datetime import date, timedelta

# Transit days by normalised region key.
REGION_TRANSIT_DAYS: dict[str, int] = {
    "us-east": 2,
    "us-west": 3,
    "eu": 5,
}


def estimate_delivery(region: str, ship_date: date) -> date:
    """Return the estimated delivery date for the given region."""
    days = REGION_TRANSIT_DAYS[region]
    return ship_date + timedelta(days=days)
