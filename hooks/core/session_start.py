"""SessionStart compact context injector (capped at <=30 lines / ~400 tokens)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .policy import AGENT_HOOKS_DATA_DIR

MAX_LINES = 30
MAX_CHARS = 1600
MAX_STATUS_LINES = 10
MAX_SNAPSHOT_AGE_SECS = 7 * 24 * 3600


def _data_dir() -> Path:
    override = os.environ.get("AGENT_HOOKS_DATA_DIR")
    return Path(override) if override else AGENT_HOOKS_DATA_DIR


def _run_git(cwd: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.rstrip("\r\n")
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _compact_file_excerpt(path: Path, max_lines: int) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    non_empty = [ln.rstrip() for ln in raw if ln.strip() and not ln.strip().startswith("<!--")]
    excerpt = non_empty[:max_lines]
    if len(non_empty) > max_lines:
        excerpt.append(f"... (+{len(non_empty) - max_lines} more lines in {path.name})")
    return excerpt


def handle(event: dict[str, Any]) -> dict[str, Any]:
    cwd_str = str(event.get("cwd") or "")
    if not cwd_str:
        return {}
    cwd = Path(cwd_str)
    if not cwd.is_dir():
        return {}

    lines: list[str] = []
    repo_root_str = _run_git(cwd, "rev-parse", "--show-toplevel")
    repo_root = Path(repo_root_str) if repo_root_str else cwd

    if repo_root_str:
        branch = _run_git(repo_root, "branch", "--show-current") or "detached"
        status_raw = _run_git(repo_root, "status", "--short") or ""
        status_lines = [ln for ln in status_raw.splitlines() if ln.strip()]
        lines.append(f"[Session Context] Repo: {repo_root.name} | Branch: {branch} | Dirty files: {len(status_lines)}")
        if status_lines:
            lines.extend(f"  {ln}" for ln in status_lines[:MAX_STATUS_LINES])
            if len(status_lines) > MAX_STATUS_LINES:
                lines.append(f"  ... (+{len(status_lines) - MAX_STATUS_LINES} more)")

    handoff_file = repo_root / "HANDOFF.md"
    progress_file = repo_root / "PROGRESS.md"

    if handoff_file.is_file():
        lines.append("[HANDOFF.md excerpt]")
        lines.extend(_compact_file_excerpt(handoff_file, 10))
    elif repo_root_str:
        repo_hash = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:12]
        snap = _data_dir() / "handoffs" / f"{repo_hash}.md"
        if snap.is_file() and (time.time() - snap.stat().st_mtime) < MAX_SNAPSHOT_AGE_SECS:
            lines.append(f"[Recent auto-handoff snapshot: {snap}]")
            lines.extend(_compact_file_excerpt(snap, 6))

    if progress_file.is_file():
        lines.append("[PROGRESS.md present]")
        lines.extend(_compact_file_excerpt(progress_file, 4))

    if not lines:
        return {}

    bounded = "\n".join(lines[:MAX_LINES])
    if len(bounded) > MAX_CHARS:
        bounded = bounded[: MAX_CHARS - 20].rstrip() + "\n... [truncated]"

    return {"system_message": bounded}
