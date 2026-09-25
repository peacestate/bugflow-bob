# ISSUE-102: Customer cannot buy the last unit of a product

**Reporter:** support-tier2@shopco.example  
**Severity:** High  
**Component:** inventory  
**Created:** 2024-06-04T10:45:00Z  

---

## Description

A customer attempted to purchase the last remaining unit of SKU-778
("Vintage Denim Jacket — Size M"). The checkout returned an
**Out of Stock** error even though the product page clearly showed
**1 unit available**.

The customer contacted support; by the time the agent refreshed the page
the product appeared in stock again (no one else had purchased it). The
customer then retried and received the same error.

This is a clear lost-sale event. Inventory correctly shows 1 unit but
the system refuses to sell it.

## Evidence

```
ERROR shopcart.api request_id=req-7f3a2 out-of-stock:
  SKU: SKU-778 requested 1, available 1
```

Log timestamp: `2024-06-04T10:31:55.883Z`  
SKU: `SKU-778`  
Quantity requested: `1`  
Quantity reported available in error message: `1`

Customer order ID (partial): `ORD-29941`
