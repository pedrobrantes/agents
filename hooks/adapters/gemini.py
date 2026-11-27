"""Gemini CLI hook protocol adapter.

Translates Gemini CLI hook payloads (BeforeTool/AfterTool/SessionStart/AfterAgent)
into the canonical internal event format.
"""

from __future__ import annotations

from typing import Any


TOOL_NAME_MAP: dict[str, str] = {
    "run_shell_command": "shell",
    "read_file": "read",
    "write_file": "write",
    "replace": "edit",
}


def normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    raw_tool_name = str(raw.get("tool_name") or "")
    tool_input = raw.get("tool_input") if isinstance(raw.get("tool_input"), dict) else {}
    canonical_tool = TOOL_NAME_MAP.get(raw_tool_name, raw_tool_name.lower())
    cwd = str(raw.get("cwd") or "")

    command = tool_input.get("command") if isinstance(tool_input.get("command"), str) else ""
    path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or ""
    )
    content = (
        tool_input.get("content")
        or tool_input.get("new_string")
        or ""
    )

    return {
        "agent": "gemini",
        "event": str(raw.get("hook_event_name") or ""),
        "conversation_id": str(raw.get("session_id") or ""),
        "cwd": cwd,
        "workspace_paths": [cwd] if cwd else [],
        "model_name": str(raw.get("model") or ""),
        "last_user_input": "",
        "step_idx": None,
        "error": str(raw.get("error") or ""),
        "execution_num": 1,
        "termination_reason": "NO_TOOL_CALL",
        "fully_idle": True,
        "continuation_active": bool(raw.get("stop_hook_active", False)),
        "tool": {
            "id": str(raw.get("tool_call_id") or ""),
            "raw_name": raw_tool_name,
            "kind": canonical_tool,
            "args": tool_input,
            "command": command,
            "path": str(path) if isinstance(path, str) else "",
            "content": str(content) if isinstance(content, str) else "",
            "start_line": tool_input.get("offset") if isinstance(tool_input.get("offset"), int) else None,
            "end_line": None,
        },
        "raw": raw,
    }


def format_output(hook_kind: str, result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if hook_kind == "pre_tool":
        decision = result.get("decision", "allow")
        if decision == "deny":
            return {"decision": "deny", "reason": str(result.get("reason") or "")}, 0
        if decision in ("ask", "force_ask"):
            return {"decision": "ask", "reason": str(result.get("reason") or "")}, 0
        return {"decision": "allow"}, 0

    if hook_kind == "session_start":
        msg = result.get("system_message")
        if msg:
            return {"systemMessage": str(msg)}, 0
        return {}, 0

    if hook_kind == "stop":
        if result.get("decision") == "continue":
            return {"decision": "deny", "reason": str(result.get("reason") or "")}, 0
        return {"decision": "allow"}, 0

    return {}, 0
