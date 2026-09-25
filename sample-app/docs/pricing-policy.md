# Pricing Policy

**Version:** 1.2  **Owner:** @payments-team

## Rule P-1 — Exact decimal arithmetic

All monetary amounts MUST be computed using exact decimal arithmetic
(`decimal.Decimal`). Floating-point types (`float`) are prohibited in any
path that touches prices, taxes, discounts, or totals.

## Rule P-2 — Rounding mode

All final amounts MUST be rounded using **ROUND_HALF_UP** (i.e. half-cent
rounds UP, never to even). This matches the rounding convention used in
Finance's billing system and on printed invoices.

Example: a $10.00 item in California (tax rate 7.25%) produces a tax amount
of $0.725. Rounding HALF_UP gives **$0.73**, so the order total is **$10.73**.

## Rule P-3 — Mismatch cost

Any one-cent discrepancy between the amount charged and the amount printed
on the customer invoice requires a manual reconciliation entry in Finance's
ledger. At current transaction volumes this costs approximately **15 minutes
of analyst time per occurrence**. Systematic rounding errors are escalated
to the VP of Finance within 24 hours of detection.

## Rule P-4 — Audit trail

The rounded total MUST be logged at INFO level with the `request_id` so
Finance can cross-reference charge records with application logs.
