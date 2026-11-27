"""Unit tests for the RTK-style command output compactor."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.compact_cmd import compact_output  # noqa: E402


def test_short_output_passes_through_verbatim():
    text = "3 passed in 0.12s\n"
    assert compact_output("pytest", text, 0) == text


def test_compacts_verbose_pytest_preserving_failures():
    lines = ["=== test session starts ==="]
    lines.extend([f"tests/test_mod.py::test_ok_{i} PASSED" for i in range(150)])
    lines.append("FAILED tests/test_mod.py::test_boom - AssertionError: expected 1 == 2")
    lines.append("E   assert 1 == 2")
    lines.append("1 failed, 150 passed in 2.34s")
    raw = "\n".join(lines) + "\n"

    compacted = compact_output("pytest -v", raw, 1)
    assert len(compacted) < len(raw)
    assert "FAILED tests/test_mod.py::test_boom" in compacted
    assert "1 failed, 150 passed" in compacted
    assert "exit=1" in compacted


def test_compacts_large_git_diff_with_file_list():
    lines = ["diff --git a/foo.py b/foo.py", "--- a/foo.py", "+++ b/foo.py"]
    lines.extend([f"+line {i}" for i in range(250)])
    raw = "\n".join(lines) + "\n"

    compacted = compact_output("git diff", raw, 0)
    assert "diff lines omitted" in compacted
    assert "Files in diff:" in compacted
    assert "diff --git a/foo.py b/foo.py" in compacted
