"""Tests for bugflow — runs against a temp copy of sample-app."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure both the repo root (bugflow package) and sample-app (shopcart package) are importable.
REPO_ROOT = Path(__file__).parent.parent
SAMPLE_APP = REPO_ROOT / "sample-app"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SAMPLE_APP) not in sys.path:
    sys.path.insert(0, str(SAMPLE_APP))


def _make_temp_project() -> Path:
    """Return a temporary copy of sample-app."""
    tmp = Path(tempfile.mkdtemp())
    dest = tmp / "sample-app"
    shutil.copytree(str(SAMPLE_APP), str(dest),
                    ignore=shutil.ignore_patterns(".bugflow", "__pycache__", "*.pyc",
                                                  ".pytest_cache"))
    return dest


class TestStart(unittest.TestCase):
    """bugflow start resets the timeline and creates .bugflow/."""

    def setUp(self):
        self.project = _make_temp_project()

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def test_start_creates_bugflow_dir(self):
        from bugflow import state
        state.ensure_dir(self.project)
        state.append_timeline(self.project, {"type": "start", "mode": "agent"})
        self.assertTrue((self.project / ".bugflow").is_dir())

    def test_start_resets_timeline(self):
        from bugflow import state
        # Write some events, then reset
        state.append_timeline(self.project, {"type": "stage", "issue": "ISSUE-101", "stage": "triage"})
        tl = state.timeline_path(self.project)
        tl.unlink()
        state.append_timeline(self.project, {"type": "start", "mode": "agent"})
        events = state.read_timeline(self.project)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "start")

    def test_start_adds_gitignore(self):
        from bugflow.cli import cmd_start
        import argparse
        args = argparse.Namespace(mode="agent")
        cmd_start(self.project, args)
        gi = self.project / ".gitignore"
        self.assertTrue(gi.exists())
        self.assertIn(".bugflow/", gi.read_text())


class TestTriage(unittest.TestCase):
    """Triage produces correct 4-report -> 3-bug deduplication."""

    def setUp(self):
        self.project = _make_temp_project()
        # Add sample-app to sys.path so shopcart imports work during snippet reads
        if str(self.project) not in sys.path:
            sys.path.insert(0, str(self.project))

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def _run_triage(self) -> list[dict]:
        from bugflow.triage import run_triage
        return run_triage(self.project, print_json=False)

    def test_four_reports_loaded(self):
        from bugflow.triage import load_issues
        issues = load_issues(self.project)
        self.assertEqual(len(issues), 4)

    def test_three_unique_bugs(self):
        wq = self._run_triage()
        self.assertEqual(len(wq), 3, f"Expected 3 unique bugs, got {len(wq)}: {[b['id'] for b in wq]}")

    def test_issue_104_duplicate_of_102(self):
        self._run_triage()
        triage_path = self.project / ".bugflow" / "triage.json"
        data = json.loads(triage_path.read_text())
        all_issues = {i["id"]: i for i in data["all_issues"]}
        self.assertFalse(all_issues["ISSUE-104"]["canonical"],
                         "ISSUE-104 should be a duplicate (non-canonical)")
        self.assertEqual(all_issues["ISSUE-104"]["duplicate_of"], "ISSUE-102",
                         "ISSUE-104 should be a duplicate of ISSUE-102")

    def test_issue_102_severity_raised(self):
        """After merging ISSUE-104 (High) into ISSUE-102 (High), severity stays High."""
        self._run_triage()
        triage_path = self.project / ".bugflow" / "triage.json"
        data = json.loads(triage_path.read_text())
        all_issues = {i["id"]: i for i in data["all_issues"]}
        # Both are High, so canonical stays High
        self.assertEqual(all_issues["ISSUE-102"]["severity"].lower(), "high")

    def test_issue_101_suspect_is_pricing_py(self):
        """ISSUE-101 (wrong-result, no traceback) should point to pricing.py."""
        self._run_triage()
        triage_path = self.project / ".bugflow" / "triage.json"
        data = json.loads(triage_path.read_text())
        wq = {e["id"]: e for e in data["work_queue"]}
        self.assertIn("ISSUE-101", wq)
        sf = wq["ISSUE-101"].get("suspect_file", "")
        self.assertIn("pricing.py", sf,
                      f"Expected pricing.py suspect for ISSUE-101, got '{sf}'")

    def test_issue_101_suspect_line_is_return_statement(self):
        """ISSUE-101 suspect must be the return statement in order_total, not a comment.

        After the demo-run fix, pricing.py returns
        `total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
        Triage must still find this line (the only candidate return in order_total).
        """
        self._run_triage()
        triage_path = self.project / ".bugflow" / "triage.json"
        data = json.loads(triage_path.read_text())
        all_issues = {i["id"]: i for i in data["all_issues"]}
        suspect = all_issues["ISSUE-101"].get("suspect")
        self.assertIsNotNone(suspect, "ISSUE-101 should have a suspect")
        line = suspect.get("line", "")
        self.assertIn("return", line,
                      f"Expected suspect line to be a return statement but got: {line!r}")
        self.assertIn("total", line,
                      f"Expected suspect line to reference 'total' but got: {line!r}")

    def test_triage_md_written(self):
        self._run_triage()
        md = self.project / ".bugflow" / "triage.md"
        self.assertTrue(md.exists())
        content = md.read_text()
        self.assertIn("ISSUE-101", content)
        self.assertIn("ISSUE-102", content)
        self.assertIn("ISSUE-103", content)

    def test_triage_json_written(self):
        self._run_triage()
        jp = self.project / ".bugflow" / "triage.json"
        self.assertTrue(jp.exists())
        data = json.loads(jp.read_text())
        self.assertIn("work_queue", data)
        self.assertIn("all_issues", data)

    def test_critical_ranked_first(self):
        """ISSUE-103 (Critical) should rank first."""
        wq = self._run_triage()
        self.assertEqual(wq[0]["id"], "ISSUE-103")

    def test_owner_assigned(self):
        """Each canonical issue should have an owner from CODEOWNERS."""
        wq = self._run_triage()
        for entry in wq:
            self.assertIsNotNone(entry.get("owner"), f"{entry['id']} has no owner")
            self.assertNotEqual(entry["owner"], "unassigned",
                                f"{entry['id']} owner is unassigned")


class TestBrief(unittest.TestCase):
    """Brief generates a markdown file with all required sections."""

    def setUp(self):
        self.project = _make_temp_project()
        if str(self.project) not in sys.path:
            sys.path.insert(0, str(self.project))
        from bugflow.triage import run_triage
        run_triage(self.project, print_json=False)

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def _brief(self, issue_id: str) -> str:
        from bugflow.brief import write_brief
        import json
        data = json.loads((self.project / ".bugflow" / "triage.json").read_text())
        p = write_brief(self.project, issue_id, data)
        return p.read_text(encoding="utf-8")

    def test_brief_101_created(self):
        text = self._brief("ISSUE-101")
        self.assertIn("ISSUE-101", text)

    def test_brief_101_has_symptom(self):
        text = self._brief("ISSUE-101")
        self.assertIn("Symptom", text)

    def test_brief_101_has_log_evidence(self):
        text = self._brief("ISSUE-101")
        self.assertIn("Log Evidence", text)

    def test_brief_101_has_policy_section(self):
        text = self._brief("ISSUE-101")
        self.assertIn("Policy", text)

    def test_brief_101_suspect_code_pricing(self):
        """ISSUE-101 brief must include a snippet from pricing.py."""
        text = self._brief("ISSUE-101")
        self.assertIn("pricing.py", text)

    def test_brief_101_definition_of_done(self):
        text = self._brief("ISSUE-101")
        self.assertIn("Definition of Done", text)
        self.assertIn("test_issue_101_", text)

    def test_brief_102_shows_duplicate_104(self):
        text = self._brief("ISSUE-102")
        self.assertIn("ISSUE-104", text)

    def test_brief_102_has_call_chain(self):
        text = self._brief("ISSUE-102")
        self.assertIn("Call Chain", text)

    def test_brief_103_has_call_chain(self):
        text = self._brief("ISSUE-103")
        self.assertIn("Call Chain", text)
        self.assertIn("shipping.py", text)


class TestLog(unittest.TestCase):
    """log command records a stage in the timeline."""

    def setUp(self):
        self.project = _make_temp_project()

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def test_log_reproduce(self):
        from bugflow.log_cmd import run_log
        from bugflow import state
        run_log(self.project, "ISSUE-101", "reproduce")
        events = state.read_timeline(self.project)
        stages = [e for e in events if e.get("stage") == "reproduce"]
        self.assertEqual(len(stages), 1)

    def test_log_fix(self):
        from bugflow.log_cmd import run_log
        from bugflow import state
        run_log(self.project, "ISSUE-101", "fix")
        events = state.read_timeline(self.project)
        stages = [e for e in events if e.get("stage") == "fix"]
        self.assertEqual(len(stages), 1)


class TestVerify(unittest.TestCase):
    """verify gate: BLOCKED when regression tests are missing."""

    def setUp(self):
        self.project = _make_temp_project()
        if str(self.project) not in sys.path:
            sys.path.insert(0, str(self.project))
        from bugflow.triage import run_triage
        run_triage(self.project, print_json=False)

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def test_gate_blocked_without_regression_tests(self):
        """Without any regression tests the gate is BLOCKED."""
        from bugflow.verify import run_verify
        # Remove any existing regression tests so the gate sees a clean slate
        for tf in (self.project / "tests").glob("test_*.py"):
            tf.unlink()
        passed = run_verify(self.project)
        self.assertFalse(passed, "Gate should be BLOCKED without regression tests")

    def test_gate_blocked_specific_issue(self):
        from bugflow.verify import run_verify
        # Remove any existing regression tests so the gate sees a clean slate
        for tf in (self.project / "tests").glob("test_*.py"):
            tf.unlink()
        passed = run_verify(self.project, issue_id="ISSUE-101")
        self.assertFalse(passed)

    def test_gate_passed_after_regression_added(self):
        """Gate passes once a proper regression test is added."""
        from bugflow.verify import run_verify
        # Write a minimal regression test
        test_file = self.project / "tests" / "test_regression_101.py"
        test_file.write_text(
            'import unittest\n\n'
            'class TestRegression101(unittest.TestCase):\n'
            '    def test_issue_101_pricing_regression(self):\n'
            '        """Regression test. ISSUE-101"""\n'
            '        self.assertTrue(True)\n',
            encoding="utf-8",
        )
        passed = run_verify(self.project, issue_id="ISSUE-101")
        # Should pass now for ISSUE-101 in isolation
        self.assertTrue(passed)


class TestPR(unittest.TestCase):
    """pr command writes a markdown file."""

    def setUp(self):
        self.project = _make_temp_project()
        if str(self.project) not in sys.path:
            sys.path.insert(0, str(self.project))
        from bugflow.triage import run_triage
        run_triage(self.project, print_json=False)

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def test_pr_written(self):
        from bugflow.pr import run_pr
        run_pr(self.project, "ISSUE-103",
               root_cause="Region string not normalised to lowercase before dict lookup.",
               fix="Add region.lower() before REGION_TRANSIT_DAYS lookup.")
        out = self.project / ".bugflow" / "pr" / "ISSUE-103.md"
        self.assertTrue(out.exists())
        content = out.read_text()
        self.assertIn("ISSUE-103", content)
        self.assertIn("Root Cause", content)
        self.assertIn("Suggested Reviewer", content)

    def test_pr_closes_duplicates(self):
        from bugflow.pr import run_pr
        run_pr(self.project, "ISSUE-102",
               root_cause="Off-by-one in reservation check.",
               fix="Use >= instead of >.")
        out = (self.project / ".bugflow" / "pr" / "ISSUE-102.md").read_text()
        self.assertIn("ISSUE-104", out)


class TestReport(unittest.TestCase):
    """report command writes report.md and report.html."""

    def setUp(self):
        self.project = _make_temp_project()
        if str(self.project) not in sys.path:
            sys.path.insert(0, str(self.project))
        from bugflow import state
        state.append_timeline(self.project, {"type": "start", "mode": "agent"})
        from bugflow.triage import run_triage
        run_triage(self.project, print_json=False)

    def tearDown(self):
        shutil.rmtree(self.project.parent, ignore_errors=True)

    def test_report_md_written(self):
        from bugflow.report import run_report
        run_report(self.project)
        md = self.project / ".bugflow" / "report.md"
        self.assertTrue(md.exists())
        content = md.read_text()
        self.assertIn("Unique bugs", content)
        self.assertIn("Duplicates resolved", content)

    def test_report_html_written(self):
        from bugflow.report import run_report
        run_report(self.project)
        html = self.project / ".bugflow" / "report.html"
        self.assertTrue(html.exists())
        self.assertIn("BugFlow", html.read_text())

    def test_report_scripted_no_speedup(self):
        from bugflow import state
        from bugflow.report import run_report
        # Reset and start in scripted mode
        tl = state.timeline_path(self.project)
        if tl.exists():
            tl.unlink()
        state.append_timeline(self.project, {"type": "start", "mode": "scripted"})
        run_report(self.project)
        md = (self.project / ".bugflow" / "report.md").read_text()
        self.assertIn("scripted", md)
        self.assertNotIn("×", md)


if __name__ == "__main__":
    unittest.main()
