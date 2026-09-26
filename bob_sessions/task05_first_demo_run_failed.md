# /bugflow

---

**Status:** active  **Date:** 2026-09-25

---

### 👤 User

---
name: bugflow
description: '# /bugflow'
metadata:
  user-invocable: true
  disable-model-invocation: true
---

# /bugflow

Runs the BugFlow triage pipeline end-to-end against `sample-app/`.

## What this command does

1. Switches to (or confirms) `bugflow-lead` mode.
2. Activates the `bugflow-triage` skill.
3. Follows every step of that skill: triage, read issues and docs, write briefs,
   spawn one parallel fixer subagent per unique bug, review each fix, draft PRs,
   and produce the impact report.

## Usage

```
/bugflow
```

No arguments are required. The command always processes all open issues found in
`sample-app/issues/` unless the triage output marks them as already closed.

## Pre-conditions

- `sample-app/` must exist and contain at least one `issues/ISSUE-*.md` file.
- `python -m bugflow` must be runnable from the workspace root
  (the `bugflow/` package is in the repo; no install step is needed).

## Mode

This command runs in `bugflow-lead` mode. If you are currently in a different mode,
Bob will switch automatically when this command is invoked.

## Instructions

Switch to `bugflow-lead` mode, then activate and follow the `bugflow-triage` skill
from Step 1 through Step 7.


---

### 🤖 Assistant

> 🔧 called: use_skill



> 🔧 **use_skill** — bugflow-triage

### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — 
[-] Step 1: Start timeline and run triage
[ ] Step 2: Read issues and docs for each unique bug
[ ] Step 3: Write a brief per unique bug
[ ] Step 4: Spawn one fixer subagent per unique bug (parallel)
[ ] Step 5: Review each fix
[ ] Step 6: Draft a PR per unique bug
[ ] Step 7: Report


### 🤖 Assistant

> 🔧 called: execute_command

## Step 1 — Start timeline and triage

> 🔧 **execute_command** — python -m bugflow --project sample-app start --mode agent

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -m bugflow --project sample-app triage

### 🤖 Assistant

> 🔧 called: update_todo_list

Triage complete. The work queue has:
- **ISSUE-103** (critical) — Checkout 500 error, shipping region lookup failure
- **ISSUE-102** (high) — Cannot buy last unit of a product (canonical; ISSUE-104 is a duplicate)
- **ISSUE-101** (medium) — Customer charged one cent less than invoice amount

ISSUE-104 is a duplicate of ISSUE-102 and will be closed with a `Closes: ISSUE-102` line.

> 🔧 **update_todo_list** — 
[x] Step 1: Start timeline and run triage
[-] Step 2: Read issues and docs for each unique bug
[ ] Step 3: Write a brief per unique bug
[ ] Step 4: Spawn one fixer subagent per unique bug (parallel)
[ ] Step 5: Review each fix
[ ] Step 6: Draft a PR per unique bug
[ ] Step 7: Report


### 🤖 Assistant

> 🔧 called: read_file

## Step 2 — Read issues and docs

Reading all three unique issue files and the `bugflow.json` in parallel:

> 🔧 **read_file** — sample-app/issues/ISSUE-103.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/issues/ISSUE-102.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/issues/ISSUE-101.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/bugflow.json

### 🤖 Assistant

> 🔧 called: read_file

Now read the three policy docs and the source files in parallel:

> 🔧 **read_file** — sample-app/docs/pricing-policy.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/docs/inventory.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/docs/shipping-sla.md

### 🤖 Assistant

> 🔧 called: read_file

Now read the source files:

> 🔧 **read_file** — sample-app/shopcart/pricing.py

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/shopcart/inventory.py

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/shopcart/shipping.py

### 🤖 Assistant

> 🔧 called: read_file

All three bugs are now clearly understood. Let me also handle ISSUE-104 (duplicate) now:

> 🔧 **read_file** — sample-app/issues/ISSUE-104.md

### 🤖 Assistant

> 🔧 called: apply_diff

Identical root cause (same `>` vs `>=` fencepost error in `Inventory.reserve`). Now marking ISSUE-104 as duplicate:

> 🔧 **apply_diff** — sample-app/issues/ISSUE-104.md

### 🤖 Assistant

> 🔧 called: update_todo_list

The bugflow-lead mode restricts edits to `.bugflow/` files. The `Closes: ISSUE-102` annotation for ISSUE-104 will be handled by the bugflow CLI or noted in the brief/triage files. Moving on to generate briefs.

> 🔧 **update_todo_list** — 
[x] Step 1: Start timeline and run triage
[x] Step 2: Read issues and docs for each unique bug
[-] Step 3: Write a brief per unique bug
[ ] Step 4: Spawn one fixer subagent per unique bug (parallel)
[ ] Step 5: Review each fix
[ ] Step 6: Draft a PR per unique bug
[ ] Step 7: Report


### 🤖 Assistant

> 🔧 called: execute_command

## Step 3 — Write briefs for unique bugs

Running all three brief commands in parallel (they're independent):

> 🔧 **execute_command** — python -m bugflow --project sample-app brief 101

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -m bugflow --project sample-app brief --help

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -m bugflow --project sample-app brief ISSUE-101 ISSUE-102 ISSUE-103

### 🤖 Assistant

> 🔧 called: read_file

All three briefs written. Reading to verify completeness:

> 🔧 **read_file** — sample-app/.bugflow/briefs/ISSUE-101.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/.bugflow/briefs/ISSUE-102.md

### 🤖 Assistant

> 🔧 called: read_file



> 🔧 **read_file** — sample-app/.bugflow/briefs/ISSUE-103.md

### 🤖 Assistant

> 🔧 called: update_todo_list

All three briefs are complete. They contain:
- ✅ Issue summary
- ✅ Relevant log excerpt  
- ✅ Policy section citations
- ✅ Source file and symbol
- ✅ Suggested test approach (Definition of Done)

Now logging the reproduce steps to the timeline and moving to Step 4:

> 🔧 **update_todo_list** — 
[x] Step 1: Start timeline and run triage
[x] Step 2: Read issues and docs for each unique bug
[x] Step 3: Write a brief per unique bug
[-] Step 4: Spawn one fixer subagent per unique bug (parallel)
[ ] Step 5: Review each fix
[ ] Step 6: Draft a PR per unique bug
[ ] Step 7: Report


### 🤖 Assistant

> 🔧 called: spawn_subagent

## Step 4 — Spawn fixer subagents in parallel

> 🔧 **spawn_subagent** — general

### 🤖 Assistant

> 🔧 called: spawn_subagent



### 🤖 Assistant

The current mode restricts file edits to `sample-app/.bugflow/` only. I cannot write the regression test to `sample-app/tests/test_inventory.py` or fix `sample-app/shopcart/inventory.py`. To complete this BugFlow task I need write access to those paths. Which mode should I switch to in order to edit files outside `.bugflow/`?

> 🔧 **spawn_subagent** — You are a BugFlow fixer working in bugflow-fixer mode. Follow the bugflow-fix skill exactly.

Brief path: sample-app/.bugflow/briefs/ISSUE-102.md
Issue ID: ISSUE-102

The workspace root is d:\bugflow-bob. All commands should be run from there.

Complete all steps through:
  python -m bugflow --project sample-app log ISSUE-102 fix
  python -m bugflow --project sample-app verify --issue ISSUE-102

Then return a structured result with:
- root cause (with policy citation)
- fix description (what changed and in which file/line)
- test name
- verify output

Key facts from triage (so you don't need to re-read everything):
- Bug: Inventory.reserve() in sample-app/shopcart/inventory.py line 22 uses `if on_hand > qty` (strict greater-than), so when on_hand == qty (exactly 1 unit, 1 requested), it raises OutOfStock instead of allowing the sale.
- Policy violation: Rule I-1 — "A reservation call for qty units MUST succeed whenever on_hand >= qty. In particular, customers must be able to buy the last unit in stock."
- Fix: change `if on_hand > qty:` to `if on_hand >= qty:` on line 22
- Test must be named test_issue_102_inventory_regression and placed in sample-app/tests/test_inventory.py
- Existing test file: sample-app/tests/test_inventory.py
- ISSUE-104 is a confirmed duplicate of ISSUE-102 (same root cause, different SKU). The fix automatically resolves ISSUE-104 as well.
- Also note: the brief mentions this also covers ISSUE-104 as a duplicate.