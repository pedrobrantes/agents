# Cross-Agent Lifecycle Hooks

[Versao em Portugues (PT-BR)](./README.pt-BR.md)

Agent-agnostic lifecycle hooks implemented in Python 3 stdlib (zero external dependencies) with thin protocol adapters for Antigravity (`agy`), Claude Code, and Gemini CLI.

## Architecture

- `dispatch.py`: Single CLI entrypoint (`--agent agy|claude|gemini --hook <name>`).
- `adapters/`: Protocol translators (`agy.py`, `claude.py`, `gemini.py`).
- `core/`: Shared hook logic and policies:
  - `safety.py`: Mirrors `~/.config/home-manager/programs/opencode.nix` denylist, scans writes/edits for hardcoded secrets, and enforces `force_ask` on pushes/deploys. Fail-closed (`force_ask`) on internal errors.
  - `token_guard.py` + `compact_cmd.py`: Blocks reads of build/cache/lockfile trees, prevents explosive shell commands, and wraps simple verbose CLI runners (`pytest`, `cargo test`, `go test`, `npm test`, `git diff`, `nix flake check`) with an RTK-style output compactor.
  - `engineering.py`: Enforces Nix flake readiness (`git add` and `tests/programs/test_<name>.py` before `./switch.sh`) and text-only Markdown docs.
  - `auto_format.py`: Silent single-file formatter on `PostToolUse` (<2s timeout, zero tokens).
  - `audit.py` + `stats.py`: Redacted JSONL audit log with estimated token counts in `~/.local/share/agent-hooks/` (30-day retention).
  - `session_start.py`: Injects compact workspace/handoff context capped at 30 lines (~400 tokens).
  - `stop_gate.py`: Diff-scoped lint and hygiene gate on `Stop` (guarded by `continuationActive` so it runs at most once per turn).
  - `notify_handoff.py`: Desktop notifications (`notify-send`) and clean deterministic auto-handoff snapshots.

## Usage

Inspect local telemetry:

```bash
python3 ~/.agents/hooks/stats.py --days 7
```

Run unit tests:

```bash
pytest ~/.agents/hooks/tests -q
```

Environment overrides:
- `AGENT_HOOKS_DISABLE_COMPACT=1`: Disable command output compaction.
- `AGENT_HOOKS_DISABLE_NOTIFY=1`: Disable desktop notifications.
- `ALLOW_MD_EMOJI=1`: Allow emojis in Markdown writes/edits.
