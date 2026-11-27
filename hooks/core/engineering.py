"""PreToolUse engineering, Nix flake, and documentation convention guards."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

# Unicode emoji ranges (symbols/pictographs, dingbats, variation selector-16).
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0000FE0F]"
)

_SWITCH_CMD_RE = re.compile(r"(?:^|[;&|]\s*)(?:\./switch\.sh\b|home-manager\s+switch\b)")


def _find_home_manager_root(cwd: str, command: str) -> Path | None:
    candidates: list[Path] = []
    if cwd:
        candidates.append(Path(cwd))
    default_hm = Path.home() / ".config" / "home-manager"
    if "home-manager" in command or default_hm.exists():
        candidates.append(default_hm)

    for base in candidates:
        cur = base.resolve()
        for parent in (cur, *cur.parents):
            if (parent / "flake.nix").exists() and (parent / "programs").is_dir():
                return parent
    return None


def _check_nix_switch_readiness(repo_root: Path) -> str | None:
    issues: list[str] = []

    # 1. Untracked files invisible to Nix flakes.
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0:
            untracked = [
                line[3:].strip()
                for line in proc.stdout.splitlines()
                if line.startswith("?? ")
            ]
            if untracked:
                preview = ", ".join(untracked[:5])
                suffix = f" (+{len(untracked) - 5} more)" if len(untracked) > 5 else ""
                issues.append(
                    f"Untracked files exist ({preview}{suffix}). Nix flakes ignore untracked files — run `git add` first."
                )
    except (OSError, subprocess.TimeoutExpired):
        pass

    # 2. Enforce matching test_<name>.py for every programs/<name>.nix.
    programs_dir = repo_root / "programs"
    tests_dir = repo_root / "tests" / "programs"
    if programs_dir.is_dir() and tests_dir.is_dir():
        missing_tests: list[str] = []
        for nix_file in sorted(programs_dir.glob("*.nix")):
            if nix_file.name == "default.nix":
                continue
            expected_test = tests_dir / f"test_{nix_file.stem}.py"
            if not expected_test.exists():
                missing_tests.append(f"tests/programs/{expected_test.name}")
        if missing_tests:
            issues.append(
                "Missing required program tests: " + ", ".join(missing_tests)
            )

    if issues:
        return "Nix home-manager pre-switch check failed: " + " | ".join(issues)
    return None


def _check_markdown_emojis(path_str: str, content: str) -> str | None:
    if os.environ.get("ALLOW_MD_EMOJI") == "1":
        return None
    normalized = path_str.replace("\\", "/")
    if not normalized.lower().endswith(".md"):
        return None
    if "/.gemini/" in normalized:
        return None
    if _EMOJI_RE.search(content):
        return (
            f"Blocked emojis in Markdown documentation '{Path(normalized).name}'. "
            "Per ~/.agents/AGENTS.md, keep Markdown headings, callouts, and lists text-only."
        )
    return None


def handle(event: dict[str, Any]) -> dict[str, Any]:
    tool = event.get("tool") or {}
    kind = tool.get("kind", "")
    cwd = str(event.get("cwd") or "")

    if kind == "shell":
        command = str(tool.get("command") or "").strip()
        if command and _SWITCH_CMD_RE.search(command):
            hm_root = _find_home_manager_root(cwd, command)
            if hm_root is not None:
                reason = _check_nix_switch_readiness(hm_root)
                if reason:
                    return {"decision": "deny", "reason": reason}

    if kind in ("write", "edit"):
        path = str(tool.get("path") or "")
        content = str(tool.get("content") or "")
        reason = _check_markdown_emojis(path, content)
        if reason:
            return {"decision": "deny", "reason": reason}

    return {"decision": "allow"}
