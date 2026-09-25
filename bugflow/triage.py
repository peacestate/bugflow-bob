"""triage command — parse issues + logs, deduplicate, rank, write triage.md / triage.json."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from bugflow import state

# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}


def _sev_rank(s: str) -> int:
    return SEVERITY_RANK.get(s.lower(), 0)


def _higher_sev(a: str, b: str) -> str:
    return a if _sev_rank(a) >= _sev_rank(b) else b


# ---------------------------------------------------------------------------
# Issue parsing
# ---------------------------------------------------------------------------
_SEVERITY_RE = re.compile(r"\*\*Severity:\*\*\s*(\w+)", re.IGNORECASE)
_COMPONENT_RE = re.compile(r"\*\*Component:\*\*\s*(\S+)", re.IGNORECASE)
_CREATED_RE = re.compile(r"\*\*Created:\*\*\s*(\S+)", re.IGNORECASE)
_REPORTER_RE = re.compile(r"\*\*Reporter:\*\*\s*(\S+)", re.IGNORECASE)
_REQUEST_ID_RE = re.compile(r"request_id=(\S+)")
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def parse_issue(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    issue_id = path.stem  # e.g. "ISSUE-101"

    title_m = _TITLE_RE.search(text)
    title = title_m.group(1).strip() if title_m else issue_id

    sev_m = _SEVERITY_RE.search(text)
    severity = sev_m.group(1).lower() if sev_m else "unknown"

    comp_m = _COMPONENT_RE.search(text)
    component = comp_m.group(1).lower() if comp_m else "unknown"

    created_m = _CREATED_RE.search(text)
    created = created_m.group(1) if created_m else ""

    reporter_m = _REPORTER_RE.search(text)
    reporter = reporter_m.group(1) if reporter_m else ""

    request_ids = _REQUEST_ID_RE.findall(text)

    return {
        "id": issue_id,
        "title": title,
        "severity": severity,
        "component": component,
        "created": created,
        "reporter": reporter,
        "request_ids": request_ids,
        "raw": text,
    }


def load_issues(project: Path) -> list[dict]:
    issues_dir = project / "issues"
    if not issues_dir.is_dir():
        return []
    issues = []
    for p in sorted(issues_dir.glob("ISSUE-*.md")):
        issues.append(parse_issue(p))
    return issues


# ---------------------------------------------------------------------------
# Log parsing (NDJSON + multi-line Python tracebacks)
# ---------------------------------------------------------------------------

def _resolve_traceback_path(raw_path: str, project: Path) -> Optional[str]:
    """Resolve an absolute path from any machine to the local project by
    matching the longest existing suffix within the project root."""
    # Normalise separators; then resolve '..' segments by treating it as a
    # pure POSIX string (we can't call .resolve() because the machine root
    # may not exist on the current host).
    normalised = raw_path.replace("\\", "/")
    # Collapse 'dir/..' pairs iteratively
    parts_raw = normalised.split("/")
    parts_clean: list[str] = []
    for part in parts_raw:
        if part == "..":
            if parts_clean and parts_clean[-1] not in ("", ".."):
                parts_clean.pop()
        elif part != ".":
            parts_clean.append(part)
    parts = tuple(p for p in parts_clean if p)
    # Walk from innermost (rightmost) to outermost: try suffixes of length
    # 1, 2, 3, … stopping at the first existing candidate that is actually a
    # *file* (not the project root itself).
    for length in range(1, len(parts) + 1):
        suffix = parts[len(parts) - length:]
        candidate = project.joinpath(*suffix)
        if candidate.is_file():
            return str(candidate.relative_to(project)).replace("\\", "/")
    return None


_FRAME_RE = re.compile(
    r'File "([^"]+)", line (\d+), in (\S+)'
)


def _parse_traceback(tb_text: str, project: Path) -> Optional[dict]:
    """Extract the innermost frame that lives inside the project source dirs."""
    frames = _FRAME_RE.findall(tb_text)
    # frames: list of (filepath, lineno, func)
    # Work from innermost (last) frame outward looking for a project file.
    for filepath, lineno, func in reversed(frames):
        resolved = _resolve_traceback_path(filepath, project)
        if resolved:
            # Only count files under shopcart/ (source dirs, not tests/scripts)
            if resolved.startswith("shopcart") or resolved.startswith("src"):
                # Extract exception type from last line
                exc_type = None
                for line in reversed(tb_text.splitlines()):
                    m = re.match(r'^(\S+(?:\.\S+)*(?:Error|Exception|Stop\S*|KeyError|OutOfStock\S*)):', line)
                    if m:
                        exc_type = m.group(1)
                        break
                    # Also bare word exceptions
                    m2 = re.match(r'^(\w[\w.]+): ', line)
                    if m2:
                        exc_type = m2.group(1)
                        break
                return {
                    "exc_type": exc_type or "UnknownException",
                    "file": resolved,
                    "lineno": int(lineno),
                    "func": func,
                }
    return None


def _crash_signature(exc_type: str, file: str, lineno: int) -> str:
    return f"{exc_type}@{file}:{lineno}"


def parse_log_events(project: Path) -> list[dict]:
    """Parse all .log / .ndjson files; return list of events."""
    logs_dir = project / "logs"
    if not logs_dir.is_dir():
        return []
    events = []
    for log_path in sorted(logs_dir.iterdir()):
        if log_path.suffix not in (".log", ".ndjson", ".jsonl"):
            continue
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            msg = entry.get("msg", "")
            tb_text = entry.get("exc", "")

            # Extract request_id from msg
            rid_m = _REQUEST_ID_RE.search(msg)
            request_id = rid_m.group(1) if rid_m else None

            tb_info = None
            if tb_text:
                tb_info = _parse_traceback(tb_text, project)

            events.append({
                "ts": entry.get("ts", ""),
                "level": entry.get("level", "INFO"),
                "request_id": request_id,
                "msg": msg,
                "traceback": tb_text,
                "tb_info": tb_info,
            })
    return events


# ---------------------------------------------------------------------------
# CODEOWNERS  (last-match wins, like GitHub)
# ---------------------------------------------------------------------------

def _parse_codeowners(project: Path) -> list[tuple[str, list[str]]]:
    co = project / "CODEOWNERS"
    if not co.exists():
        return []
    rules = []
    for line in co.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rules.append((parts[0], parts[1:]))
    return rules


def owner_for_file(rel_path: str, codeowners: list[tuple[str, list[str]]]) -> Optional[str]:
    """Return the last matching owner(s) as a string."""
    matched = None
    # Normalise to forward slashes and remove leading /
    rel_path_norm = "/" + rel_path.replace("\\", "/").lstrip("/")
    for pattern, owners in codeowners:
        pat = pattern.rstrip("/")
        # GitHub CODEOWNERS: match if the path ends with the pattern-suffix
        # or if the pattern (with leading /) is a prefix of the path.
        if rel_path_norm == pat:
            matched = " ".join(owners)
        elif rel_path_norm.startswith(pat + "/"):
            matched = " ".join(owners)
        elif rel_path_norm.endswith(pat) or rel_path_norm.endswith(pat.lstrip("/")):
            matched = " ".join(owners)
        # Simple glob: pattern ends with wildcard
        elif pat.endswith("/*"):
            prefix = pat[:-2]
            if rel_path_norm.startswith(prefix + "/") and "/" not in rel_path_norm[len(prefix)+1:]:
                matched = " ".join(owners)
    return matched


# ---------------------------------------------------------------------------
# Keyword overlap for wrong-result bugs (no traceback)
# ---------------------------------------------------------------------------

def _keywords(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\w+", text) if len(w) > 3}


def best_policy_section(issue: dict, project: Path) -> Optional[dict]:
    """Find the policy doc section that best matches the issue by keyword overlap."""
    docs_dir = project / "docs"
    if not docs_dir.is_dir():
        return None
    issue_kw = _keywords(issue["raw"])
    best = None
    best_score = 0
    for doc_path in sorted(docs_dir.glob("*.md")):
        doc_text = doc_path.read_text(encoding="utf-8")
        # Split into sections on "##" headings
        sections = re.split(r"(?=^## )", doc_text, flags=re.MULTILINE)
        for section in sections:
            if not section.strip():
                continue
            kw = _keywords(section)
            score = len(issue_kw & kw)
            if score > best_score:
                best_score = score
                heading_m = re.match(r"^## (.+)", section.strip())
                heading = heading_m.group(1).strip() if heading_m else "(intro)"
                best = {
                    "doc": doc_path.name,
                    "section": heading,
                    "text": section.strip(),
                    "score": score,
                }
    return best


# Lines that are structural or non-executable and should be skipped when
# looking for the buggy statement.
_SKIP_LINE_RE = re.compile(
    r"""^\s*(
        \#          |   # comment
        \"\"\"      |   # triple-quote open/close
        \'\'\'      |   # triple-quote open/close
        def\s       |   # function definition
        class\s     |   # class definition
        import\s    |   # bare import
        from\s.*\simport  # from … import
    )""",
    re.VERBOSE,
)


def _is_scoreable_line(line: str) -> bool:
    """Return True if *line* is executable application code (not a comment,
    docstring delimiter, def/class header, or import statement)."""
    stripped = line.strip()
    if not stripped:
        return False
    return not _SKIP_LINE_RE.match(line)


def _suspect_from_policy(policy_section: dict, project: Path) -> Optional[dict]:
    """Find the best real-code line matching the policy vocabulary.

    Uses the vocabulary of the *entire policy document* so that technical
    terms (e.g. 'rounding', 'decimal', 'float', 'half') appear across
    sections and accumulate a strong signal.

    Scoring per candidate line (comments/docstrings/def/imports excluded):
        score = line_hits * 10 + func_hits
    where line_hits = keyword matches on that line alone, and
    func_hits = total keyword matches in the enclosing function body.
    This prefers a line inside a function that broadly matches the policy.
    """
    if policy_section is None:
        return None
    # Use the whole doc for vocabulary, not just the matched section
    doc_path = project / "docs" / policy_section["doc"]
    full_doc_text = doc_path.read_text(encoding="utf-8") if doc_path.exists() else policy_section["text"]
    kw = _keywords(full_doc_text)
    best = None
    best_score = -1

    def _func_range(lines: list[str], idx: int) -> tuple[int, int]:
        """Return (start, end) indices (0-based, exclusive end) of the
        function that contains line index *idx*."""
        func_start = 0
        for i in range(idx, -1, -1):
            if re.match(r"^(    |\t)?def |^def ", lines[i]):
                func_start = i
                break
        func_end = len(lines)
        for i in range(func_start + 1, len(lines)):
            if re.match(r"^(def |class )", lines[i]):
                func_end = i
                break
        return func_start, func_end

    src_dirs = [project / "shopcart", project / "src"]
    for src_dir in src_dirs:
        if not src_dir.is_dir():
            continue
        for py_file in sorted(src_dir.rglob("*.py")):
            rel = str(py_file.relative_to(project)).replace("\\", "/")
            lines = py_file.read_text(encoding="utf-8").splitlines()
            in_docstring = False
            for i, line in enumerate(lines, 1):
                # Track triple-quoted docstring blocks so we can skip them
                stripped = line.strip()
                triple = stripped.count('"""') + stripped.count("'''")
                if triple:
                    # Toggle docstring state on odd count of triple-quotes
                    if triple % 2 == 1:
                        in_docstring = not in_docstring
                    # Either way, this line is part of a docstring boundary — skip
                    continue
                if in_docstring:
                    continue
                if not _is_scoreable_line(line):
                    continue
                line_hits = len(kw & _keywords(line))
                if line_hits == 0:
                    continue
                # Boost by keyword hits across the enclosing function body
                fs, fe = _func_range(lines, i - 1)
                func_text = "\n".join(lines[fs:fe])
                func_hits = len(kw & _keywords(func_text))
                score = line_hits * 10 + func_hits
                if score > best_score:
                    best_score = score
                    best = {
                        "file": rel,
                        "lineno": i,
                        "line": line.strip(),
                    }
    return best


# ---------------------------------------------------------------------------
# Core triage logic
# ---------------------------------------------------------------------------

def run_triage(project: Path, print_json: bool = False) -> list[dict]:
    issues = load_issues(project)
    if not issues:
        print("No issues found in issues/", file=sys.stderr)
        return []

    log_events = parse_log_events(project)
    codeowners = _parse_codeowners(project)

    # Build a lookup: request_id -> log event
    events_by_rid: dict[str, list[dict]] = defaultdict(list)
    for ev in log_events:
        if ev["request_id"]:
            events_by_rid[ev["request_id"]].append(ev)

    # Annotate issues with log data
    bug_records: list[dict] = []
    for issue in issues:
        # Linked log events
        linked = []
        for rid in issue["request_ids"]:
            linked.extend(events_by_rid.get(rid, []))

        # Find traceback info
        tb_info = None
        for ev in linked:
            if ev["tb_info"]:
                tb_info = ev["tb_info"]
                break

        # Crash signature
        signature = None
        if tb_info:
            signature = _crash_signature(
                tb_info["exc_type"], tb_info["file"], tb_info["lineno"]
            )

        # Policy / suspect for wrong-result (no traceback)
        policy_section = None
        suspect = None
        if not tb_info:
            policy_section = best_policy_section(issue, project)
            suspect = _suspect_from_policy(policy_section, project)

        # Owner: use tb_info file or component-derived guess
        owner = None
        if tb_info:
            # Try exact match first, then strip leading 'sample-app/'
            owner = owner_for_file(tb_info["file"], codeowners)
            if owner is None:
                # Try with project name prefix
                owner = owner_for_file(
                    f"sample-app/{tb_info['file']}", codeowners
                )
        if owner is None and suspect:
            owner = owner_for_file(suspect["file"], codeowners)
            if owner is None:
                owner = owner_for_file(f"sample-app/{suspect['file']}", codeowners)

        bug_records.append({
            "id": issue["id"],
            "title": issue["title"],
            "severity": issue["severity"],
            "component": issue["component"],
            "created": issue["created"],
            "reporter": issue["reporter"],
            "request_ids": issue["request_ids"],
            "linked_events": linked,
            "tb_info": tb_info,
            "signature": signature,
            "policy_section": policy_section,
            "suspect": suspect,
            "owner": owner,
            "canonical": True,
            "duplicate_of": None,
            "duplicates": [],
        })

    # Deduplicate by signature (earliest is canonical)
    sig_to_canonical: dict[str, str] = {}
    for rec in bug_records:
        sig = rec["signature"]
        if sig is None:
            continue
        if sig not in sig_to_canonical:
            sig_to_canonical[sig] = rec["id"]
        else:
            # This is a duplicate
            canonical_id = sig_to_canonical[sig]
            rec["canonical"] = False
            rec["duplicate_of"] = canonical_id
            # Mark the canonical
            for c in bug_records:
                if c["id"] == canonical_id:
                    c["duplicates"].append(rec["id"])
                    # Raise severity to highest
                    c["severity"] = _higher_sev(c["severity"], rec["severity"])
                    break

    # Rank: canonical bugs by severity desc, then created asc
    ranked = [r for r in bug_records if r["canonical"]]
    ranked.sort(key=lambda r: (-_sev_rank(r["severity"]), r["created"]))

    # Build work-queue output
    work_queue = []
    for r in ranked:
        entry: dict = {
            "id": r["id"],
            "title": r["title"],
            "severity": r["severity"],
            "component": r["component"],
            "owner": r["owner"] or "unassigned",
            "signature": r["signature"],
            "suspect_file": None,
            "suspect_line": None,
            "duplicates": r["duplicates"],
        }
        if r["tb_info"]:
            entry["suspect_file"] = r["tb_info"]["file"]
            entry["suspect_line"] = r["tb_info"]["lineno"]
        elif r["suspect"]:
            entry["suspect_file"] = r["suspect"]["file"]
            entry["suspect_line"] = r["suspect"]["lineno"]
        work_queue.append(entry)

    # Build full output (work_queue + all issue detail)
    output = {
        "work_queue": work_queue,
        "all_issues": bug_records,
    }

    # Write files
    _write_triage_json(project, output)
    _write_triage_md(project, work_queue, bug_records)

    state.record_stage(project, "all", "triage")

    if print_json:
        print(json.dumps(work_queue, indent=2))
    else:
        text = _triage_table_text(work_queue, bug_records)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()

    return work_queue


def _triage_table_text(work_queue: list[dict], all_issues: list[dict]) -> str:
    lines = []
    lines.append("## BugFlow Triage — Work Queue\n")
    lines.append(
        f"{'ID':<12} {'Severity':<10} {'Component':<12} {'Owner':<30} {'Duplicates':<15} Title"
    )
    lines.append("-" * 110)
    for entry in work_queue:
        dups = ",".join(entry["duplicates"]) or "—"
        lines.append(
            f"{entry['id']:<12} {entry['severity']:<10} {entry['component']:<12} "
            f"{(entry['owner'] or 'unassigned'):<30} {dups:<15} {entry['title']}"
        )
    lines.append("")

    # Show duplicates section
    dup_issues = [i for i in all_issues if not i["canonical"]]
    if dup_issues:
        lines.append("### Duplicates resolved")
        for d in dup_issues:
            lines.append(f"  {d['id']} -> duplicate of {d['duplicate_of']} (same signature: {d['signature']})")
        lines.append("")

    return "\n".join(lines)


def _write_triage_json(project: Path, output: dict) -> None:
    state.ensure_dir(project)
    path = state.triage_json_path(project)
    path.write_text(
        json.dumps(output, indent=2, default=str), encoding="utf-8"
    )


def _write_triage_md(project: Path, work_queue: list[dict], all_issues: list[dict]) -> None:
    state.ensure_dir(project)
    path = state.triage_md_path(project)
    lines = ["# BugFlow Triage Report\n"]
    lines.append(
        "| ID | Severity | Component | Owner | Duplicates | Suspect File | Suspect Line | Title |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|"
    )
    for entry in work_queue:
        dups = ", ".join(entry["duplicates"]) or "—"
        sf = entry["suspect_file"] or "—"
        sl = str(entry["suspect_line"]) if entry["suspect_line"] else "—"
        owner = entry["owner"] or "unassigned"
        lines.append(
            f"| {entry['id']} | {entry['severity']} | {entry['component']} | `{owner}` "
            f"| {dups} | `{sf}` | {sl} | {entry['title']} |"
        )
    lines.append("")

    dup_issues = [i for i in all_issues if not i["canonical"]]
    if dup_issues:
        lines.append("## Duplicates")
        for d in dup_issues:
            lines.append(f"- **{d['id']}** -- duplicate of **{d['duplicate_of']}** "
                         f"(signature: `{d['signature']}`)")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
