# BugFlow — IBM Bob 2.0 Hackathon Entry

## Problem

Before a single line of fix code is written, engineers work through a long, serial chain of
manual steps to handle each bug report. Each step requires context switching between tools
(issue tracker, log viewer, policy docs, editor, CI) with no shared state between them.
The result is an estimated **~2.7 hours per bug**, high duplicate-fix rate,
and frequent "fix ships, behaviour still wrong" regressions because the reproducing test
was skipped under time pressure.

---

## Manual Baseline (per-stage estimates)

| # | Stage | Who / Tool | Est. time | Pain point |
|---|-------|-----------|-----------|------------|
| 1 | **Triage** — read report, spot duplicates, assign severity | Engineer + issue tracker | 20 min / report | Same root cause reported 3–5× before anyone notices |
| 2 | **Context** — find request in logs, read stack trace, map to code | Engineer + grep / log viewer | 45 min / bug | Logs are noisy; trace spans multiple services |
| 3 | **Policy** — locate the doc that defines correct behaviour | Engineer + wiki | included in context | Doc is stale or absent ~30 % of the time |
| 4 | **Reproduce** — write a failing test that pins the bug | Engineer | 35 min / bug | Most often skipped; fix ships without a test |
| 5 | **Fix** — write the minimal code change | Engineer | 25 min / bug | Over-scoped without a tight test to aim at |
| 6 | **Verify** — run test suite, confirm fix, check no regression | Engineer + CI | 20 min / bug | Slow feedback loop; flaky tests mask real failures |
| 7 | **PR** — write description, pick reviewer, link issue | Engineer | 15 min / bug | Reviewer has no context; review takes another cycle |

**Total (estimates): ~2.7 h / bug** across stages 2–7 (triage counted separately per report).

---

## Target

| Metric | Baseline (est.) | Target |
|--------|----------------|--------|
| Time from report to merged PR | ~2.7 h | ≤ 45 min |
| Bugs fixed without a reproducing test | ~60 % | 0 % |
| Duplicate fixes for same root cause | ~20 % | < 5 % |
| PR descriptions rated "sufficient context" by reviewer | ~50 % | > 90 % |

---

## Solution Overview

**BugFlow** combines:

- **`sample-app/`** — a small Python web service with seeded, realistic bugs, a GitHub-style
  issue list, synthetic log files, and policy docs; provides a repeatable benchmark baseline.
- **`bugflow/` CLI toolkit** — stdlib-only Python commands that do the deterministic, mechanical
  steps (deduplication hash, log search, test scaffolding, CI invocation, PR draft generation,
  impact report). No LLM in the hot path for steps that don't need judgement.
- **`.bob/` configuration** — custom Bob modes, rules files, skills, and a `/bugflow` slash
  command that orchestrate the judgement-heavy steps via parallel subagents (one subagent per
  open bug, reproduce-first discipline enforced by a quality gate).
- **Live run + impact report** — end-to-end execution against the sample app's seeded bugs,
  with before/after timing and a machine-readable `impact.json`.

---

## Build Plan

### Part 1 — `sample-app/`: seeded benchmark target

**Intent:** Provide a self-contained, reproducible app with known bugs so every demo run
starts from the same ground truth.

**Expected outcomes:**
- `sample-app/app.py` — minimal Flask/stdlib HTTP service with 5 seeded bugs (off-by-one,
  missing auth check, wrong status code, stale cache, unhandled edge case).
- `sample-app/issues/` — one Markdown file per bug, GitHub-style (title, description,
  steps to reproduce, environment).
- `sample-app/logs/` — synthetic NDJSON log files with realistic noise and one stack trace
  per seeded bug.
- `sample-app/policy/` — short Markdown policy docs defining correct behaviour for each
  affected endpoint.
- `sample-app/tests/` — empty test directory (intentionally empty; BugFlow will populate it).

**Todo:**
- [ ] Scaffold `sample-app/` directory layout.
- [ ] Write `app.py` with 5 labelled seeded bugs.
- [ ] Write 5 issue Markdown files in `issues/`.
- [ ] Generate synthetic log files in `logs/` with matching stack traces.
- [ ] Write policy docs in `policy/`.

**Status:** `[ ] pending`

---

### Part 2 — `bugflow/` CLI toolkit

**Intent:** Automate every deterministic step so engineers never perform mechanical work
by hand; each command is stdlib-only for zero-dependency portability.

**Expected outcomes:**
- `bugflow/cli.py` — entry point; dispatches subcommands.
- `bugflow/triage.py` — reads `issues/`, computes similarity hash, flags duplicates,
  outputs ranked triage list.
- `bugflow/brief.py` — given an issue ID, reads the matching log snippet and policy doc,
  writes a structured `brief.md` that Bob subagents consume.
- `bugflow/log.py` — searches NDJSON logs for a request ID or error pattern, extracts the
  relevant window, formats it.
- `bugflow/verify.py` — runs the test suite (subprocess), parses result, returns
  pass/fail + coverage delta.
- `bugflow/pr.py` — templates a PR description from issue, brief, diff summary, and
  test results; suggests a reviewer from `CODEOWNERS`.
- `bugflow/report.py` — reads timing data written by each command, produces
  `impact.json` + human-readable `impact.md`.

**Todo:**
- [ ] Write `cli.py` dispatcher.
- [ ] Implement `triage.py` with duplicate detection.
- [ ] Implement `brief.py` linking issue → log → policy.
- [ ] Implement `log.py` NDJSON search and windowed extract.
- [ ] Implement `verify.py` subprocess test runner.
- [ ] Implement `pr.py` PR description templater.
- [ ] Implement `report.py` timing aggregator.

**Status:** `[ ] pending`

---

### Part 3 — `.bob/` configuration

**Intent:** Give Bob the context and authority to orchestrate the judgement steps —
understanding what "correct behaviour" means, enforcing reproduce-first discipline,
and running one subagent per bug in parallel.

**Expected outcomes:**
- `.bob/rules/bugflow.md` — project rules: reproduce-first gate, policy-doc citation
  requirement, PR checklist.
- `.bob/skills/bugflow-triage.md` — skill: how to read a `brief.md`, rank fixes, spot
  duplicate root causes.
- `.bob/skills/bugflow-fix.md` — skill: reproduce-first workflow, minimal-change
  discipline, test-then-fix sequence.
- `.bob/custom_modes.yaml` — two modes: `bugflow-triage` (read-only, analysis) and
  `bugflow-fix` (write, one bug at a time, quality-gated).
- `.bob/commands/bugflow.md` — `/bugflow` slash command definition that accepts an issue
  ID, calls `bugflow brief`, spawns a fix subagent, calls `bugflow verify`, calls
  `bugflow pr`.

**Todo:**
- [ ] Write `rules/bugflow.md`.
- [ ] Write `skills/bugflow-triage.md`.
- [ ] Write `skills/bugflow-fix.md`.
- [ ] Write `custom_modes.yaml` with both modes.
- [ ] Write `commands/bugflow.md` slash command.

**Status:** `[ ] pending`

---

### Part 4 — Live run + impact report

**Intent:** Demonstrate end-to-end execution on the seeded bugs and produce a measurable
before/after impact report that satisfies the hackathon judging criteria.

**Expected outcomes:**
- All 5 seeded bugs triaged, briefed, fixed (with a new test each), verified, and PR-drafted
  in a single `/bugflow` session.
- `impact.json` with per-bug and aggregate timing, test coverage delta, and duplicate
  detection results.
- `impact.md` — human-readable summary suitable for the hackathon submission.
- `DEMO.md` — step-by-step instructions for judges to reproduce the live run.

**Todo:**
- [ ] Run `bugflow triage` against all 5 issues and record timing.
- [ ] Run `/bugflow <id>` for each bug, capture subagent output and wall-clock time.
- [ ] Run `bugflow report` to produce `impact.json` and `impact.md`.
- [ ] Write `DEMO.md`.

**Status:** `[ ] pending`
