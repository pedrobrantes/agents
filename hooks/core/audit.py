"""PostToolUse JSONL audit logger with secret redaction, token estimates, and 30d rotation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .policy import AGENT_HOOKS_DATA_DIR, AUDIT_RETENTION_DAYS
from .redact import redact_text, redact_value


def _data_dir() -> Path:
    override = os.environ.get("AGENT_HOOKS_DATA_DIR")
    return Path(override) if override else AGENT_HOOKS_DATA_DIR


def _audit_file_for_today(base_dir: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return base_dir / f"audit-{day}.jsonl"


def prune_old_logs(base_dir: Path, retention_days: int = AUDIT_RETENTION_DAYS) -> None:
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=retention_days)
    for path in base_dir.glob("audit-*.jsonl"):
        date_part = path.stem.removeprefix("audit-")
        try:
            file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            try:
                path.unlink()
            except OSError:
                pass


def has_session_activity(conversation_id: str) -> bool:
    """Return True if today's audit log already recorded tool calls for this session."""
    if not conversation_id:
        return False
    log_path = _audit_file_for_today(_data_dir())
    if not log_path.is_file():
        return False
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if conversation_id in line:
                    return True
    except OSError:
        return False
    return False


def handle(event: dict[str, Any]) -> dict[str, Any]:
    base_dir = _data_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base_dir, 0o700)
    except OSError:
        pass

    tool = event.get("tool") or {}
    raw_args = tool.get("args") or {}
    raw_args_len = len(json.dumps(raw_args, ensure_ascii=False, default=str))

    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": event.get("agent", ""),
        "conversation_id": event.get("conversation_id", ""),
        "cwd": event.get("cwd", ""),
        "tool": tool.get("raw_name") or tool.get("kind", ""),
        "kind": tool.get("kind", ""),
        "step_idx": event.get("step_idx"),
        "ok": not bool(event.get("error")),
        "error": redact_text(str(event.get("error") or ""))[:300],
        "args": redact_value(raw_args, max_str_len=240),
        "args_chars": raw_args_len,
        "est_input_tokens": max(1, raw_args_len // 4) if raw_args_len else 0,
    }

    log_path = _audit_file_for_today(base_dir)
    is_new_day_file = not log_path.exists()
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    if is_new_day_file:
        prune_old_logs(base_dir)

    return {}
