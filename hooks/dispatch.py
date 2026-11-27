#!/usr/bin/env python3
"""Unified cross-agent hook dispatcher.

Usage:
    python3 ~/.agents/hooks/dispatch.py --agent agy --hook safety-guard

Failure policy:
    - safety-guard: fail-closed (force_ask) on unexpected exceptions.
    - all other hooks: fail-open (allow / {}) so auxiliary hooks never block work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

# Ensure ~/.agents/hooks is on sys.path regardless of hook working directory.
HOOKS_ROOT = Path(__file__).resolve().parent
if str(HOOKS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOOKS_ROOT))

from adapters import agy as agy_adapter  # noqa: E402
from adapters import claude as claude_adapter  # noqa: E402
from adapters import gemini as gemini_adapter  # noqa: E402
from core import audit  # noqa: E402
from core import auto_format  # noqa: E402
from core import engineering  # noqa: E402
from core import notify_handoff  # noqa: E402
from core import safety  # noqa: E402
from core import session_start  # noqa: E402
from core import stop_gate  # noqa: E402
from core import token_guard  # noqa: E402


ADAPTERS: dict[str, Any] = {
    "agy": agy_adapter,
    "claude": claude_adapter,
    "gemini": gemini_adapter,
}

# Maps hook name -> (hook_kind, handler_fn, fail_closed)
HOOK_REGISTRY: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]], bool]] = {
    "safety-guard": ("pre_tool", safety.handle, True),
    "token-guard": ("pre_tool", token_guard.handle, False),
    "engineering-guard": ("pre_tool", engineering.handle, False),
    "auto-format": ("post_tool", auto_format.handle, False),
    "audit-telemetry": ("post_tool", audit.handle, False),
    "session-context": ("session_start", session_start.handle, False),
    "quality-hygiene-gate": ("stop", stop_gate.handle, False),
    "handoff-and-notify": ("stop", notify_handoff.handle, False),
}


def dispatch_payload(agent: str, hook_name: str, raw_payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Run a single hook against a parsed payload using the selected agent adapter."""
    adapter = ADAPTERS[agent]
    hook_kind, handler, fail_closed = HOOK_REGISTRY[hook_name]
    try:
        event = adapter.normalize_input(raw_payload)
        result = handler(event)
    except Exception as exc:  # pragma: no cover - defensive boundary
        if fail_closed:
            result = {
                "decision": "force_ask",
                "reason": f"safety-guard encountered an internal error ({type(exc).__name__}); requesting confirmation.",
            }
        else:
            result = {"decision": "allow"} if hook_kind in ("pre_tool", "stop") else {}
    return adapter.format_output(hook_kind, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-agent lifecycle hook dispatcher")
    parser.add_argument("--agent", choices=sorted(ADAPTERS), default="agy")
    parser.add_argument("--hook", choices=sorted(HOOK_REGISTRY), required=True)
    args = parser.parse_args(argv)

    raw_text = sys.stdin.read().strip()
    try:
        raw_payload = json.loads(raw_text) if raw_text else {}
        if not isinstance(raw_payload, dict):
            raw_payload = {}
    except json.JSONDecodeError:
        raw_payload = {}
        hook_kind, _handler, fail_closed = HOOK_REGISTRY[args.hook]
        if fail_closed:
            out, code = ADAPTERS[args.agent].format_output(
                hook_kind,
                {
                    "decision": "force_ask",
                    "reason": "safety-guard received invalid JSON payload; requesting confirmation.",
                },
            )
            sys.stdout.write(json.dumps(out) + "\n")
            return code

    output, exit_code = dispatch_payload(args.agent, args.hook, raw_payload)
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
