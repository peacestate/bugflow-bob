# ISSUE-101: Customer charged one cent less than invoice amount

**Reporter:** finance-alerts@shopco.example  
**Severity:** Medium  
**Component:** pricing  
**Created:** 2024-06-04T09:17:00Z  

---

## Description

A customer in California purchased a single item priced at $10.00. Their
credit card was charged **$10.72**, but the system-generated invoice (which
Finance reconciles against) shows **$10.73**.

The one-cent discrepancy requires a manual ledger entry. At current volumes
this pattern affects an estimated 200–300 transactions per day in CA alone,
translating to 50–75 hours of analyst time per week.

Finance has opened a formal audit. If the root cause is a systematic
rounding error rather than a one-off, the VP of Finance requires a
post-incident review within 5 business days.

## Evidence

```
request_id=req-3c19a sku=ITEM-042 qty=1 total=10.72 delivery=2024-06-06
```

Log timestamp: `2024-06-04T08:44:01.102Z`  
Expected total per invoice: `10.73`  
Actual charge: `10.72`

See also: Finance ticket FIN-2204.
