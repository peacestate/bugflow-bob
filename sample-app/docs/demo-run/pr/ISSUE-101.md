# PR: Fix ISSUE-101 — ISSUE-101: Customer charged one cent less than invoice amount

## Summary

Closes ISSUE-101

## Root Cause

order_total() converted Decimal to float and used Python built-in round() (banker's rounding), violating pricing-policy.md Rules P-1 and P-2, causing half-cent amounts like .725 to round down to .72 instead of up to .73

## Fix

Replace float conversion and built-in round() with total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) to keep all arithmetic in Decimal and enforce ROUND_HALF_UP

## Evidence

Suspect: `shopcart/pricing.py` line 19  
Bug brief: `.bugflow\briefs\ISSUE-101.md`

## Verification

Regression test: `test_issue_101_pricing_regression` (ISSUE-101 in docstring)  
Run: `python -m bugflow --project . verify`

## Suggested Reviewer

`@payments-team`
