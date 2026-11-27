"""Unit tests for SessionStart, Audit Telemetry, Stop Gate, and Auto-Handoff."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import audit, notify_handoff, session_start, stop_gate  # noqa: E402


def _init_git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "app.py").write_text("def hello():\n    return 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    return tmp_path


def test_audit_redacts_secrets_and_logs_tokens(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENT_HOOKS_DATA_DIR", str(tmp_path))
    secret = "ghp_" + "a" * 36
    audit.handle(
        {
            "agent": "agy",
            "conversation_id": "conv-123",
            "cwd": "/repo",
            "step_idx": 2,
            "error": "",
            "tool": {
                "raw_name": "run_command",
                "kind": "shell",
                "args": {"CommandLine": f"curl -H 'Authorization: Bearer {secret}' https://example.com"},
            },
        }
    )

    log_files = list(tmp_path.glob("audit-*.jsonl"))
    assert len(log_files) == 1
    rec = json.loads(log_files[0].read_text().strip())
    assert secret not in json.dumps(rec)
    assert "[REDACTED]" in json.dumps(rec)
    assert rec["est_input_tokens"] > 0
    assert audit.has_session_activity("conv-123") is True


def test_session_start_respects_budget_and_reads_handoff(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENT_HOOKS_DATA_DIR", str(tmp_path / "data"))
    repo = _init_git_repo(tmp_path / "repo")
    (repo / "HANDOFF.md").write_text("# Handoff\n- Goal: Ship hooks\n- Next: Run tests\n")

    res = session_start.handle({"cwd": str(repo)})
    msg = res["system_message"]
    assert "HANDOFF.md excerpt" in msg
    assert "Ship hooks" in msg
    assert len(msg.splitlines()) <= session_start.MAX_LINES


def test_stop_gate_catches_debug_prints_and_respects_anti_loop(tmp_path: Path):
    repo = _init_git_repo(tmp_path)
    (repo / "app.py").write_text("def hello():\n    breakpoint()\n    return 1\n")

    res = stop_gate.handle(
        {
            "cwd": str(repo),
            "continuation_active": False,
            "termination_reason": "NO_TOOL_CALL",
        }
    )
    assert res["decision"] == "continue"
    assert "breakpoint" in res["reason"].lower()

    # Anti-loop: second pass with continuation_active=True must allow stopping
    res_loop = stop_gate.handle(
        {
            "cwd": str(repo),
            "continuation_active": True,
            "termination_reason": "NO_TOOL_CALL",
        }
    )
    assert res_loop["decision"] == "allow"


def test_auto_handoff_writes_outside_repo_unless_fenced_handoff_exists(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("AGENT_HOOKS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AGENT_HOOKS_DISABLE_NOTIFY", "1")

    repo = _init_git_repo(tmp_path / "repo")
    (repo / "app.py").write_text("def hello():\n    return 2\n")

    res = notify_handoff.handle(
        {
            "agent": "agy",
            "cwd": str(repo),
            "conversation_id": "conv-9",
            "termination_reason": "NO_TOOL_CALL",
            "execution_num": 2,
            "continuation_active": False,
        }
    )
    assert res["decision"] == "allow"
    assert not (repo / "HANDOFF.md").exists()
    snaps = list((data_dir / "handoffs").glob("*.md"))
    assert len(snaps) == 1
    assert "app.py" in snaps[0].read_text()

    # If HANDOFF.md exists with fenced markers, update in-place preserving custom text
    (repo / "HANDOFF.md").write_text(
        "# Notes\nKeep me.\n\n<!-- AUTO-STATE:START -->\nold\n<!-- AUTO-STATE:END -->\n"
    )
    notify_handoff.handle(
        {
            "agent": "agy",
            "cwd": str(repo),
            "conversation_id": "conv-9",
            "termination_reason": "NO_TOOL_CALL",
            "execution_num": 2,
            "continuation_active": False,
        }
    )
    updated = (repo / "HANDOFF.md").read_text()
    assert "Keep me." in updated
    assert "old" not in updated
    assert "app.py" in updated
