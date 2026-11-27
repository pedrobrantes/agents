#!/usr/bin/env python3
"""Lightweight RTK-style command output compactor (Python 3 stdlib only).

Runs a shell command, preserves its exact exit code, and compacts verbose
outputs while keeping failures, tracebacks, diffs headers, and summaries.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

PASSTHROUGH_MAX_LINES = 60
PASSTHROUGH_MAX_CHARS = 4000

_TEST_CMD_RE = re.compile(r"^(?:uv\s+run\s+pytest|pytest|cargo\s+(?:test|check)|go\s+test|(?:npm|pnpm|yarn)\s+test)\b")
_GIT_DIFF_RE = re.compile(r"^git\s+diff\b")

_ERROR_LINE_RE = re.compile(
    r"(?i)(?:^FAIL\b|^FAILED\b|^ERROR\b|^E\s+|panicked at|assertion|traceback|--- FAIL:|error\[E\d+\]|warning:|short test summary)"
)
_SUMMARY_LINE_RE = re.compile(
    r"(?i)(?:(?:^|[\s,=])\d+\s+(?:passed|failed|skipped|error|warnings)\b|^test result:|^Tests:\s|^FAIL\s+\S|^ok\s+\S|^Finished\s)"
)


def compact_output(command: str, output: str, returncode: int) -> str:
    """Compact command stdout/stderr while preserving high-signal lines."""
    lines = output.splitlines()
    if len(lines) <= PASSTHROUGH_MAX_LINES and len(output) <= PASSTHROUGH_MAX_CHARS:
        return output

    cmd = command.strip()

    if _GIT_DIFF_RE.match(cmd):
        return _compact_git_diff(lines, returncode)

    if _TEST_CMD_RE.match(cmd):
        return _compact_test_output(lines, returncode)

    return _compact_generic(lines, returncode)


def _compact_test_output(lines: list[str], returncode: int) -> str:
    kept: list[str] = []
    # Keep concise header
    kept.extend(lines[:8])

    # Keep error/failure context lines (with 2 lines of trailing context)
    selected_indices: set[int] = set(range(min(8, len(lines))))
    tail_start = max(0, len(lines) - 25)
    selected_indices.update(range(tail_start, len(lines)))

    for idx, line in enumerate(lines):
        if _ERROR_LINE_RE.search(line) or _SUMMARY_LINE_RE.search(line):
            for near in range(max(0, idx - 1), min(len(lines), idx + 4)):
                selected_indices.add(near)

    sorted_idx = sorted(selected_indices)
    out: list[str] = []
    prev = -1
    omitted = 0
    for idx in sorted_idx:
        if prev != -1 and idx > prev + 1:
            gap = idx - prev - 1
            omitted += gap
            out.append(f"... [{gap} verbose lines omitted] ...")
        out.append(lines[idx])
        prev = idx
        if len(out) >= 120:
            rem = len(lines) - idx - 1
            if rem > 0:
                omitted += rem
                out.append(f"... [{rem} trailing lines omitted] ...")
            break

    out.append(f"[compact_cmd: {len(lines)} total lines, {omitted} omitted, exit={returncode}]")
    return "\n".join(out) + "\n"


def _compact_git_diff(lines: list[str], returncode: int) -> str:
    max_lines = 140
    if len(lines) <= max_lines:
        return "\n".join(lines) + "\n"

    file_headers = [ln for ln in lines if ln.startswith("diff --git ")]
    kept = lines[:max_lines]
    omitted = len(lines) - max_lines
    kept.append(f"... [{omitted} diff lines omitted across {len(file_headers)} files] ...")
    if file_headers:
        kept.append("Files in diff:")
        for hdr in file_headers[:25]:
            kept.append(f"  {hdr}")
        if len(file_headers) > 25:
            kept.append(f"  ... (+{len(file_headers) - 25} more files)")
    kept.append(f"[compact_cmd: {len(lines)} total lines, exit={returncode}]")
    return "\n".join(kept) + "\n"


def _compact_generic(lines: list[str], returncode: int) -> str:
    head = lines[:20]
    tail = lines[-35:]
    middle = lines[20:-35]
    important_mid = [ln for ln in middle if _ERROR_LINE_RE.search(ln)][:25]

    omitted = max(0, len(middle) - len(important_mid))
    out = list(head)
    if important_mid:
        out.append(f"... [{len(middle)} middle lines scanned; {len(important_mid)} error/warning lines kept] ...")
        out.extend(important_mid)
    elif omitted > 0:
        out.append(f"... [{omitted} lines omitted] ...")
    out.extend(tail)
    out.append(f"[compact_cmd: {len(lines)} total lines, {omitted} omitted, exit={returncode}]")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compact verbose CLI output")
    parser.add_argument("--cmd", required=True, help="Shell command string to execute")
    args = parser.parse_args(argv)

    proc = subprocess.run(
        args.cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    compacted = compact_output(args.cmd, proc.stdout or "", proc.returncode)
    sys.stdout.write(compacted)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
