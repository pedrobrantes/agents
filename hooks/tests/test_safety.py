"""Unit tests for PreToolUse safety guardrails."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import safety  # noqa: E402


def _event(kind: str, *, path: str = "", content: str = "", command: str = "") -> dict:
    return {
        "agent": "agy",
        "cwd": "/tmp",
        "tool": {
            "kind": kind,
            "path": path,
            "content": content,
            "command": command,
            "args": {},
        },
    }


def test_denies_sensitive_files_on_read_and_write():
    for sensitive in (
        "/repo/.env",
        "/repo/.env.production",
        "/home/user/.ssh/id_ed25519",
        "/home/user/.ssh/id_rsa",
        "/home/user/.config/sops/age/keys.txt",
        "/run/user/1000/sops-nix/secrets/gemini_api_key",
        "/etc/secrets.d/token",
    ):
        res = safety.handle(_event("read", path=sensitive))
        assert res["decision"] == "deny", f"Expected deny for {sensitive}"


def test_allows_safe_env_example_and_public_keys():
    assert safety.handle(_event("read", path="/repo/.env.example"))["decision"] == "allow"
    assert safety.handle(_event("read", path="/home/user/.ssh/id_ed25519.pub"))["decision"] == "allow"


def test_denies_hardcoded_secrets_on_write():
    fake_aws = "AKIA" + "9876543210ABCDEF"
    res = safety.handle(_event("write", path="/repo/config.py", content=f"KEY = '{fake_aws}'\n"))
    assert res["decision"] == "deny"

    # Encrypted sops or placeholder markers are allowed.
    res_sops = safety.handle(
        _event("write", path="/repo/secrets.yaml", content=f"key: ENC[AES256_GCM,data:{fake_aws}]\n")
    )
    assert res_sops["decision"] == "allow"

    res_example = safety.handle(
        _event("write", path="/repo/docs.md", content="KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
    )
    assert res_example["decision"] == "allow"


def test_denies_destructive_shell_commands():
    for cmd in (
        "rm -rf /",
        "rm -rf ~/*",
        "git push --force origin main",
        "git push -f origin main",
        "git reset --hard HEAD~1",
        "git clean -fd",
        "sudo apt update",
        "sops --decrypt secrets.yaml",
        "gcloud billing accounts list",
        "gcloud projects delete my-proj",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sdb1",
        "cat .env",
    ):
        res = safety.handle(_event("shell", command=cmd))
        assert res["decision"] == "deny", f"Expected deny for: {cmd}"


def test_force_asks_on_push_and_deploy():
    for cmd in (
        "git push origin main",
        "terraform apply",
        "wrangler deploy",
        "firebase deploy",
        "gcloud run deploy my-svc",
        "kubectl apply -f deploy.yaml",
    ):
        res = safety.handle(_event("shell", command=cmd))
        assert res["decision"] == "force_ask", f"Expected force_ask for: {cmd}"


def test_allows_safe_shell_commands():
    for cmd in ("git status -sb", "rg foo src/", "uv run pytest -q", "nix flake check"):
        res = safety.handle(_event("shell", command=cmd))
        assert res["decision"] == "allow", f"Expected allow for: {cmd}"
