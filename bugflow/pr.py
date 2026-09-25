"""pr command — write a PR markdown description for an issue."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bugflow import state


def run_pr(project: Path, issue_id: str, root_cause: str, fix: str) -> None:
    triage_path = state.triage_json_path(project)
    if not triage_path.exists():
        print("Run 'triage' first.", file=sys.stderr)
        sys.exit(1)

    triage_data = json.loads(triage_path.read_text(encoding="utf-8"))
    all_issues = {i["id"]: i for i in triage_data["all_issues"]}
    rec = all_issues.get(issue_id)
    if rec is None:
        print(f"Issue {issue_id} not found.", file=sys.stderr)
        sys.exit(1)

    # Canonical record
    if not rec["canonical"] and rec.get("duplicate_of"):
        canonical_rec = all_issues.get(rec["duplicate_of"], rec)
    else:
        canonical_rec = rec

    dup_ids = canonical_rec.get("duplicates", [])

    # Brief path
    brief_path = state.briefs_dir(project) / f"{canonical_rec['id']}.md"

    # Reviewer
    owner = canonical_rec.get("owner") or "unassigned"

    # Closes line
    closes = [f"Closes {canonical_rec['id']}"]
    if dup_ids:
        closes.append(f"Closes duplicates: {', '.join(dup_ids)}")
    closes_str = "  \n".join(closes)

    # Issue title
    title = canonical_rec.get("title", issue_id)

    # Suspect
    suspect_file = None
    suspect_line = None
    if canonical_rec.get("tb_info"):
        tbi = canonical_rec["tb_info"]
        suspect_file = tbi["file"]
        suspect_line = tbi["lineno"]
    elif canonical_rec.get("suspect"):
        sus = canonical_rec["suspect"]
        suspect_file = sus["file"]
        suspect_line = sus["lineno"]

    # Regression test
    num_m = re.search(r"(\d+)$", canonical_rec["id"])
    num = num_m.group(1) if num_m else canonical_rec["id"]
    regression_name = f"test_issue_{num}_{canonical_rec.get('component', 'unknown')}_regression"

    lines = [
        f"# PR: Fix {canonical_rec['id']} — {title}",
        "",
        "## Summary",
        "",
        f"{closes_str}",
        "",
        "## Root Cause",
        "",
        root_cause,
        "",
        "## Fix",
        "",
        fix,
        "",
    ]

    if suspect_file:
        lines += [
            "## Evidence",
            "",
            f"Suspect: `{suspect_file}` line {suspect_line}  ",
            f"Bug brief: `{brief_path.relative_to(project) if brief_path.exists() else brief_path}`",
            "",
        ]

    lines += [
        "## Verification",
        "",
        f"Regression test: `{regression_name}` (ISSUE-{num} in docstring)  ",
        "Run: `python -m bugflow --project . verify`",
        "",
        "## Suggested Reviewer",
        "",
        f"`{owner}`",
        "",
    ]

    out_path = state.pr_dir(project) / f"{canonical_rec['id']}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    state.record_stage(project, issue_id, "pr")
    print(f"PR description written: {out_path}")
    import sys as _sys
    text = out_path.read_text(encoding="utf-8")
    _sys.stdout.buffer.write(("\n" + text).encode("utf-8"))
    _sys.stdout.buffer.flush()
