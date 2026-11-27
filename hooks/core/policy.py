"""Shared security, token, and engineering policy definitions.

Mirrors the security posture in ~/.config/home-manager/programs/opencode.nix
so all AI coding agents enforce consistent guardrails.
"""

from __future__ import annotations

import re
from pathlib import Path

# Files/paths that agents must never read or modify.
SENSITIVE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|/)\.env$", re.IGNORECASE),
    re.compile(r"(^|/)\.env\.(?!example$|sample$|template$|dist$).+", re.IGNORECASE),
    re.compile(r"(^|/)id_(ed25519|rsa|ecdsa|dsa)(?!\.pub$)($|\.)", re.IGNORECASE),
    re.compile(r"(^|/)age/keys\.txt$", re.IGNORECASE),
    re.compile(r"sops-nix/secrets", re.IGNORECASE),
    re.compile(r"secrets\.d/", re.IGNORECASE),
    re.compile(r"\.(pem|p12|pfx|jks)$", re.IGNORECASE),
)

# High-confidence secret content patterns for write/edit scanning.
SECRET_CONTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"),
    ),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub classic PAT", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("Stripe live secret key", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b")),
)

SECRET_IGNORE_MARKERS: tuple[str, ...] = (
    "ENC[AES256_GCM",
    "REDACTED",
    "EXAMPLE",
    "PLACEHOLDER",
    "DUMMY",
    "YOUR_API_KEY",
    "fake_",
)

# Shell commands that are always hard-blocked (mirrors opencode.nix denylist).
DENY_SHELL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "destructive rm targeting root or home",
        re.compile(
            r"(?:^|[;&|]\s*)rm\s+(?:-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive\s+--force|--force\s+--recursive)\s+(?:/(?:\*|\s|$)|~(?:/|\*|\s|$)|\$HOME\b|\$\{HOME\})"
        ),
    ),
    (
        "force git push",
        re.compile(r"(?:^|[;&|]\s*)git\s+push\b[^\n]*(?:\s--force(?:\s|$)|\s-f(?:\s|$))"),
    ),
    (
        "git reset --hard",
        re.compile(r"(?:^|[;&|]\s*)git\s+reset\s+--hard\b"),
    ),
    (
        "git clean -fd / -fx",
        re.compile(r"(?:^|[;&|]\s*)git\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*[dx]\b"),
    ),
    (
        "privilege escalation via sudo",
        re.compile(r"(?:^|[;&|]\s*)sudo\s+"),
    ),
    (
        "sops decryption",
        re.compile(r"(?:^|[;&|]\s*)sops\s+(?:--decrypt|-d)\b"),
    ),
    (
        "GCP billing mutation",
        re.compile(r"(?:^|[;&|]\s*)gcloud\s+billing\b"),
    ),
    (
        "GCP project deletion",
        re.compile(r"(?:^|[;&|]\s*)gcloud\s+projects\s+delete\b"),
    ),
    (
        "raw disk write via dd",
        re.compile(r"(?:^|[;&|]\s*)dd\s+"),
    ),
    (
        "filesystem formatting via mkfs",
        re.compile(r"(?:^|[;&|]\s*)mkfs(?:\.[a-z0-9]+)?\b"),
    ),
)

# Shell commands that always require explicit human confirmation (force_ask).
FORCE_ASK_SHELL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "git push to remote",
        re.compile(r"(?:^|[;&|]\s*)git\s+push\b"),
    ),
    (
        "Terraform state/infra mutation",
        re.compile(r"(?:^|[;&|]\s*)terraform\s+(?:apply|destroy)\b"),
    ),
    (
        "Cloudflare Workers deploy",
        re.compile(r"(?:^|[;&|]\s*)(?:wrangler|cf)\s+deploy\b"),
    ),
    (
        "Firebase deploy",
        re.compile(r"(?:^|[;&|]\s*)firebase\s+deploy\b"),
    ),
    (
        "GCP deploy/create/delete operation",
        re.compile(r"(?:^|[;&|]\s*)gcloud\b[^\n]*\b(?:deploy|create|delete)\b"),
    ),
    (
        "Kubernetes apply/delete",
        re.compile(r"(?:^|[;&|]\s*)kubectl\s+(?:apply|delete)\b"),
    ),
)

# Directories that explode token budgets if read directly.
JUNK_DIR_SEGMENTS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        "target",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".next",
        ".nuxt",
        "result",
    }
)

# Lockfiles that should not be read in full without a narrow line range.
LOCKFILE_NAMES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "flake.lock",
        "uv.lock",
        "Cargo.lock",
        "poetry.lock",
        "composer.lock",
        "Gemfile.lock",
    }
)

MINIFIED_SUFFIXES: tuple[str, ...] = (".min.js", ".min.css", ".bundle.js", ".js.map", ".css.map")

# Maximum line span allowed when explicitly slicing a lockfile.
MAX_LOCKFILE_SLICE_LINES = 200

# Maximum line count allowed for plain `cat <file>` before redirecting to bounded read.
MAX_CAT_LINES = 500

# Data directory for audit logs & out-of-repo auto-handoff snapshots.
AGENT_HOOKS_DATA_DIR = Path.home() / ".local" / "share" / "agent-hooks"
AUDIT_RETENTION_DAYS = 30
