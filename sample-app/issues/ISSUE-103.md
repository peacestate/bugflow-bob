# ISSUE-103: Checkout 500 error from web storefront — region lookup failure

**Reporter:** sre-oncall@shopco.example  
**Severity:** Critical  
**Component:** shipping  
**Created:** 2024-06-04T11:02:00Z  

---

## Description

Multiple customers using the **web storefront** are receiving a generic
"Something went wrong" error at checkout. SRE was paged at 10:58 UTC.
Error rate is 8% of all checkout attempts originating from the US-East
region, which accounts for roughly 40% of total checkout volume.

The web front-end sends the region value `"US-East"` (title-case) in the
checkout payload. This value is apparently not handled by the backend,
causing an unhandled exception that returns HTTP 500.

A 500 at checkout is a direct revenue impact. Initial estimate: ~$12 k/h
in lost GMV based on current conversion rates.

## Evidence

```
ERROR shopcart.api request_id=req-9b1e0 bad region or missing field: 'US-East'
Traceback (most recent call last):
  File ".../shopcart/api.py", line 48, in handle
    delivery = estimate_delivery(region, ship_date)
  File ".../shopcart/shipping.py", line 21, in estimate_delivery
    days = REGION_TRANSIT_DAYS[region]
KeyError: 'US-East'
```

Log timestamp: `2024-06-04T10:58:44.201Z`  
Affected client: web storefront (sends `"US-East"`)  
HTTP status returned to client: `400` (wrapped by api.py KeyError handler)  
Expected behaviour: should resolve to `us-east` → 2 days transit

Note: mobile app sends `"US-EAST"` and is similarly broken but not yet
reported separately.
