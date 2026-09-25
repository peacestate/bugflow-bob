"""brief command — one markdown brief per unique bug."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bugflow import state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_triage(project: Path) -> dict:
    p = state.triage_json_path(project)
    if not p.exists():
        print("Run 'triage' first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def _issue_text(project: Path, issue_id: str) -> str:
    p = project / "issues" / f"{issue_id}.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def _source_snippet(project: Path, rel_file: str, lineno: int) -> str:
    """Return the whole enclosing function around lineno, with the target line marked."""
    src = project / rel_file
    if not src.exists():
        return f"(file not found: {rel_file})"
    lines = src.read_text(encoding="utf-8").splitlines()
    if lineno < 1 or lineno > len(lines):
        return f"(line {lineno} out of range in {rel_file})"

    # Find enclosing function: scan upward for 'def '
    start = lineno - 1  # 0-based
    func_start = 0
    for i in range(start, -1, -1):
        if re.match(r'^(    |\t)?def ', lines[i]) or re.match(r'^def ', lines[i]):
            func_start = i
            break

    # Find end of function: next non-indented def / class or EOF
    func_end = len(lines)
    for i in range(func_start + 1, len(lines)):
        if re.match(r'^(def |class )', lines[i]):
            func_end = i
            break

    # Build snippet with marker
    snippet_lines = []
    for i in range(func_start, func_end):
        prefix = ">>>" if (i + 1) == lineno else "   "
        snippet_lines.append(f"{prefix} {i+1:4d} | {lines[i]}")

    return "\n".join(snippet_lines)


def _related_tests(project: Path, component: str, issue_id: str) -> list[str]:
    """Return existing test file paths relevant to component."""
    tests_dir = project / "tests"
    found = []
    if tests_dir.is_dir():
        for tf in sorted(tests_dir.glob("*.py")):
            if component.lower() in tf.name.lower():
                found.append(str(tf.relative_to(project)))
    return found


def _policy_sections(project: Path, component: str, issue_text: str) -> list[dict]:
    """Return policy doc sections relevant to the component."""
    docs_dir = project / "docs"
    if not docs_dir.is_dir():
        return []

    comp_keywords = set(component.lower().split("-"))
    # Also grab keywords from issue title
    words = {w.lower() for w in re.findall(r"\w+", issue_text) if len(w) > 3}

    results = []
    for doc_path in sorted(docs_dir.glob("*.md")):
        doc_text = doc_path.read_text(encoding="utf-8")
        sections = re.split(r"(?=^## )", doc_text, flags=re.MULTILINE)
        doc_kw = {w.lower() for w in re.findall(r"\w+", doc_path.stem) if len(w) > 2}
        # Include if doc name overlaps with component
        if not (comp_keywords & doc_kw or doc_path.stem.lower().startswith(component.lower())):
            # Also include if issue keywords heavily overlap
            doc_all_kw = {w.lower() for w in re.findall(r"\w+", doc_text) if len(w) > 3}
            if len(words & doc_all_kw) < 5:
                continue
        for section in sections:
            if not section.strip():
                continue
            heading_m = re.match(r"^## (.+)", section.strip())
            heading = heading_m.group(1).strip() if heading_m else "(intro)"
            results.append({"doc": doc_path.name, "section": heading, "text": section.strip()})
    return results


def _call_chain(tb_text: str) -> str:
    """Extract a readable call chain from a traceback string."""
    if not tb_text:
        return "(no traceback available)"
    lines = tb_text.splitlines()
    chain = []
    frame_re = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
    for i, line in enumerate(lines):
        m = frame_re.search(line)
        if m:
            filepath = m.group(1)
            # Shorten path
            short = re.sub(r'.+[\\/]', '', filepath)
            lineno = m.group(2)
            func = m.group(3)
            # Grab the code line if present
            code = lines[i + 1].strip() if i + 1 < len(lines) else ""
            chain.append(f"  {short}:{lineno} in `{func}()` — `{code}`")
    return "\n".join(chain) if chain else "(no frames found)"


def _log_evidence(issue_record: dict) -> str:
    events = issue_record.get("linked_events", [])
    if not events:
        return "(no log events linked)"
    lines = []
    for ev in events:
        line = f"[{ev['ts']}] {ev['level']} — {ev['msg']}"
        if ev.get("traceback"):
            # Indent traceback
            tb_lines = ev["traceback"].replace("\\n", "\n").splitlines()
            for tl in tb_lines:
                line += f"\n    {tl}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write brief
# ---------------------------------------------------------------------------

def write_brief(project: Path, issue_id: str, triage_data: dict) -> Path:
    all_issues = {i["id"]: i for i in triage_data["all_issues"]}
    rec = all_issues.get(issue_id)
    if rec is None:
        print(f"Issue {issue_id} not found in triage data.", file=sys.stderr)
        sys.exit(1)

    # Resolve canonical if this is a dup
    if not rec["canonical"] and rec["duplicate_of"]:
        canonical_id = rec["duplicate_of"]
        canonical_rec = all_issues.get(canonical_id, rec)
    else:
        canonical_id = issue_id
        canonical_rec = rec

    # Gather duplicates
    dup_ids = canonical_rec.get("duplicates", [])
    dup_records = [all_issues[d] for d in dup_ids if d in all_issues]

    issue_text = _issue_text(project, canonical_id)
    component = canonical_rec.get("component", "")

    # Suspect info
    suspect_file = None
    suspect_line = None
    tb_text = ""
    if canonical_rec.get("tb_info"):
        tbi = canonical_rec["tb_info"]
        suspect_file = tbi["file"]
        suspect_line = tbi["lineno"]
        # Pull tb_text from linked events
        for ev in canonical_rec.get("linked_events", []):
            if ev.get("traceback"):
                tb_text = ev["traceback"].replace("\\n", "\n")
                break
    elif canonical_rec.get("suspect"):
        sus = canonical_rec["suspect"]
        suspect_file = sus["file"]
        suspect_line = sus["lineno"]

    snippet = ""
    if suspect_file and suspect_line:
        snippet = _source_snippet(project, suspect_file, suspect_line)

    call_chain = _call_chain(tb_text)
    log_ev = _log_evidence(canonical_rec)
    policy = _policy_sections(project, component, issue_text)
    tests = _related_tests(project, component, canonical_id)

    # Regression test name
    # Extract number from issue id (e.g. "101" from "ISSUE-101")
    num_m = re.search(r"(\d+)$", canonical_id)
    num = num_m.group(1) if num_m else canonical_id
    regression_test_name = f"test_issue_{num}_{component}_regression"
    regression_docstring = f"Regression test for {canonical_id}: {canonical_rec['title'][:60]}."

    # Build markdown
    md_lines = [
        f"# Bug Brief: {canonical_id}",
        "",
        f"**Severity:** {canonical_rec['severity']}  ",
        f"**Component:** {component}  ",
        f"**Owner:** {canonical_rec.get('owner') or 'unassigned'}  ",
        f"**Created:** {canonical_rec.get('created', '')}  ",
        "",
        "---",
        "",
        "## Symptom",
        "",
        issue_text if issue_text else f"See {canonical_id}.md",
        "",
    ]

    if dup_records:
        md_lines += [
            "## Duplicates",
            "",
        ]
        for d in dup_records:
            md_lines.append(f"- **{d['id']}** — {d['title']} (severity: {d['severity']})")
        md_lines.append("")

    md_lines += [
        "## Log Evidence",
        "",
        "```",
        log_ev,
        "```",
        "",
        "## Call Chain",
        "",
        call_chain,
        "",
        "## Suspect Code",
        "",
    ]

    if suspect_file:
        md_lines += [
            f"**File:** `{suspect_file}` **Line:** {suspect_line}",
            "",
            "```python",
            snippet,
            "```",
            "",
        ]
    else:
        md_lines += ["(no traceback; see policy-based suspect above)", ""]

    md_lines += ["## Relevant Policy Sections", ""]
    if policy:
        for sec in policy:
            md_lines += [
                f"### [{sec['doc']}] {sec['section']}",
                "",
                sec["text"],
                "",
            ]
    else:
        md_lines += ["(no matching policy docs found)", ""]

    md_lines += [
        "## Existing Tests",
        "",
    ]
    if tests:
        for t in tests:
            md_lines.append(f"- `{t}`")
    else:
        md_lines.append("(none)")
    md_lines.append("")

    # Definition of done
    md_lines += [
        "## Definition of Done",
        "",
        f"Add a regression test named **`{regression_test_name}`** in `tests/`.",
        f"Its docstring MUST contain `{canonical_id}`.",
        "",
        "Template:",
        "",
        "```python",
        f"def {regression_test_name}(self):",
        f'    """{regression_docstring}',
        f'',
        f'    {canonical_id}',
        f'    """',
        "    # TODO: implement",
        "    pass",
        "```",
        "",
        "The `bugflow verify` gate will run:",
        f"```",
        f"python -m unittest discover -k issue_{num}",
        f"```",
        "and require at least one test to pass.",
        "",
    ]

    out_path = state.briefs_dir(project) / f"{canonical_id}.md"
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    return out_path


def run_brief(project: Path, issue_ids: list[str]) -> None:
    triage_data = _load_triage(project)

    # Determine which issues to brief
    if not issue_ids:
        # All canonical issues
        issue_ids = [i["id"] for i in triage_data["all_issues"] if i["canonical"]]

    for issue_id in issue_ids:
        out_path = write_brief(project, issue_id, triage_data)
        state.record_stage(project, issue_id, "brief")
        print(f"Brief written: {out_path}")

    # If briefing a specific issue, print it
    if len(issue_ids) == 1:
        text = (state.briefs_dir(project) / f"{issue_ids[0]}.md").read_text(encoding="utf-8")
        # Write via sys.stdout.buffer to handle non-ASCII on Windows consoles
        sys.stdout.buffer.write(("\n" + text).encode("utf-8"))
        sys.stdout.buffer.flush()
