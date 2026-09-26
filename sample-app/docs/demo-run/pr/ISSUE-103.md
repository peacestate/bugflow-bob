# PR: Fix ISSUE-103 — ISSUE-103: Checkout 500 error from web storefront — region lookup failure

## Summary

Closes ISSUE-103

## Root Cause

estimate_delivery() looked up REGION_TRANSIT_DAYS using the raw caller-supplied region string without normalising to lowercase, violating shipping-sla.md Rule S-1 (case-insensitive lookup required), causing a KeyError that propagated as HTTP 500 in violation of Rule S-3

## Fix

Normalise region to lowercase before lookup with region.lower(), and wrap the KeyError in a try/except that raises ValueError so unknown regions produce HTTP 400 instead of 500

## Evidence

Suspect: `shopcart/shipping.py` line 21  
Bug brief: `.bugflow\briefs\ISSUE-103.md`

## Verification

Regression test: `test_issue_103_shipping_regression` (ISSUE-103 in docstring)  
Run: `python -m bugflow --project . verify`

## Suggested Reviewer

`@fulfillment-team`
