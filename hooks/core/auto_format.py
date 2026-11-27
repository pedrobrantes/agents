"""PostToolUse silent single-file auto-formatter (0 tokens, <2s timeout)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

_PRETTIER_EXTS = frozenset({".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".json"})
_PRETTIER_CONFIG_NAMES = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yml",
    ".prettierrc.yaml",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.mjs",
    "prettier.config.js",
    "prettier.config.cjs",
    "prettier.config.mjs",
)


def _has_prettier_config(file_path: Path) -> bool:
    for parent in (file_path.parent, *file_path.parent.parents):
        if any((parent / cfg).exists() for cfg in _PRETTIER_CONFIG_NAMES):
            return True
        if (parent / ".git").exists():
            break
    return False


def _select_formatter(file_path: Path) -> list[str] | None:
    ext = file_path.suffix.lower()
    if ext == ".py" and shutil.which("ruff"):
        return ["ruff", "format", "--quiet", str(file_path)]
    if ext == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", str(file_path)]
    if ext == ".rs" and shutil.which("rustfmt"):
        return ["rustfmt", "--quiet", str(file_path)]
    if ext == ".nix":
        if shutil.which("nixfmt"):
            return ["nixfmt", str(file_path)]
        if shutil.which("alejandra"):
            return ["alejandra", "-q", str(file_path)]
    if ext in _PRETTIER_EXTS and shutil.which("prettier") and _has_prettier_config(file_path):
        return ["prettier", "--write", "--log-level", "silent", str(file_path)]
    return None


def handle(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("error"):
        return {}

    tool = event.get("tool") or {}
    if tool.get("kind") not in ("write", "edit"):
        return {}

    path_str = str(tool.get("path") or "")
    if not path_str:
        return {}

    file_path = Path(path_str).expanduser()
    if not file_path.is_absolute() and event.get("cwd"):
        file_path = Path(event["cwd"]) / file_path
    if not file_path.is_file():
        return {}

    cmd = _select_formatter(file_path)
    if not cmd:
        return {}

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass

    return {}
