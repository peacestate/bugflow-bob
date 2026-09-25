"""Shared helpers: .bugflow/ directory, timeline, and timing."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def bugflow_dir(project: Path) -> Path:
    return project / ".bugflow"


def ensure_dir(project: Path) -> Path:
    d = bugflow_dir(project)
    d.mkdir(parents=True, exist_ok=True)
    return d


def timeline_path(project: Path) -> Path:
    return bugflow_dir(project) / "timeline.jsonl"


def append_timeline(project: Path, event: dict) -> None:
    ensure_dir(project)
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with timeline_path(project).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def read_timeline(project: Path) -> list[dict]:
    p = timeline_path(project)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def triage_json_path(project: Path) -> Path:
    return bugflow_dir(project) / "triage.json"


def triage_md_path(project: Path) -> Path:
    return bugflow_dir(project) / "triage.md"


def briefs_dir(project: Path) -> Path:
    p = bugflow_dir(project) / "briefs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pr_dir(project: Path) -> Path:
    p = bugflow_dir(project) / "pr"
    p.mkdir(parents=True, exist_ok=True)
    return p


def record_stage(project: Path, issue: str, stage: str) -> None:
    append_timeline(project, {"type": "stage", "issue": issue, "stage": stage})


def session_mode(project: Path) -> str:
    """Return the session mode ('agent' or 'scripted'); default 'agent'."""
    for ev in read_timeline(project):
        if ev.get("type") == "start":
            return ev.get("mode", "agent")
    return "agent"
