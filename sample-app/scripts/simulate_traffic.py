"""Simulate realistic traffic against ShopCartAPI and write logs/app.log.

Replays 7 requests with fixed request IDs and deterministic timestamps.
Includes the three buggy requests so the log file contains the expected
evidence lines for the four support issues.
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# Logging setup — write NDJSON to logs/app.log
# ---------------------------------------------------------------------------

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOGS_DIR, "app.log")


class NDJSONFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _build_logger() -> logging.Logger:
    handler = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    handler.setFormatter(NDJSONFormatter())
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(handler)
    # Also echo to stdout so the test run shows something.
    stdout_h = logging.StreamHandler(sys.stdout)
    stdout_h.setFormatter(logging.Formatter("%(levelname)-8s %(name)s  %(message)s"))
    root.addHandler(stdout_h)
    return logging.getLogger("simulate")


# ---------------------------------------------------------------------------
# Import app — path massage so this script runs from repo root or scripts/
# ---------------------------------------------------------------------------

_here = os.path.dirname(os.path.abspath(__file__))
_app_root = os.path.join(_here, "..")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from shopcart.inventory import seed_stock  # noqa: E402
from shopcart.api import ShopCartAPI  # noqa: E402

# ---------------------------------------------------------------------------
# Seed inventory
# ---------------------------------------------------------------------------

seed_stock({
    "ITEM-042": 50,   # $10 CA pricing-bug item
    "SKU-778":  1,    # last-unit bug (ISSUE-102)
    "SKU-210":  20,   # healthy stock
    "SKU-512":  5,    # healthy stock
    "SKU-901":  1,    # last-unit bug VIP (ISSUE-104)
})

# ---------------------------------------------------------------------------
# Request fixtures  (request_id, payload)
# ---------------------------------------------------------------------------

REQUESTS = [
    # req-1a2b3 — normal US-West purchase, clean path
    ("req-1a2b3", {
        "sku": "SKU-210", "qty": 2, "subtotal": "49.99",
        "state": "WA", "region": "us-west", "ship_date": "2024-06-03",
    }),
    # req-2d4e5 — normal EU purchase, clean path
    ("req-2d4e5", {
        "sku": "SKU-512", "qty": 1, "subtotal": "29.99",
        "state": "NY", "region": "eu", "ship_date": "2024-06-03",
    }),
    # req-3c19a — BUG #1: $10.00 CA -> total will be 10.72 not 10.73
    ("req-3c19a", {
        "sku": "ITEM-042", "qty": 1, "subtotal": "10.00",
        "state": "CA", "region": "us-west", "ship_date": "2024-06-03",
    }),
    # req-5f6g7 — normal TX purchase, clean path
    ("req-5f6g7", {
        "sku": "SKU-210", "qty": 1, "subtotal": "75.00",
        "state": "TX", "region": "us-east", "ship_date": "2024-06-03",
    }),
    # req-7f3a2 — BUG #2: last unit of SKU-778 -> OutOfStock
    ("req-7f3a2", {
        "sku": "SKU-778", "qty": 1, "subtotal": "89.95",
        "state": "NY", "region": "us-east", "ship_date": "2024-06-04",
    }),
    # req-9b1e0 — BUG #3: region "US-East" (title-case) -> KeyError
    ("req-9b1e0", {
        "sku": "SKU-210", "qty": 1, "subtotal": "34.50",
        "state": "WA", "region": "US-East", "ship_date": "2024-06-04",
    }),
    # req-a4d77 — BUG #2 again: last unit of SKU-901 (VIP sneaker) -> OutOfStock
    ("req-a4d77", {
        "sku": "SKU-901", "qty": 1, "subtotal": "220.00",
        "state": "CA", "region": "us-west", "ship_date": "2024-06-04",
    }),
]

# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

def main() -> None:
    log = _build_logger()
    api = ShopCartAPI()

    print(f"\nWriting logs to: {os.path.abspath(LOG_PATH)}\n")
    print(f"{'REQUEST ID':<14}  {'STATUS':>6}  DETAIL")
    print("-" * 60)

    for req_id, payload in REQUESTS:
        response = api.handle(req_id, payload)
        status = response["status"]
        if status == 200:
            detail = f"total={response['total']}  delivery={response['delivery_date']}"
        else:
            detail = response.get("error", "")
        print(f"{req_id:<14}  {status:>6}  {detail}")

    print("\nDone. Log lines written:", sum(1 for _ in open(LOG_PATH)))


if __name__ == "__main__":
    main()
