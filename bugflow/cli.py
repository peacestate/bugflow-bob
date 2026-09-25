"""CLI dispatcher: python -m bugflow --project <dir> <command> [args]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bugflow import state


def _resolve_project(raw: str) -> Path:
    p = Path(raw).resolve()
    if not p.is_dir():
        print(f"Error: project directory not found: {raw}", file=sys.stderr)
        sys.exit(1)
    return p


def cmd_start(project: Path, args: argparse.Namespace) -> None:
    """Reset timeline and record start."""
    state.ensure_dir(project)
    tl = state.timeline_path(project)
    if tl.exists():
        tl.unlink()
    state.append_timeline(project, {
        "type": "start",
        "mode": args.mode,
    })
    # Add .bugflow/ to .gitignore if not already present
    gi = project / ".gitignore"
    entry = ".bugflow/"
    if gi.exists():
        text = gi.read_text(encoding="utf-8")
        if entry not in text:
            with gi.open("a", encoding="utf-8") as fh:
                fh.write(f"\n{entry}\n")
    else:
        gi.write_text(f"{entry}\n", encoding="utf-8")
    print(f"Session started (mode={args.mode}). Timeline reset.")


def cmd_triage(project: Path, args: argparse.Namespace) -> None:
    from bugflow.triage import run_triage
    run_triage(project, print_json=args.json)


def cmd_brief(project: Path, args: argparse.Namespace) -> None:
    from bugflow.brief import run_brief
    run_brief(project, args.ISSUE)


def cmd_log(project: Path, args: argparse.Namespace) -> None:
    from bugflow.log_cmd import run_log
    run_log(project, args.ISSUE, args.stage)


def cmd_verify(project: Path, args: argparse.Namespace) -> None:
    from bugflow.verify import run_verify
    passed = run_verify(project, issue_id=args.issue)
    sys.exit(0 if passed else 1)


def cmd_pr(project: Path, args: argparse.Namespace) -> None:
    from bugflow.pr import run_pr
    run_pr(project, args.ISSUE, args.root_cause, args.fix)


def cmd_report(project: Path, args: argparse.Namespace) -> None:
    from bugflow.report import run_report
    run_report(project)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m bugflow",
        description="BugFlow — deterministic bug-workflow toolkit",
    )
    parser.add_argument("--project", required=True, metavar="DIR",
                        help="Path to the project directory")

    sub = parser.add_subparsers(dest="command", required=True)

    # start
    p_start = sub.add_parser("start", help="Reset timeline and record session start")
    p_start.add_argument("--mode", choices=["agent", "scripted"], default="agent")

    # triage
    p_triage = sub.add_parser("triage", help="Parse issues+logs, deduplicate, rank")
    p_triage.add_argument("--json", action="store_true", dest="json",
                          help="Print work queue as JSON")

    # brief
    p_brief = sub.add_parser("brief", help="Write markdown brief(s)")
    p_brief.add_argument("ISSUE", nargs="*",
                         help="Issue IDs (default: all canonical issues)")

    # log
    p_log = sub.add_parser("log", help="Record a stage for an issue")
    p_log.add_argument("ISSUE", help="Issue ID (e.g. ISSUE-101)")
    p_log.add_argument("stage", choices=["reproduce", "fix"],
                       help="Stage completed")

    # verify
    p_verify = sub.add_parser("verify", help="Run test suite and regression gate")
    p_verify.add_argument("--issue", metavar="ID",
                          help="Check only this issue's regression test")

    # pr
    p_pr = sub.add_parser("pr", help="Write a PR description")
    p_pr.add_argument("ISSUE", help="Issue ID")
    p_pr.add_argument("--root-cause", required=True, dest="root_cause",
                      metavar="TEXT", help="Root cause description")
    p_pr.add_argument("--fix", required=True, metavar="TEXT",
                      help="Fix description")

    # report
    sub.add_parser("report", help="Generate impact report")

    # --- parse ---
    args = parser.parse_args()
    project = _resolve_project(args.project)

    dispatch = {
        "start": cmd_start,
        "triage": cmd_triage,
        "brief": cmd_brief,
        "log": cmd_log,
        "verify": cmd_verify,
        "pr": cmd_pr,
        "report": cmd_report,
    }
    dispatch[args.command](project, args)
