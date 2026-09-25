# Inventory Policy

**Version:** 2.0  **Owner:** @fulfillment-team

## Rule I-1 — Reservation succeeds when stock covers request

A reservation call for *qty* units of a SKU MUST succeed whenever
`on_hand >= qty`. In particular, **customers must be able to buy the last
unit in stock**. Blocking the final unit causes lost revenue and is
classified as a P2 defect.

## Rule I-2 — Atomicity

The check-and-decrement of `on_hand` MUST be atomic. No two concurrent
reservations may both succeed for the same unit.

## Rule I-3 — OutOfStock error format

When stock is insufficient the `OutOfStock` exception message MUST follow
the format:

```
SKU: <sku> requested <qty>, available <on_hand>
```

This format is parsed by the fulfilment dashboard. Deviation breaks alerts.

## Rule I-4 — Unknown SKU

A SKU not present in the inventory store is treated as having 0 units and
MUST raise `OutOfStock`, not `KeyError`.
