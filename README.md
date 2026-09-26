# BugFlow — IBM Bob 2.0 Hackathon Entry

> **Turn raw bug reports into verified, PR-ready fixes — automatically.**

See [PROBLEM.md](PROBLEM.md) for the full problem statement, per-stage baseline table, and build plan.

---

## The Problem

Before a single line of fix code is written, engineers manually work through a long, serial chain:
triage the report, find the request in logs, locate the policy doc, write a reproducing test
(often skipped), implement the fix, verify, and write the PR. Each step requires a context switch
between tools with no shared state between them — roughly **~2.7 hours per bug** (estimated).
Duplicate reports for the same root cause are routinely missed, leading to duplicate fixes.

---

## Architecture

```
bugflow-bob/
│
├── PROBLEM.md              ← problem statement & baseline table
├── README.md               ← this file
│
├── bugflow/                ← stdlib-only Python CLI toolkit
│   ├── cli.py              ← entry point (python -m bugflow --project <dir> <cmd>)
│   ├── triage.py           ← reads issues/, deduplicates, ranks by severity
│   ├── brief.py            ← issue + log + policy doc → structured brief.md
│   ├── log_cmd.py          ← records stage events to timeline.jsonl
│   ├── verify.py           ← runs pytest, checks regression-test gate
│   ├── pr.py               ← templates PR description from brief + diff
│   ├── report.py           ← aggregates timeline → report.md + report.html
│   └── state.py            ← .bugflow/ directory and timeline helpers
│
├── sample-app/             ← benchmark target: realistic Python checkout service
│   ├── bugflow.json        ← project config (bugs, policy docs, baseline minutes)
│   ├── shopcart/           ← source code with 3 seeded bugs
│   ├── issues/             ← 4 GitHub-style bug reports (ISSUE-101 … ISSUE-104)
│   ├── docs/               ← policy docs (pricing, inventory, shipping SLA)
│   │   └── demo-run/       ← committed artifacts from the live demo run
│   ├── logs/               ← synthetic NDJSON logs with realistic noise
│   └── tests/              ← test suite (regression tests added by BugFlow)
│
├── .bob/                   ← IBM Bob 2.0 configuration
│   ├── custom_modes.yaml   ← bugflow-lead, bugflow-fixer, bugflow-reviewer modes
│   ├── commands/bugflow.md ← /bugflow slash command definition
│   ├── rules/              ← workspace rules (policy docs win, regression required)
│   └── skills/             ← bugflow-triage, bugflow-fix, bugflow skills
│
├── tests/                  ← unit tests for the bugflow/ toolkit itself
└── bob_sessions/           ← session logs from all 8 tasks (tasks 01–08); extra_*.png files are screenshots from the demo recording
```

---

## IBM Bob 2.0 Features Used

| Feature | How BugFlow uses it |
|---|---|
| **Agent mode** | Default mode for writing, running and verifying fixes |
| **Custom modes** | `bugflow-lead` orchestrates the pipeline; `bugflow-fixer` enforces reproduce-first; `bugflow-reviewer` is read-only for reviewing diffs |
| **Parallel subagents** | Lead spawns one `spawn_subagent` per unique bug; all three fixer subagents run concurrently, each isolated in its own context |
| **Skills** | `bugflow-triage` (step-by-step lead pipeline), `bugflow-fix` (reproduce-first fixer workflow), `bugflow` (general toolkit reference) |
| **Workspace rules** | `.bob/rules/01-bugflow.md` enforces: policy docs win over code, regression test required before merge, duplicates close via canonical, stdlib-only in `bugflow/` |
| **Document understanding** | Fixer subagents read policy docs (`docs/pricing-policy.md`, `docs/inventory.md`, `docs/shipping-sla.md`) and cite the exact rule violated before writing any fix |
| **`/bugflow` command** | `.bob/commands/bugflow.md` slash command — one invocation triggers the full triage → brief → parallel fix → verify → PR → report pipeline |

---

## Quick Start

```bash
# Clone the repo
git clone <repo-url>
cd bugflow-bob

# Run the full pipeline against sample-app (requires IBM Bob 2.0)
# In Bob, type:
/bugflow

# Or run individual CLI steps manually:
python -m bugflow --project sample-app start --mode agent
python -m bugflow --project sample-app triage
python -m bugflow --project sample-app brief ISSUE-101 ISSUE-102 ISSUE-103
# ... (Bob fixer subagents write tests and fix code) ...
python -m bugflow --project sample-app verify
python -m bugflow --project sample-app report

# Run the toolkit unit tests
python -m pytest tests/ -v

# Run the sample-app regression tests (added by the demo run)
python -m pytest sample-app/tests/ -v
```

---

## Live Demo Run Results

The demo was run against `sample-app/` with 4 seeded bug reports and 3 unique root causes.
All times below are wall-clock measurements; baseline minutes are **estimates** from
[PROBLEM.md](PROBLEM.md).

| Metric | Result |
|---|---|
| Bug reports processed | 4 |
| Unique bugs fixed | 3 |
| Duplicates detected | 1 (ISSUE-104 → ISSUE-102) |
| Regression tests added | 3 |
| Verify gate | ✅ PASSED |
| Wall-clock time | **4.0 min** |
| Manual baseline estimate | **500 min** (20 min × 4 reports + 140 min × 3 bugs) |
| **Speedup** | **~124×** |

### What the baseline of 500 min represents (estimates)

```
Triage stage:   20 min/report × 4 reports =  80 min  (read, deduplicate, assign severity)
Context stage:  45 min/bug    × 3 bugs    = 135 min  (find logs, read stack trace, map to code)
Reproduce:      35 min/bug    × 3 bugs    = 105 min  (write failing test — often skipped)
Fix:            25 min/bug    × 3 bugs    =  75 min  (minimal code change)
Verify:         20 min/bug    × 3 bugs    =  60 min  (run CI, confirm regression-free)
PR:             15 min/bug    × 3 bugs    =  45 min  (description, reviewer, link issue)
                                            ─────────
                                            500 min total (estimates)
```

### Bugs fixed

| Issue | Severity | Component | Root Cause | Policy Violated |
|---|---|---|---|---|
| ISSUE-103 | Critical | shipping | Region string not lowercased before dict lookup → KeyError → 500 | `S-1`: all regions must resolve |
| ISSUE-102 | High | inventory | `on_hand > qty` (strict) rejects last-unit purchase | `I-1`: reservation must succeed when `on_hand >= qty` |
| ISSUE-101 | Medium | pricing | `round(float(...))` loses sub-cent precision | `P-2`: totals must use exact decimal arithmetic |

ISSUE-104 (VIP customer cannot buy last sneaker) is a duplicate of ISSUE-102 — same root cause,
different SKU. It was automatically detected by triage's fingerprint hash and closed without a
separate fix.

Committed demo artifacts are in [`sample-app/docs/demo-run/`](sample-app/docs/demo-run/):
- [`triage.md`](sample-app/docs/demo-run/triage.md) — ranked triage output
- [`report.md`](sample-app/docs/demo-run/report.md) — full session report
- [`report.html`](sample-app/docs/demo-run/report.html) — HTML report with metric cards
- [`pr/`](sample-app/docs/demo-run/pr/) — PR descriptions for all three fixes

---

## Built with IBM Bob

The entire project was built in IBM Bob 2.0 across 8 sessions, all logged in [`bob_sessions/`](bob_sessions/).

| Task | Session | What happened |
|---|---|---|
| 01 | [`task01_plan_and_sample_app.md`](bob_sessions/task01_plan_and_sample_app.md) | Wrote PROBLEM.md; scaffolded `sample-app/` with seeded bugs, issues, logs, policy docs |
| 02 | [`task02_bugflow_toolkit.md`](bob_sessions/task02_bugflow_toolkit.md) | Built the entire `bugflow/` CLI toolkit (triage, brief, log, verify, pr, report) — stdlib-only |
| 03 | [`task03_bob_modes_skills.md`](bob_sessions/task03_bob_modes_skills.md) | Wrote `.bob/` config: custom modes, rules, skills, `/bugflow` slash command |
| 04 | [`task04_commit_and_push.md`](bob_sessions/task04_commit_and_push.md) | Committed `.bob/` and `bob_sessions/` and pushed to main (no test run) |
| 05 | [`task05_first_demo_run_failed.md`](bob_sessions/task05_first_demo_run_failed.md) | **First `/bugflow` run failed** — fixer subagents inherited lead's restricted edit permissions and could not write to `shopcart/` or `tests/`. One subagent fell back to shell edits, leaving pricing.py half-changed. |
| 06 | [`task06_fix_permissions_and_reset.md`](bob_sessions/task06_fix_permissions_and_reset.md) | Bob diagnosed the permission inheritance issue, reset the demo (`git checkout -- sample-app`), and fixed `custom_modes.yaml` to expand `bugflow-lead`'s `fileRegex` to include `shopcart/*.py` and `tests/*.py` |
| 07 | [`task07_demo_run_parallel_fixers.md`](bob_sessions/task07_demo_run_parallel_fixers.md) | Successful `/bugflow` run — Bob spawned 3 parallel fixer subagents, each wrote a failing regression test first, then applied the minimal fix, verified, and drafted a PR. All 3 bugs fixed in 4 min wall-clock. |
| 08 | [`task08_wrapup_readme_report.md`](bob_sessions/task08_wrapup_readme_report.md) | Fixed the baseline math (500 min, 123.8x), corrected ISSUE-104 wording, copied demo-run artifacts to `sample-app/docs/demo-run/`, wrote this README, updated tests |

The failed first run (task 05) and the self-correction (task 06) are kept in `bob_sessions/`
deliberately — they demonstrate how Bob identifies and recovers from a configuration mistake;
the developer spotted the blocked fixer and described the cause; Bob then reset the demo and fixed the mode configuration.

---

## Project Rules

Defined in [`.bob/rules/01-bugflow.md`](.bob/rules/01-bugflow.md):

1. **Policy docs win** — when source code conflicts with a policy doc, the policy doc defines correct behaviour
2. **Regression test required** — no fix may be merged without a new `test_issue_NNN_*` test that was failing before the fix
3. **Duplicates close via canonical** — one fix per root cause; the duplicate issue is closed, not fixed separately
4. **stdlib only** — the `bugflow/` CLI toolkit must have zero third-party dependencies

---

*Made with IBM Bob 2.0*
