"""Antigravity (agy) hook protocol adapter.

Normalizes camelCase protojson payloads from agy into the canonical internal
event format and translates core hook results back to agy stdout JSON.
"""

from __future__ import annotations

from typing import Any


TOOL_NAME_MAP: dict[str, str] = {
    "run_command": "shell",
    "read_file": "read",
    "view_file": "read",
    "write_file": "write",
    "write_to_file": "write",
    "edit_file": "edit",
    "replace_file_content": "edit",
    "multi_replace_file_content": "edit",
}


def _get_ci(mapping: dict[str, Any], *keys: str) -> Any:
    """Case-insensitive lookup across candidate keys."""
    lowered = {k.lower(): v for k, v in mapping.items()}
    for key in keys:
        if key in mapping:
            return mapping[key]
        val = lowered.get(key.lower())
        if val is not None:
            return val
    return None


def _extract_content(raw_tool_name: str, args: dict[str, Any]) -> str:
    """Extract written/edited text content from agy write/edit tool arguments."""
    chunks = _get_ci(args, "ReplacementChunks")
    if isinstance(chunks, list):
        parts: list[str] = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                rc = _get_ci(chunk, "ReplacementContent", "Replacement")
                if isinstance(rc, str):
                    parts.append(rc)
        return "\n".join(parts)

    content = _get_ci(
        args,
        "Content",
        "CodeContent",
        "Replacement",
        "ReplacementContent",
    )
    return content if isinstance(content, str) else ""


def normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert raw agy stdin JSON into canonical event structure."""
    tool_call = raw.get("toolCall") if isinstance(raw.get("toolCall"), dict) else {}
    raw_tool_name = str(tool_call.get("name") or "")
    args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}

    canonical_tool = TOOL_NAME_MAP.get(raw_tool_name, raw_tool_name)
    command = _get_ci(args, "CommandLine", "command")
    path = _get_ci(args, "Path", "AbsolutePath", "TargetFile", "file_path")
    start_line = _get_ci(args, "StartLine", "offset")
    end_line = _get_ci(args, "EndLine", "limit")

    workspace_paths = raw.get("workspacePaths")
    if not isinstance(workspace_paths, list):
        workspace_paths = []

    cwd = raw.get("cwd") or (workspace_paths[0] if workspace_paths else "")

    return {
        "agent": "agy",
        "event": str(raw.get("hookEventName") or ""),
        "conversation_id": str(raw.get("conversationId") or ""),
        "cwd": str(cwd or ""),
        "workspace_paths": [str(p) for p in workspace_paths],
        "model_name": str(raw.get("modelName") or ""),
        "last_user_input": str(raw.get("lastUserInput") or ""),
        "step_idx": raw.get("stepIdx"),
        "error": str(raw.get("error") or ""),
        "execution_num": raw.get("executionNum", 0),
        "termination_reason": str(raw.get("terminationReason") or ""),
        "fully_idle": bool(raw.get("fullyIdle", True)),
        "continuation_active": bool(raw.get("continuationActive", False)),
        "tool": {
            "id": str(tool_call.get("id") or ""),
            "raw_name": raw_tool_name,
            "kind": canonical_tool,
            "args": args,
            "command": command if isinstance(command, str) else "",
            "path": path if isinstance(path, str) else "",
            "content": _extract_content(raw_tool_name, args),
            "start_line": start_line if isinstance(start_line, int) else None,
            "end_line": end_line if isinstance(end_line, int) else None,
        },
        "raw": raw,
    }


def format_output(hook_kind: str, result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Translate canonical hook result into (agy stdout JSON, exit_code)."""
    if hook_kind == "pre_tool":
        out: dict[str, Any] = {"decision": result.get("decision", "allow")}
        if result.get("reason"):
            out["reason"] = str(result["reason"])
        if result.get("overwrite_command"):
            out["overwrite"] = {"CommandLine": str(result["overwrite_command"])}
        elif isinstance(result.get("overwrite"), dict):
            out["overwrite"] = result["overwrite"]
        return out, 0

    if hook_kind == "post_tool":
        return {}, 0

    if hook_kind == "session_start":
        msg = result.get("system_message")
        if msg:
            return {
                "injectSteps": [
                    {
                        "systemMessage": {
                            "systemMessage": str(msg),
                        }
                    }
                ]
            }, 0
        return {}, 0

    if hook_kind == "stop":
        decision = result.get("decision", "allow")
        if decision == "continue":
            out = {"decision": "continue"}
            if result.get("reason"):
                out["reason"] = str(result["reason"])
            return out, 0
        return {"decision": "allow"}, 0

    return {}, 0
