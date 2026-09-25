---
name: bugflow-fix
description: >-
  Use when fixing a single BugFlow issue as a fixer subagent.
  Follows the reproduce-first workflow: read brief, write failing test, confirm
  failure, log reproduce, apply minimal fix, log fix, verify, and return a
  structured result.
---

# BugFlow Fix Skill

You fix exactly ONE bug. Follow every step in order. Do not skip any step.
All paths are relative to `sample-app/` unless stated otherwise.

---

## Step 1 — Read the brief

Read the brief file at the path provided in your instructions
(e.g. `sample-app/.bugflow/briefs/ISSUE-101.md`).

Extract and note:
- **Issue ID** (`<ID>`)
- **Policy doc path** and the relevant section title
- **Source file** and **symbol** (function or class method) containing the bug
- **Expected behaviour** as stated in the policy
- **Suggested test approach** from the brief

---

## Step 2 — Write a failing test

Create a new file:
`sample-app/tests/test_issue_<ID>_<short_description>.py`

where `<short_description>` is 2–4 words from the issue title, lowercased and
hyphenated (e.g. `test_issue_101_order_total_discount.py`).

The test must:
- Import only from `sample-app/shopcart/` (or stdlib)
- Exercise the specific symbol identified in the brief
- Assert the behaviour the policy requires
- Have a clear docstring: `"""Regression test for ISSUE-<ID>: <one-line description>."""`

Do not touch any product file yet.

---

## Step 3 — Confirm the test fails

Run (from the workspace root; the toolkit uses `unittest`, not pytest):

```
python -m unittest discover -s sample-app/tests -t sample-app -k issue_<N>
```

where `<N>` is the numeric part of the issue ID (e.g. `101` for `ISSUE-101`).

The test MUST fail. If it passes on the unmodified code, the test does not pin the
bug — revise it until it fails before continuing.

Record the failure message verbatim; you will include it in the final report.

---

## Step 4 — Log the reproduction

```
python -m bugflow --project sample-app log <ID> reproduce
```

This writes a timeline entry confirming the bug is reproducible.

---

## Step 5 — Apply the minimal fix

Edit the source file and symbol identified in the brief (under `sample-app/shopcart/`).

Rules:
- Make the **smallest possible change** that causes the failing test to pass.
- Do not rename, reformat, or refactor anything unrelated to the fix.
- Do not add new imports, dependencies, or helper functions unless strictly required.
- If the correct behaviour is ambiguous, the policy doc is authoritative.

---

## Step 6 — Log the fix

```
python -m bugflow --project sample-app log <ID> fix
```

This writes a timeline entry recording the fix.

---

## Step 7 — Verify

```
python -m bugflow --project sample-app verify --issue <ID>
```

Read the full output. It must show:
- The new test passing
- No previously-passing tests now failing

Record the verify output verbatim.

---

## Step 8 — Return a structured result

Reply with the following sections (no other prose):

### Root cause
One paragraph. Cite the policy section by name (e.g. "Per *Pricing Policy § 3.2 — Discount
Application Order*, discounts must be applied before tax is calculated.").

### Fix
One paragraph describing the change made and why it satisfies the policy.

### Test name
`test_issue_<ID>_<short_description>.py`

### Failure output (before fix)
```
<paste pytest failure output from Step 3>
```

### Verify output (after fix)
```
<paste bugflow verify output from Step 7>
```
