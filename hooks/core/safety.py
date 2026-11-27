"""PreToolUse safety guardrails.

Mirrors ~/.config/home-manager/programs/opencode.nix denylist, adds hardcoded
secret detection for write/edit operations, and enforces force_ask on pushes,
deploys, and infrastructure mutations.
"""

from __future__ import annotations

import shlex
from typing import Any

from .policy import (
    DENY_SHELL_PATTERNS,
    FORCE_ASK_SHELL_PATTERNS,
    SECRET_CONTENT_PATTERNS,
    SECRET_IGNORE_MARKERS,
    SENSITIVE_PATH_PATTERNS,
)


def is_sensitive_path(path: str) -> bool:
    if not path:
        return False
    normalized = path.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in SENSITIVE_PATH_PATTERNS)


def find_hardcoded_secret(content: str, path: str = "") -> str | None:
    """Return label of detected secret in written/edited content, or None."""
    if not content:
        return None
    normalized = path.replace("\\", "/")
    if normalized.endswith(".sops.yaml") or normalized.endswith(".sops.yml"):
        return None

    for line in content.splitlines():
        upper = line.upper()
        if any(marker.upper() in upper for marker in SECRET_IGNORE_MARKERS):
            continue
        for label, pattern in SECRET_CONTENT_PATTERNS:
            if pattern.search(line):
                return label
    return None


def _shell_references_sensitive_path(command: str) -> str | None:
    """Detect shell commands attempting to read/cat sensitive files directly."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    for tok in tokens[1:]:
        cleaned = tok.strip("'\"")
        if is_sensitive_path(cleaned):
            return cleaned
    return None


def handle(event: dict[str, Any]) -> dict[str, Any]:
    tool = event.get("tool") or {}
    kind = tool.get("kind", "")
    path = str(tool.get("path") or "")
    content = str(tool.get("content") or "")
    command = str(tool.get("command") or "").strip()

    if kind in ("read", "write", "edit"):
        if is_sensitive_path(path):
            return {
                "decision": "deny",
                "reason": (
                    f"Blocked access to sensitive path '{path}'. "
                    "Keep secrets managed via sops-nix and never read or edit secret files directly."
                ),
            }

    if kind in ("write", "edit"):
        secret_label = find_hardcoded_secret(content, path=path)
        if secret_label:
            return {
                "decision": "deny",
                "reason": (
                    f"Blocked writing potential hardcoded secret ({secret_label}) into '{path}'. "
                    "Use sops-nix or environment/file references instead."
                ),
            }

    if kind == "shell" and command:
        for label, pattern in DENY_SHELL_PATTERNS:
            if pattern.search(command):
                return {
                    "decision": "deny",
                    "reason": f"Blocked dangerous shell command ({label}).",
                }

        sensitive_ref = _shell_references_sensitive_path(command)
        if sensitive_ref:
            return {
                "decision": "deny",
                "reason": (
                    f"Blocked shell command referencing sensitive file '{sensitive_ref}'. "
                    "Secrets must not be inspected directly by agents."
                ),
            }

        for label, pattern in FORCE_ASK_SHELL_PATTERNS:
            if pattern.search(command):
                return {
                    "decision": "force_ask",
                    "reason": f"Explicit confirmation required for {label}.",
                }

    return {"decision": "allow"}
