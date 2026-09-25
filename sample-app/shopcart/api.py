"""ShopCart public API handler."""

import json
import logging
import sys
from datetime import date
from decimal import Decimal

from shopcart.inventory import Inventory, OutOfStock
from shopcart.pricing import order_total
from shopcart.shipping import estimate_delivery

log = logging.getLogger("shopcart.api")


class ShopCartAPI:
    """Thin orchestration layer: reserve → price → ship estimate."""

    def __init__(self) -> None:
        self.inventory = Inventory()

    def handle(self, request_id: str, payload: dict) -> dict:
        """Process a checkout request.

        Expected payload keys:
            sku        (str)
            qty        (int)
            subtotal   (str | float)  — pre-tax amount
            state      (str)          — two-letter US state
            region     (str)          — shipping region
            ship_date  (str)          — ISO-8601 date

        Returns a response dict with status, total, and delivery date,
        or an error dict with status and message.
        """
        try:
            sku = payload["sku"]
            qty = int(payload["qty"])
            subtotal = Decimal(str(payload["subtotal"]))
            state = payload["state"]
            region = payload["region"]
            ship_date = date.fromisoformat(payload["ship_date"])

            self.inventory.reserve(sku, qty)
            total = order_total(subtotal, state)
            delivery = estimate_delivery(region, ship_date)

            log.info(
                "request_id=%s sku=%s qty=%d total=%s delivery=%s",
                request_id, sku, qty, total, delivery,
            )
            return {
                "status": 200,
                "request_id": request_id,
                "total": str(total),
                "delivery_date": delivery.isoformat(),
            }

        except OutOfStock as exc:
            log.exception("request_id=%s out-of-stock: %s", request_id, exc)
            return {"status": 409, "request_id": request_id, "error": str(exc)}

        except KeyError as exc:
            log.exception("request_id=%s bad region or missing field: %s", request_id, exc)
            return {"status": 400, "request_id": request_id, "error": f"Unknown key: {exc}"}

        except Exception as exc:  # noqa: BLE001
            log.exception("request_id=%s unexpected error: %s", request_id, exc)
            return {"status": 500, "request_id": request_id, "error": str(exc)}
