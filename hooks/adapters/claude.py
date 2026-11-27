"""Claude Code hook protocol adapter.

Translates Claude Code snake_case JSON payloads (Bash/Read/Write/Edit) into
the canonical internal event format and outputs Claude Code compatible JSON.
"""

from __future__ import annotations

from typing import Any


TOOL_NAME_MAP: dict[str, str] = {
    "Bash": "shell",
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "MultiEdit": "edit",
}


def _extract_content(tool_input: dict[str, Any]) -> str:
    if isinstance(tool_input.get("content"), str):
        return tool_input["content"]
    if isinstance(tool_input.get("new_string"), str):
        return tool_input["new_string"]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        return "\n".join(
            str(e.get("new_string", "")) for e in edits if isinstance(e, dict)
        )
    return ""


def normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert Claude Code hook stdin JSON into canonical event structure."""
    raw_tool_name = str(raw.get("tool_name") or "")
    tool_input = raw.get("tool_input") if isinstance(raw.get("tool_input"), dict) else {}
    canonical_tool = TOOL_NAME_MAP.get(raw_tool_name, raw_tool_name.lower())

    cwd = str(raw.get("cwd") or "")
    command = tool_input.get("command") if isinstance(tool_input.get("command"), str) else ""
    path = tool_input.get("file_path") if isinstance(tool_input.get("file_path"), str) else ""
    offset = tool_input.get("offset")
    limit = tool_input.get("limit")
    start_line = offset if isinstance(offset, int) else None
    end_line = (start_line + limit) if (isinstance(start_line, int) and isinstance(limit, int)) else None

    return {
        "agent": "claude",
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
            "id": str(raw.get("tool_use_id") or ""),
            "raw_name": raw_tool_name,
            "kind": canonical_tool,
            "args": tool_input,
            "command": command,
            "path": path,
            "content": _extract_content(tool_input),
            "start_line": start_line,
            "end_line": end_line,
        },
        "raw": raw,
    }


def format_output(hook_kind: str, result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Translate canonical hook result into Claude Code JSON output + exit code."""
    if hook_kind == "pre_tool":
        decision = result.get("decision", "allow")
        reason = str(result.get("reason") or "")
        claude_decision = {
            "allow": "allow",
            "deny": "deny",
            "ask": "ask",
            "force_ask": "ask",
        }.get(decision, "allow")
        hook_out: dict[str, Any] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": claude_decision,
        }
        if reason:
            hook_out["permissionDecisionReason"] = reason
        if result.get("overwrite_command"):
            hook_out["updatedInput"] = {"command": str(result["overwrite_command"])}
        return {"hookSpecificOutput": hook_out}, 0

    if hook_kind == "session_start":
        msg = result.get("system_message")
        if msg:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": str(msg),
                }
            }, 0
        return {}, 0

    if hook_kind == "stop":
        if result.get("decision") == "continue":
            return {
                "decision": "block",
                "reason": str(result.get("reason") or "Quality gate reported issues."),
            }, 0
        return {}, 0

    return {}, 0
