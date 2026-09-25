# BugFlow Fixer Rules

These rules apply only in the `bugflow-fixer` mode.

## 1. Failing test before any product change

Before editing any file under `sample-app/shopcart/`, you MUST:

1. Write a test in `sample-app/tests/` named `test_issue_<ID>_<short_description>.py`
   (e.g. `test_issue_101_order_total_discount.py`).
2. Run the test and confirm it **fails** on the unmodified code.
3. Record the failure output.

Only after the test is confirmed failing may you touch product code.

## 2. Smallest fix

Apply the minimal code change that makes the failing test pass and no other test
regress. Do not refactor, rename, reformat, or add features beyond what is required
by the test. If you find a second bug while fixing the first, note it in your report
but do not fix it — that is a separate issue.

## 3. Don't touch other agents' files

You own `sample-app/shopcart/` and `sample-app/tests/` only.
Do not edit:
- `sample-app/.bugflow/` (owned by bugflow-lead)
- `bugflow/` (CLI toolkit — out of scope for bug fixes)
- Any issue, doc, log, or config file

If a fix seems to require changes outside your allowed paths, stop, report the
constraint in your output, and return to the lead agent for guidance.
