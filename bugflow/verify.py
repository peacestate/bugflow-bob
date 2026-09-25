"""verify command — run unittest suite; require regression tests; gate pass/fail."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from bugflow import state


def _regression_test_exists(project: Path, issue_id: str) -> bool:
    """Return True if any test file contains a function matching test_issue_<n>."""
    m = re.search(r"(\d+)$", issue_id)
    if not m:
        return False
    num = m.group(1)
    pattern = re.compile(rf"def test_issue_{num}_")
    tests_dir = project / "tests"
    if not tests_dir.is_dir():
        return False
    for tf in tests_dir.rglob("*.py"):
        text = tf.read_text(encoding="utf-8")
        if pattern.search(text):
            return True
    return False


def _issue_in_docstring(project: Path, issue_id: str) -> bool:
    """Return True if the issue_id appears in a docstring of the matching test."""
    m = re.search(r"(\d+)$", issue_id)
    if not m:
        return False
    num = m.group(1)
    func_pattern = re.compile(rf"def test_issue_{num}_")
    tests_dir = project / "tests"
    if not tests_dir.is_dir():
        return False
    for tf in tests_dir.rglob("*.py"):
        text = tf.read_text(encoding="utf-8")
        # Find functions matching the pattern and check subsequent docstring
        for match in func_pattern.finditer(text):
            # Look for docstring in next ~5 lines
            snippet = text[match.start():match.start() + 400]
            if issue_id in snippet:
                return True
    return False


def _run_suite(project: Path, keyword: str | None = None) -> tuple[bool, str]:
    """Run the test suite; return (passed, output)."""
    cmd = [
        sys.executable, "-m", "unittest", "discover",
        "-s", "tests", "-t", ".",
    ]
    if keyword:
        # unittest discover doesn't have -k; use the test runner's -k if available (Python 3.11+)
        cmd = [
            sys.executable, "-m", "unittest", "discover",
            "-s", "tests", "-t", ".", "-k", keyword,
        ]
    result = subprocess.run(
        cmd,
        cwd=str(project),
        capture_output=True,
        text=True,
    )
    output = result.stdout + "\n" + result.stderr
    passed = result.returncode == 0
    return passed, output


def run_verify(project: Path, issue_id: str | None = None) -> bool:
    """Run the gate. Returns True if PASSED, False if BLOCKED."""
    # Load triage data to know which issues exist
    triage_path = state.triage_json_path(project)
    canonical_issues: list[str] = []
    if triage_path.exists():
        triage_data = json.loads(triage_path.read_text(encoding="utf-8"))
        canonical_issues = [i["id"] for i in triage_data.get("all_issues", []) if i.get("canonical")]

    # Which issues to check
    issues_to_check = [issue_id] if issue_id else canonical_issues

    blocked_reasons = []

    for iid in issues_to_check:
        if not _regression_test_exists(project, iid):
            blocked_reasons.append(f"  {iid}: no regression test (expected 'def test_issue_<n>_...')")
        elif not _issue_in_docstring(project, iid):
            blocked_reasons.append(f"  {iid}: regression test found but {iid} not in its docstring")

    # Run full suite first
    suite_passed, suite_output = _run_suite(project)
    if not suite_passed:
        blocked_reasons.append("  full test suite: FAILING")

    print("=== Test Suite Output ===")
    print(suite_output.strip())

    # Run per-issue regression tests
    for iid in issues_to_check:
        m = re.search(r"(\d+)$", iid)
        if not m:
            continue
        num = m.group(1)
        passed, out = _run_suite(project, keyword=f"issue_{num}")
        print(f"\n=== Regression test for {iid} (-k issue_{num}) ===")
        print(out.strip())
        # Note: if no matching tests exist, unittest returns 0 but says 0 tests run
        # We already checked existence above; here we check the run outcome
        if not passed:
            blocked_reasons.append(f"  {iid}: regression test run FAILED")

    print()
    if blocked_reasons:
        print("GATE: BLOCKED")
        for reason in blocked_reasons:
            print(reason)
        state.record_stage(project, issue_id or "all", "verify:blocked")
        return False
    else:
        print("GATE: PASSED")
        state.record_stage(project, issue_id or "all", "verify:passed")
        return True
