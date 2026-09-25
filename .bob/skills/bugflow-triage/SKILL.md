---
name: bugflow-triage
description: >-
  Use when running the BugFlow pipeline end-to-end in bugflow-lead mode.
  Guides triage of open issues, duplicate detection, brief generation, parallel
  fix subagent spawning, review, PR drafting, and final report.
---

# BugFlow Triage Skill

Follow these steps in order. Never skip a step. All file paths are relative to
`sample-app/` unless stated otherwise.

---

## Step 1 — Start

Confirm you are in `bugflow-lead` mode. If not, switch before proceeding.

Start a fresh timeline:

```
python -m bugflow --project sample-app start --mode agent
```

Run the triage command to get a ranked, deduplicated list of open issues:

```
python -m bugflow --project sample-app triage
```

Read the output. Note which issues are flagged as duplicates and which issue is
canonical for each duplicate group.

---

## Step 2 — Read issues and docs

For each **unique** (non-duplicate) issue:

1. Read the issue file: `issues/ISSUE-<ID>.md`
2. Look up the matching entry in `sample-app/bugflow.json` to find `policy_doc`,
   `source_file`, `symbol`, and `log_request_id`.
3. Read the policy doc cited in `policy_doc`.
4. Read the relevant section of the source file named in `source_file`.

---

## Step 3 — Write a brief per unique bug

For each unique issue, run:

```
python -m bugflow --project sample-app brief <ID>
```

This writes `sample-app/.bugflow/briefs/<ID>.md`.

Read each brief after it is written to confirm it contains:
- Issue summary
- Relevant log excerpt
- Policy section citation
- Source file and symbol
- Suggested test approach

If a brief is missing any of these sections, add them by editing
`sample-app/.bugflow/briefs/<ID>.md` directly before proceeding.

For duplicate issues: update the duplicate issue file to add a `Closes: ISSUE-<canonical>`
line, then skip brief generation — no separate brief or fix is needed.

---

## Step 4 — Spawn one fixer subagent per unique bug IN THE SAME TURN

In a **single assistant turn**, call `spawn_subagent` once for each unique bug.
All calls must appear in the same turn so they execute in parallel.

For each unique issue `<ID>`, spawn with:
- `name`: `"general"`
- `description`: >-
    You are a BugFlow fixer working in bugflow-fixer mode.
    Follow the bugflow-fix skill exactly.
    Brief path: sample-app/.bugflow/briefs/<ID>.md
    Issue ID: <ID>
    Complete all steps through `python -m bugflow --project sample-app log <ID> fix`
    and `python -m bugflow --project sample-app verify --issue <ID>`,
    then return: root cause (with policy citation), fix description, test name,
    and verify output.
- `fork_context`: `false`

Do not spawn subagents sequentially across multiple turns — all must be launched
in the same turn to run in parallel.

---

## Step 5 — Review each fix

When all subagents have returned, for each result:

1. Read the diff produced by the fixer (check `sample-app/tests/` for the new test
   and `sample-app/shopcart/` for the product change).
2. Verify the root cause cites a policy section.
3. Verify a test named `test_issue_<ID>_*` exists in `sample-app/tests/`.
4. If either check fails, note the gap — do NOT re-spawn; record the issue in the
   report instead.

---

## Step 6 — Draft a PR per unique bug

For each fix that passed review, run (substituting the one-line root cause and fix
summaries returned by the fixer subagent for `ROOT_CAUSE` and `FIX`):

```
python -m bugflow --project sample-app pr <ID> \
  --root-cause "ROOT_CAUSE" \
  --fix "FIX"
```

Read the generated PR description and confirm it references the issue, the policy
section, and the test name.

---

## Step 7 — Report

Run the impact report:

```
python -m bugflow --project sample-app report
```

Read `sample-app/.bugflow/triage.md` (updated by this run) and the report output.
Summarise in chat:
- Total unique bugs found
- Duplicates closed
- Fixes applied (APPROVE / gap noted)
- PR descriptions generated
- Any step that could not be completed and why
