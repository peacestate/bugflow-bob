# Shipping SLA Policy

**Version:** 1.1  **Owner:** @fulfillment-team

## Rule S-1 — Region codes are case-insensitive

Shipping region codes MUST be normalised to lowercase before any lookup.
Clients send mixed-case values:

| Client     | Example value sent |
|------------|--------------------|
| Web storefront | `US-East`      |
| Mobile app | `US-EAST`          |
| Internal tools | `us-east`      |

All three MUST resolve to a transit time of **2 business days**.

## Rule S-2 — Canonical region keys

| Normalised key | Transit days (business) |
|----------------|------------------------|
| `us-east`      | 2                      |
| `us-west`      | 3                      |
| `eu`           | 5                      |

## Rule S-3 — Unknown region → 400, not 500

If a region code is unrecognised after normalisation the service MUST return
HTTP **400 Bad Request** with a human-readable error message. Allowing an
unhandled `KeyError` to propagate and return a 500 violates this rule and
triggers a P1 incident.

## Rule S-4 — Delivery date calculation

Transit days are calendar days for the purposes of the estimate returned to
customers. Business-day conversion is handled downstream by the logistics
provider.
