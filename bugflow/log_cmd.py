"""log command — record a stage for an issue."""

from __future__ import annotations

import sys
from pathlib import Path

from bugflow import state


def run_log(project: Path, issue: str, stage: str) -> None:
    valid_stages = {"reproduce", "fix"}
    if stage not in valid_stages:
        print(f"Unknown stage '{stage}'. Valid: {', '.join(sorted(valid_stages))}", file=sys.stderr)
        sys.exit(1)
    state.record_stage(project, issue, stage)
    print(f"Stage '{stage}' recorded for {issue}.")
