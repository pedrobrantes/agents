"""Unit tests for PreToolUse token-efficiency guard."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import token_guard  # noqa: E402


def _read_event(path: str, start: int | None = None, end: int | None = None) -> dict:
    return {
        "agent": "agy",
        "cwd": "/tmp",
        "tool": {
            "kind": "read",
            "path": path,
            "start_line": start,
            "end_line": end,
            "args": {},
        },
    }


def _shell_event(command: str, cwd: str = "/tmp") -> dict:
    return {
        "agent": "agy",
        "cwd": cwd,
        "tool": {
            "kind": "shell",
            "command": command,
            "args": {},
        },
    }


def test_blocks_junk_dirs_and_minified():
    for path in (
        "/repo/node_modules/pkg/index.js",
        "/repo/.git/objects/pack/foo",
        "/repo/target/debug/out.txt",
        "/repo/dist/app.min.js",
    ):
        res = token_guard.handle(_read_event(path))
        assert res["decision"] == "deny"


def test_blocks_unbounded_lockfile_but_allows_small_slice():
    assert token_guard.handle(_read_event("/repo/flake.lock"))["decision"] == "deny"
    assert token_guard.handle(_read_event("/repo/flake.lock", start=1, end=40))["decision"] == "allow"
    assert token_guard.handle(_read_event("/repo/flake.lock", start=1, end=500))["decision"] == "deny"


def test_blocks_explosive_shell_commands(tmp_path: Path):
    assert token_guard.handle(_shell_event("grep -rn foo ."))["decision"] == "deny"
    assert token_guard.handle(_shell_event("find . -name '*.py'"))["decision"] == "deny"
    assert token_guard.handle(_shell_event("git log"))["decision"] == "deny"
    assert token_guard.handle(_shell_event("git log -n 10 --oneline"))["decision"] == "allow"

    big_file = tmp_path / "big.txt"
    big_file.write_text("\n".join(f"line {i}" for i in range(600)))
    assert token_guard.handle(_shell_event("cat big.txt", cwd=str(tmp_path)))["decision"] == "deny"

    small_file = tmp_path / "small.txt"
    small_file.write_text("hello\nworld\n")
    assert token_guard.handle(_shell_event("cat small.txt", cwd=str(tmp_path)))["decision"] == "allow"


def test_rewrites_simple_verbose_commands_only():
    res = token_guard.handle(_shell_event("pytest -v"))
    assert res["decision"] == "allow"
    assert "compact_cmd.py" in res["overwrite_command"]

    # Compound commands with pipes/chains must NOT be rewritten.
    res_pipe = token_guard.handle(_shell_event("pytest -v | tee out.log"))
    assert res_pipe["decision"] == "allow"
    assert "overwrite_command" not in res_pipe
