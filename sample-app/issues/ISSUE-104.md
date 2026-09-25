# ISSUE-104: VIP customer cannot purchase limited-edition sneaker SKU-901

**Reporter:** vip-support@shopco.example  
**Severity:** High  
**Component:** inventory  
**Created:** 2024-06-04T13:30:00Z  

---

## Description

A VIP customer (Gold tier, account age 7 years) attempted to purchase the
last pair of the **AirEdge Pro limited-edition sneaker (SKU-901)** during
the exclusive early-access window. The checkout page returned:

> "Sorry, this item is out of stock."

The customer immediately contacted the VIP hotline. Our agent confirmed
in the warehouse management system that **1 unit is physically in stock
and unallocated**. The customer has escalated to the Head of Customer
Experience.

This is a high-visibility issue: SKU-901 has been featured in a marketing
campaign and the limited run of 50 units sold out in under 3 minutes —
except for the final unit, which no one can buy.

There is potential brand damage if this is shared on social media.
Requesting urgent investigation and a hotfix within 2 hours.

## Evidence

```
ERROR shopcart.api request_id=req-a4d77 out-of-stock:
  SKU: SKU-901 requested 1, available 1
```

Log timestamp: `2024-06-04T13:18:09.554Z`  
SKU: `SKU-901`  
Quantity requested: `1`  
Quantity reported available: `1`  
Customer tier: Gold VIP  
Campaign: "AirEdge Pro Drop — Exclusive Early Access"
