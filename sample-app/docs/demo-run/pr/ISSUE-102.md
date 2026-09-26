# PR: Fix ISSUE-102 — ISSUE-102: Customer cannot buy the last unit of a product

## Summary

Closes ISSUE-102  
Closes duplicates: ISSUE-104

## Root Cause

Inventory.reserve() used strict greater-than (on_hand > qty) instead of greater-than-or-equal, violating inventory.md Rule I-1 which requires reservation to succeed whenever on_hand >= qty, blocking the last unit from being purchased

## Fix

Change the guard condition in Inventory.reserve() from 'on_hand > qty' to 'on_hand >= qty' so reservations succeed when available stock exactly matches the requested quantity

## Evidence

Suspect: `shopcart/inventory.py` line 30  
Bug brief: `.bugflow\briefs\ISSUE-102.md`

## Verification

Regression test: `test_issue_102_inventory_regression` (ISSUE-102 in docstring)  
Run: `python -m bugflow --project . verify`

## Suggested Reviewer

`@fulfillment-team`
