# BugFlow Project Rules

These rules apply to every agent and mode operating in this workspace.

## 1. Docs win over code

When there is a conflict between what the source code does and what a policy document
(`sample-app/docs/`) specifies, the policy document defines correct behaviour.
Always locate and cite the exact section of the relevant policy doc before diagnosing
or fixing a bug.

## 2. Regression test required

No bug fix may be merged without a new test in `sample-app/tests/` that:
- was **failing** on the unmodified codebase, and
- **passes** after the fix is applied.

This is a hard gate — verify the test exists and cite its name before declaring a bug fixed.

## 3. Duplicates close via canonical

When triage identifies that two issues share the same root cause, the later-filed issue
is closed as a duplicate. Only ONE fix is written, targeting the canonical (earliest) issue.
The duplicate issue file is updated with a `Closes: ISSUE-<canonical>` line; no separate PR
is opened for it.

## 4. stdlib only

The `bugflow/` CLI toolkit must remain stdlib-only (no third-party packages). Fixes to
`sample-app/` may use whatever the app already imports; they must not add new dependencies.
