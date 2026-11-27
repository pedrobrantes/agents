"""Stop hook: desktop notification and clean deterministic auto-handoff snapshot.

Never blocks stopping (`decision: allow`).
- Sends `notify-send` only when meaningful work happened or an error occurred.
- Updates fenced `<!-- AUTO-STATE:START --> ... <!-- AUTO-STATE:END -->` block
  inside `HANDOFF.md` if present, otherwise stores snapshot in
  `~/.local/share/agent-hooks/handoffs/<repo-hash>.md` (never polluting git).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import has_session_activity
from .policy import AGENT_HOOKS_DATA_DIR

START_MARKER = "<!-- AUTO-STATE:START -->"
END_MARKER = "<!-- AUTO-STATE:END -->"
_MARKER_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)


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


def _build_snapshot(repo_root: Path, agent: str, termination_reason: str) -> tuple[str, int]:
    branch = _run_git(repo_root, "branch", "--show-current") or "detached"
    status = _run_git(repo_root, "status", "--short") or ""
    diff_stat = _run_git(repo_root, "diff", "--stat") or ""
    dirty_count = len([ln for ln in status.splitlines() if ln.strip()])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"- Updated: `{now}` by `{agent}` (`{termination_reason or 'NO_TOOL_CALL'}`)",
        f"- Repo: `{repo_root.name}` | Branch: `{branch}` | Dirty files: `{dirty_count}`",
    ]
    if status:
        status_preview = "\n".join(status.splitlines()[:20])
        lines.append("\n```text\n" + status_preview + "\n```")
    if diff_stat:
        stat_preview = "\n".join(diff_stat.splitlines()[:15])
        lines.append("\n```text\n" + stat_preview + "\n```")
    if dirty_count >= 5 or termination_reason in ("ERROR", "MAX_TOKEN_BUDGET_EXCEEDED"):
        lines.append("\nNote: Update `HANDOFF.md` / `PROGRESS.md` before switching agents.")

    return "\n".join(lines), dirty_count


def _write_auto_handoff(repo_root: Path, snapshot_body: str) -> None:
    handoff_path = repo_root / "HANDOFF.md"
    fenced = f"{START_MARKER}\n{snapshot_body}\n{END_MARKER}"

    if handoff_path.is_file():
        try:
            existing = handoff_path.read_text(encoding="utf-8", errors="replace")
            if START_MARKER in existing and END_MARKER in existing:
                updated = _MARKER_RE.sub(lambda _m: fenced, existing, count=1)
                handoff_path.write_text(updated, encoding="utf-8")
                return
        except OSError:
            pass

    out_dir = _data_dir() / "handoffs"
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_hash = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:12]
    snap_path = out_dir / f"{repo_hash}.md"
    header = f"# Auto-Handoff Snapshot ({repo_root.name})\n\n"
    try:
        snap_path.write_text(header + fenced + "\n", encoding="utf-8")
    except OSError:
        pass


def _send_notification(title: str, body: str, urgency: str = "normal") -> None:
    if os.environ.get("AGENT_HOOKS_DISABLE_NOTIFY") == "1":
        return
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "AI Agent", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def handle(event: dict[str, Any]) -> dict[str, Any]:
    reason = str(event.get("termination_reason") or "NO_TOOL_CALL")
    if reason == "USER_CANCELED":
        return {"decision": "allow"}

    agent = str(event.get("agent") or "agent")
    cwd_str = str(event.get("cwd") or "")
    conv_id = str(event.get("conversation_id") or "")
    project_name = Path(cwd_str).name if cwd_str else "workspace"

    dirty_count = 0
    if cwd_str and Path(cwd_str).is_dir():
        root_str = _run_git(Path(cwd_str), "rev-parse", "--show-toplevel")
        if root_str:
            repo_root = Path(root_str)
            project_name = repo_root.name
            snapshot_body, dirty_count = _build_snapshot(repo_root, agent, reason)
            if dirty_count > 0:
                _write_auto_handoff(repo_root, snapshot_body)

    did_real_work = (
        dirty_count > 0
        or int(event.get("execution_num") or 0) > 1
        or has_session_activity(conv_id)
    )

    if reason in ("ERROR", "MAX_TOKEN_BUDGET_EXCEEDED", "MAX_INVOCATIONS"):
        _send_notification(
            f"{agent}: attention needed ({project_name})",
            f"Stopped with {reason}. Consider updating HANDOFF.md.",
            urgency="critical" if reason == "ERROR" else "normal",
        )
    elif did_real_work and not event.get("continuation_active"):
        suffix = f" ({dirty_count} dirty files)" if dirty_count else ""
        reminder = " — update HANDOFF.md" if dirty_count >= 5 else ""
        _send_notification(
            f"{agent}: task finished ({project_name})",
            f"Turn completed{suffix}{reminder}.",
        )

    return {"decision": "allow"}
