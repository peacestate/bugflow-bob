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
