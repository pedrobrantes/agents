"""Unit tests for cross-agent adapters and dispatcher failure policies."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dispatch  # noqa: E402


def test_agy_adapter_pre_tool_deny_and_overwrite():
    out_deny, code = dispatch.dispatch_payload(
        "agy",
        "safety-guard",
        {
            "hookEventName": "PreToolUse",
            "cwd": "/tmp",
            "toolCall": {
                "id": "t1",
                "name": "run_command",
                "args": {"CommandLine": "git push --force origin main"},
            },
        },
    )
    assert code == 0
    assert out_deny["decision"] == "deny"

    out_compact, code = dispatch.dispatch_payload(
        "agy",
        "token-guard",
        {
            "hookEventName": "PreToolUse",
            "cwd": "/tmp",
            "toolCall": {
                "id": "t2",
                "name": "run_command",
                "args": {"CommandLine": "pytest -q"},
            },
        },
    )
    assert code == 0
    assert out_compact["decision"] == "allow"
    assert "compact_cmd.py" in out_compact["overwrite"]["CommandLine"]


def test_claude_adapter_pre_tool_and_session_start():
    out, code = dispatch.dispatch_payload(
        "claude",
        "safety-guard",
        {
            "hook_event_name": "PreToolUse",
            "session_id": "s1",
            "cwd": "/tmp",
            "tool_name": "Bash",
            "tool_input": {"command": "sudo rm -rf /"},
        },
    )
    assert code == 0
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_gemini_adapter_pre_tool():
    out, code = dispatch.dispatch_payload(
        "gemini",
        "safety-guard",
        {
            "hook_event_name": "BeforeTool",
            "session_id": "g1",
            "cwd": "/tmp",
            "tool_name": "run_shell_command",
            "tool_input": {"command": "git reset --hard"},
        },
    )
    assert code == 0
    assert out["decision"] == "deny"


def test_fail_closed_for_safety_and_fail_open_for_others(monkeypatch):
    def boom(_event):
        raise RuntimeError("boom")

    monkeypatch.setitem(dispatch.HOOK_REGISTRY, "safety-guard", ("pre_tool", boom, True))
    monkeypatch.setitem(dispatch.HOOK_REGISTRY, "token-guard", ("pre_tool", boom, False))

    out_safety, _ = dispatch.dispatch_payload("agy", "safety-guard", {})
    assert out_safety["decision"] == "force_ask"

    out_token, _ = dispatch.dispatch_payload("agy", "token-guard", {})
    assert out_token["decision"] == "allow"
