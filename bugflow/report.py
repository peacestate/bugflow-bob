"""report command — aggregate timings, write report.md and report.html."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bugflow import state

# Manual baseline per-stage estimates in minutes (from PROBLEM.md)
BASELINE_MINUTES: dict[str, float] = {
    "triage": 20.0,       # per report
    "brief": 45.0,        # context stage
    "reproduce": 35.0,
    "fix": 25.0,
    "verify:passed": 20.0,
    "verify:blocked": 20.0,
    "pr": 15.0,
}

BASELINE_TOTAL_PER_BUG = 140.0  # minutes (stages 2-7, excludes triage which is counted per report)


def run_report(project: Path) -> None:
    timeline = state.read_timeline(project)
    if not timeline:
        print("No timeline data found. Run 'start' and some commands first.")
        return

    triage_path = state.triage_json_path(project)
    triage_data: dict = {}
    if triage_path.exists():
        triage_data = json.loads(triage_path.read_text(encoding="utf-8"))

    all_issues = {i["id"]: i for i in triage_data.get("all_issues", [])}
    canonical_ids = [i["id"] for i in triage_data.get("all_issues", []) if i.get("canonical")]
    total_reports = len(all_issues)
    unique_bugs = len(canonical_ids)
    duplicate_count = total_reports - unique_bugs

    # Collect per-issue stages with timestamps
    # Each event: {type, issue, stage, ts}
    stage_events: list[dict] = [e for e in timeline if e.get("type") == "stage"]

    # Session start time
    start_events = [e for e in timeline if e.get("type") == "start"]
    session_start = start_events[0]["ts"] if start_events else timeline[0]["ts"]
    session_mode_val = start_events[0].get("mode", "agent") if start_events else "agent"

    # Group stages by issue
    per_issue: dict[str, list[dict]] = defaultdict(list)
    for ev in stage_events:
        per_issue[ev.get("issue", "all")].append(ev)

    # Approximate wall-clock: difference from session start to last event
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return datetime.now(timezone.utc)

    start_dt = _parse_ts(session_start)
    last_dt = _parse_ts(timeline[-1]["ts"])
    wall_clock_seconds = max(0, (last_dt - start_dt).total_seconds())
    wall_clock_minutes = wall_clock_seconds / 60.0

    # Count regression tests
    tests_dir = project / "tests"
    regression_tests: list[str] = []
    if tests_dir.is_dir():
        for tf in sorted(tests_dir.rglob("*.py")):
            text = tf.read_text(encoding="utf-8")
            for m in re.finditer(r"def (test_issue_\d+_\S+)", text):
                regression_tests.append(m.group(1))

    regression_coverage = len(regression_tests)

    # Speedup
    if session_mode_val == "scripted":
        speedup_note = "No speedup claimed (scripted mode)."
        speedup = None
    else:
        baseline_total = BASELINE_TOTAL_PER_BUG * unique_bugs + 20.0 * total_reports
        if wall_clock_minutes > 0:
            speedup = baseline_total / wall_clock_minutes
            speedup_note = (
                f"Baseline estimate: {baseline_total:.0f} min for {unique_bugs} bugs "
                f"({total_reports} reports).  \n"
                f"Actual wall-clock: {wall_clock_minutes:.1f} min.  \n"
                f"Speedup: **{speedup:.1f}×**"
            )
        else:
            speedup = None
            speedup_note = "Wall-clock time too short to compute speedup."

    # Per-stage summary
    stage_counts: dict[str, int] = defaultdict(int)
    for ev in stage_events:
        stage_counts[ev.get("stage", "?")] += 1

    # Build report.md
    md_lines = [
        "# BugFlow Session Report",
        "",
        f"**Session mode:** {session_mode_val}  ",
        f"**Session start:** {session_start}  ",
        f"**Last event:** {timeline[-1]['ts']}  ",
        f"**Wall-clock time:** {wall_clock_minutes:.1f} min",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        "|---|---|",
        f"| Total reports | {total_reports} |",
        f"| Unique bugs | {unique_bugs} |",
        f"| Duplicates resolved | {duplicate_count} |",
        f"| Regression tests added | {regression_coverage} |",
        "",
        "## Stage Timings",
        "",
        "| Stage | Count |",
        "|---|---|",
    ]
    for stage, count in sorted(stage_counts.items()):
        md_lines.append(f"| {stage} | {count} |")
    md_lines.append("")

    if regression_tests:
        md_lines += ["## Regression Tests", ""]
        for t in regression_tests:
            md_lines.append(f"- `{t}`")
        md_lines.append("")

    md_lines += [
        "## Speedup",
        "",
        speedup_note,
        "",
    ]

    report_md = "\n".join(md_lines)
    md_path = state.bugflow_dir(project) / "report.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"Report written: {md_path}")

    # Write report.html
    html = _make_html(report_md, total_reports, unique_bugs, duplicate_count,
                      regression_coverage, wall_clock_minutes, speedup, session_mode_val,
                      stage_counts)
    html_path = state.bugflow_dir(project) / "report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML report written: {html_path}")


def _make_html(report_md: str, total_reports: int, unique_bugs: int,
               duplicate_count: int, regression_coverage: int,
               wall_clock_minutes: float, speedup: float | None,
               session_mode_val: str, stage_counts: dict) -> str:
    speedup_str = f"{speedup:.1f}×" if speedup else "N/A"
    stage_rows = "".join(
        f"<tr><td>{s}</td><td>{c}</td></tr>"
        for s, c in sorted(stage_counts.items())
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BugFlow Report</title>
<style>
  body {{font-family: -apple-system, "Segoe UI", sans-serif; max-width: 760px;
         margin: 40px auto; padding: 0 20px; color: #1f2328; line-height: 1.6;}}
  h1 {{border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;}}
  h2 {{color: #3b82d4; margin-top: 32px;}}
  table {{border-collapse: collapse; width: 100%; margin: 16px 0;}}
  th {{background: #f7f8fa; text-align: left; padding: 8px 12px;
       border: 1px solid #e5e7eb;}}
  td {{padding: 8px 12px; border: 1px solid #e5e7eb;}}
  .metric {{font-size: 2em; font-weight: bold; color: #3b82d4;}}
  .card {{background: #f7f8fa; border: 1px solid #e5e7eb; border-radius: 6px;
          padding: 16px; margin: 8px 0; display: inline-block; min-width: 140px;
          text-align: center;}}
  .cards {{display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0;}}
  footer {{margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 12px;
           text-align: center; font-size: 12px; color: #57606a;}}
</style>
</head>
<body>
<h1>BugFlow Session Report</h1>
<div class="cards">
  <div class="card"><div class="metric">{total_reports}</div>Reports</div>
  <div class="card"><div class="metric">{unique_bugs}</div>Unique bugs</div>
  <div class="card"><div class="metric">{duplicate_count}</div>Duplicates resolved</div>
  <div class="card"><div class="metric">{regression_coverage}</div>Regression tests</div>
  <div class="card"><div class="metric">{wall_clock_minutes:.1f}m</div>Wall-clock</div>
  <div class="card"><div class="metric">{speedup_str}</div>Speedup</div>
</div>
<h2>Stage Counts</h2>
<table><tr><th>Stage</th><th>Count</th></tr>{stage_rows}</table>
<footer>Made with IBM Bob</footer>
</body>
</html>"""
