"""Unit tests for engineering, Nix flake, and Markdown convention guards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import engineering  # noqa: E402


def _init_fake_hm_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "flake.nix").write_text("{ }\n")
    (tmp_path / "programs").mkdir()
    (tmp_path / "tests" / "programs").mkdir(parents=True)
    (tmp_path / "programs" / "git.nix").write_text("{ }\n")
    (tmp_path / "tests" / "programs" / "test_git.py").write_text("def test_ok(): pass\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    return tmp_path


def test_blocks_switch_when_untracked_or_missing_test(tmp_path: Path):
    repo = _init_fake_hm_repo(tmp_path)

    # Clean + matching test -> allowed
    res_ok = engineering.handle(
        {"cwd": str(repo), "tool": {"kind": "shell", "command": "./switch.sh"}}
    )
    assert res_ok["decision"] == "allow"

    # Untracked new nix module without matching test -> denied with both reasons
    (repo / "programs" / "newtool.nix").write_text("{ }\n")
    res_fail = engineering.handle(
        {"cwd": str(repo), "tool": {"kind": "shell", "command": "./switch.sh"}}
    )
    assert res_fail["decision"] == "deny"
    assert "Untracked files exist" in res_fail["reason"]
    assert "test_newtool.py" in res_fail["reason"]


def test_blocks_markdown_emojis_outside_gemini_dir():
    res_deny = engineering.handle(
        {
            "cwd": "/repo",
            "tool": {"kind": "write", "path": "/repo/README.md", "content": "# Title \U0001F680\n"},
        }
    )
    assert res_deny["decision"] == "deny"

    res_clean = engineering.handle(
        {
            "cwd": "/repo",
            "tool": {"kind": "write", "path": "/repo/README.md", "content": "# Clean Title\n"},
        }
    )
    assert res_clean["decision"] == "allow"

    # Non-markdown files are unaffected
    res_py = engineering.handle(
        {
            "cwd": "/repo",
            "tool": {"kind": "write", "path": "/repo/ui.py", "content": "ICON = '\U0001F680'\n"},
        }
    )
    assert res_py["decision"] == "allow"
