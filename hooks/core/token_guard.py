"""PreToolUse token-efficiency guard and safe output compaction router."""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from .policy import (
    JUNK_DIR_SEGMENTS,
    LOCKFILE_NAMES,
    MAX_CAT_LINES,
    MAX_LOCKFILE_SLICE_LINES,
    MINIFIED_SUFFIXES,
)

COMPACT_CMD_SCRIPT = Path(__file__).resolve().parent / "compact_cmd.py"

# Characters indicating compound shell syntax that should not be rewritten blindly.
_COMPOUND_SHELL_RE = re.compile(r"[|><;&`\n]|\$\(")

# Simple, deterministic verbose commands safe to wrap with compact_cmd.py.
_COMPACTABLE_CMD_RE = re.compile(
    r"^(?:uv\s+run\s+pytest|pytest|cargo\s+(?:test|check)|go\s+test|"
    r"(?:npm|pnpm|yarn)\s+test|nix\s+flake\s+check|git\s+diff|git\s+log)\b"
)

_GREP_RECURSIVE_RE = re.compile(r"(?:^|[;&|]\s*)grep\b[^\n]*\s-(?:[a-zA-Z]*[rR][a-zA-Z]*)\b")
_FIND_UNBOUNDED_RE = re.compile(r"(?:^|[;&|]\s*)find\s+\S+")
_GIT_LOG_RE = re.compile(r"(?:^|[;&|]\s*)git\s+(?:-C\s+\S+\s+)?log\b")
_GIT_LOG_BOUNDED_RE = re.compile(r"(?:\s-n\s*\d+|\s--max-count(?:=|\s)\d+|\s-\d+\b|\s--stat\b|\s--shortstat\b|\.\.)")


def _check_read_path(path_str: str, start_line: int | None, end_line: int | None) -> str | None:
    if not path_str:
        return None
    normalized = path_str.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    name = parts[-1] if parts else ""

    for seg in parts[:-1]:
        if seg in JUNK_DIR_SEGMENTS:
            return (
                f"Blocked reading inside '{seg}/' to save tokens. "
                "Use targeted search (rg/fd) if you genuinely need a specific file."
            )

    if any(name.endswith(sfx) for sfx in MINIFIED_SUFFIXES):
        return f"Blocked reading minified/sourcemap file '{name}' to prevent token blowup."

    if name in LOCKFILE_NAMES:
        if (
            isinstance(start_line, int)
            and isinstance(end_line, int)
            and 0 <= (end_line - start_line) <= MAX_LOCKFILE_SLICE_LINES
        ):
            return None
        return (
            f"Blocked unbounded read of lockfile '{name}'. "
            f"Use rg to locate a package or pass StartLine/EndLine (<= {MAX_LOCKFILE_SLICE_LINES} lines)."
        )

    return None


def _count_file_lines(path: Path, limit: int) -> int:
    count = 0
    try:
        with path.open("rb") as fh:
            for _ in fh:
                count += 1
                if count > limit:
                    return count
    except OSError:
        return 0
    return count


def _check_large_cat(command: str, cwd: str) -> str | None:
    if _COMPOUND_SHELL_RE.search(command):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) != 2 or tokens[0] != "cat" or tokens[1].startswith("-"):
        return None

    target = Path(tokens[1]).expanduser()
    if not target.is_absolute() and cwd:
        target = Path(cwd) / target
    if target.is_file():
        lines = _count_file_lines(target, MAX_CAT_LINES)
        if lines > MAX_CAT_LINES:
            return (
                f"Blocked `cat` on large file '{tokens[1]}' (>{MAX_CAT_LINES} lines). "
                "Use read_file with StartLine/EndLine, head/tail, or rg instead."
            )
    return None


def should_compact_command(command: str) -> bool:
    if os.environ.get("AGENT_HOOKS_DISABLE_COMPACT") == "1":
        return False
    if "compact_cmd.py" in command:
        return False
    if _COMPOUND_SHELL_RE.search(command):
        return False
    return bool(_COMPACTABLE_CMD_RE.match(command.strip()))


def handle(event: dict[str, Any]) -> dict[str, Any]:
    tool = event.get("tool") or {}
    kind = tool.get("kind", "")
    cwd = str(event.get("cwd") or "")

    if kind == "read":
        reason = _check_read_path(
            str(tool.get("path") or ""),
            tool.get("start_line"),
            tool.get("end_line"),
        )
        if reason:
            return {"decision": "deny", "reason": reason}
        return {"decision": "allow"}

    if kind == "shell":
        command = str(tool.get("command") or "").strip()
        if not command:
            return {"decision": "allow"}

        if _GREP_RECURSIVE_RE.search(command):
            return {
                "decision": "deny",
                "reason": "Use `rg` instead of recursive `grep -r` (faster, respects .gitignore, saves tokens).",
            }

        if _FIND_UNBOUNDED_RE.search(command) and not re.search(r"-maxdepth\s+[12]\b", command):
            return {
                "decision": "deny",
                "reason": "Use `fd` instead of unbounded `find` (respects .gitignore and avoids noisy trees).",
            }

        if _GIT_LOG_RE.search(command) and not _GIT_LOG_BOUNDED_RE.search(command):
            return {
                "decision": "deny",
                "reason": "Unbounded `git log` wastes tokens. Add `-n 20 --oneline` or an explicit range.",
            }

        large_cat_reason = _check_large_cat(command, cwd)
        if large_cat_reason:
            return {"decision": "deny", "reason": large_cat_reason}

        if should_compact_command(command):
            py_bin = shlex.quote(sys.executable or "python3")
            wrapped = f"{py_bin} {shlex.quote(str(COMPACT_CMD_SCRIPT))} --cmd {shlex.quote(command)}"
            return {
                "decision": "allow",
                "overwrite_command": wrapped,
            }

    return {"decision": "allow"}
