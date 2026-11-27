"""Stop hook: lightweight diff-scoped quality and engineering hygiene gate.

Protected by `continuation_active` so it runs at most once per turn and only
when actual git diff changes exist.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

MAX_FILE_LINES_WARNING = 600

_DEBUG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Python breakpoint/pdb", re.compile(r"\b(?:breakpoint\s*\(|pdb\.set_trace\s*\(|import\s+pdb\b)")),
    ("JS/TS debugger statement", re.compile(r"\bdebugger\s*;")),
    ("JS/TS console.log", re.compile(r"\bconsole\.log\s*\(")),
)

_CODE_EXTS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".nix"})


def _run(cmd: list[str], cwd: Path, timeout: float = 4.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, (proc.stdout + proc.stderr).rstrip("\r\n")
    except (OSError, subprocess.TimeoutExpired):
        return 0, ""


def _changed_files(repo_root: Path) -> tuple[list[str], list[str]]:
    """Return (modified_files, new_untracked_files) relative to repo_root."""
    code, out = _run(["git", "status", "--porcelain"], repo_root, timeout=2.0)
    if code != 0 or not out:
        return [], []
    modified: list[str] = []
    untracked: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        if status == "??":
            untracked.append(rel)
        elif "D" not in status:
            modified.append(rel)
    return modified, untracked


def _check_added_debug_statements(repo_root: Path, files: list[str]) -> list[str]:
    code_files = [
        f for f in files
        if Path(f).suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx"}
        and "test" not in Path(f).name.lower()
    ]
    if not code_files:
        return []

    rc, diff = _run(["git", "diff", "-U0", "--", *code_files], repo_root, timeout=2.5)
    if rc != 0 or not diff:
        return []

    findings: list[str] = []
    current_file = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        for label, pattern in _DEBUG_PATTERNS:
            if "JS/TS" in label and not current_file.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            if "Python" in label and not current_file.endswith(".py"):
                continue
            if pattern.search(added):
                findings.append(f"Debug statement ({label}) added in {current_file}")
                break
        if len(findings) >= 4:
            break
    return findings


def _check_nix_program_tests(repo_root: Path, all_files: list[str]) -> list[str]:
    if not (repo_root / "flake.nix").exists() or not (repo_root / "tests" / "programs").is_dir():
        return []
    findings: list[str] = []
    for rel in all_files:
        p = Path(rel)
        if p.parent == Path("programs") and p.suffix == ".nix" and p.name != "default.nix":
            expected = repo_root / "tests" / "programs" / f"test_{p.stem}.py"
            if not expected.exists():
                findings.append(f"Missing matching Nix test: tests/programs/test_{p.stem}.py")
    return findings


def _check_large_files(repo_root: Path, all_files: list[str]) -> list[str]:
    findings: list[str] = []
    for rel in all_files:
        p = repo_root / rel
        if p.suffix.lower() not in _CODE_EXTS or not p.is_file():
            continue
        try:
            line_count = sum(1 for _ in p.open("rb"))
        except OSError:
            continue
        if line_count > MAX_FILE_LINES_WARNING:
            findings.append(f"Large modified file ({line_count} lines > {MAX_FILE_LINES_WARNING}): {rel}")
    return findings[:3]


def _run_fast_linters(repo_root: Path, all_files: list[str]) -> list[str]:
    findings: list[str] = []

    py_files = [f for f in all_files if f.endswith(".py") and (repo_root / f).is_file()]
    if py_files and shutil.which("ruff"):
        rc, out = _run(
            ["ruff", "check", "--output-format", "concise", "--no-fix", *py_files[:20]],
            repo_root,
            timeout=4.0,
        )
        if rc != 0 and out:
            first_lines = [ln for ln in out.splitlines() if ln.strip()][:5]
            findings.append("ruff lint errors:\n  " + "\n  ".join(first_lines))

    nix_files = [f for f in all_files if f.endswith(".nix") and (repo_root / f).is_file()]
    if nix_files and shutil.which("nix-instantiate"):
        for nf in nix_files[:10]:
            rc, out = _run(["nix-instantiate", "--parse", str(repo_root / nf)], repo_root, timeout=2.5)
            if rc != 0:
                first_err = out.splitlines()[0] if out else "syntax error"
                findings.append(f"Nix syntax error in {nf}: {first_err}")

    return findings


def handle(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("continuation_active"):
        return {"decision": "allow"}
    if event.get("termination_reason") not in ("NO_TOOL_CALL", ""):
        return {"decision": "allow"}

    cwd_str = str(event.get("cwd") or "")
    if not cwd_str or not Path(cwd_str).is_dir():
        return {"decision": "allow"}

    rc, root_out = _run(["git", "rev-parse", "--show-toplevel"], Path(cwd_str), timeout=1.5)
    if rc != 0 or not root_out:
        return {"decision": "allow"}
    repo_root = Path(root_out)

    modified, untracked = _changed_files(repo_root)
    all_files = modified + untracked
    code_changed = [f for f in all_files if Path(f).suffix.lower() in _CODE_EXTS]
    if not code_changed:
        return {"decision": "allow"}

    issues: list[str] = []
    issues.extend(_run_fast_linters(repo_root, code_changed))
    issues.extend(_check_nix_program_tests(repo_root, code_changed))
    issues.extend(_check_added_debug_statements(repo_root, modified))
    issues.extend(_check_large_files(repo_root, code_changed))

    if not issues:
        return {"decision": "allow"}

    summary = "Quality/hygiene gate found issues in modified files:\n- " + "\n- ".join(issues[:8])
    return {"decision": "continue", "reason": summary}
