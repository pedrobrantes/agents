"""Secret redaction helpers for audit logs and diagnostics."""

from __future__ import annotations

import re
from typing import Any

from .policy import SECRET_CONTENT_PATTERNS

_EXTRA_REDACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?([^\s'\",;}{]{8,})['\"]?"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"),
)


def redact_text(text: str) -> str:
    """Replace high-confidence secrets and bearer tokens with [REDACTED]."""
    if not text:
        return text

    out = text
    for _label, pattern in SECRET_CONTENT_PATTERNS:
        out = pattern.sub("[REDACTED]", out)

    out = _EXTRA_REDACT_PATTERNS[0].sub(r"\1=[REDACTED]", out)
    out = _EXTRA_REDACT_PATTERNS[1].sub("Bearer [REDACTED]", out)
    return out


def redact_value(value: Any, max_str_len: int = 500) -> Any:
    """Recursively redact secrets and truncate long strings for compact logs."""
    if isinstance(value, str):
        cleaned = redact_text(value)
        if len(cleaned) > max_str_len:
            return f"{cleaned[:max_str_len]}... (+{len(cleaned) - max_str_len} chars)"
        return cleaned
    if isinstance(value, dict):
        return {str(k): redact_value(v, max_str_len=max_str_len) for k, v in value.items()}
    if isinstance(value, list):
        items = [redact_value(v, max_str_len=max_str_len) for v in value[:20]]
        if len(value) > 20:
            items.append(f"... (+{len(value) - 20} items)")
        return items
    return value
