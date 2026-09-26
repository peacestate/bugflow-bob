# BugFlow Triage Report

| ID | Severity | Component | Owner | Duplicates | Suspect File | Suspect Line | Title |
|---|---|---|---|---|---|---|---|
| ISSUE-103 | critical | shipping | `@fulfillment-team` | — | `shopcart/shipping.py` | 21 | ISSUE-103: Checkout 500 error from web storefront — region lookup failure |
| ISSUE-102 | high | inventory | `@fulfillment-team` | ISSUE-104 | `shopcart/inventory.py` | 30 | ISSUE-102: Customer cannot buy the last unit of a product |
| ISSUE-101 | medium | pricing | `@payments-team` | — | `shopcart/pricing.py` | 19 | ISSUE-101: Customer charged one cent less than invoice amount |

## Duplicates
- **ISSUE-104** -- duplicate of **ISSUE-102** (signature: `shopcart.inventory.OutOfStock@shopcart/inventory.py:30`)
