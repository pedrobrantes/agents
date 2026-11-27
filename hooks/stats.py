#!/usr/bin/env python3
"""Summarize local agent hook audit logs and estimated token usage.

Usage:
    python3 ~/.agents/hooks/stats.py [--days 7]
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.policy import AGENT_HOOKS_DATA_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize agent-hooks audit telemetry")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    args = parser.parse_args(argv)

    base = Path(os.environ.get("AGENT_HOOKS_DATA_DIR") or AGENT_HOOKS_DATA_DIR)
    if not base.is_dir():
        print(f"No telemetry directory found at {base}")
        return 0

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=max(1, args.days) - 1)
    total_calls = 0
    total_errors = 0
    total_tokens = 0
    by_tool: Counter[str] = Counter()
    tokens_by_tool: Counter[str] = Counter()
    by_cwd: Counter[str] = Counter()

    for path in sorted(base.glob("audit-*.jsonl")):
        date_part = path.stem.removeprefix("audit-")
        try:
            file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            total_calls += 1
            if not rec.get("ok", True):
                total_errors += 1
            est = int(rec.get("est_input_tokens") or 0)
            total_tokens += est
            tool = str(rec.get("tool") or "unknown")
            by_tool[tool] += 1
            tokens_by_tool[tool] += est
            cwd = str(rec.get("cwd") or "unknown")
            by_cwd[Path(cwd).name or cwd] += 1

    print(f"Agent Hooks Telemetry (last {args.days} days)")
    print(f"  Total tool calls : {total_calls} (errors: {total_errors})")
    print(f"  Est. args tokens : ~{total_tokens}")
    if by_tool:
        print("\nTop tools:")
        for tool, count in by_tool.most_common(10):
            print(f"  {tool:24s} calls={count:4d}  est_tokens~{tokens_by_tool[tool]}")
    if by_cwd:
        print("\nTop workspaces:")
        for ws, count in by_cwd.most_common(10):
            print(f"  {ws:24s} calls={count:4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
