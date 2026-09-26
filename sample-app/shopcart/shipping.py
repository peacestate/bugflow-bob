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
    try:
        days = REGION_TRANSIT_DAYS[region.lower()]
    except KeyError:
        raise ValueError(f"Unknown shipping region: {region!r}")
    return ship_date + timedelta(days=days)
