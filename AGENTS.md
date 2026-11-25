# Global Agent Rules (`~/.agents/AGENTS.md`)

Shared across all AI coding agents (`agy`, `opencode`, Claude Code, Codex, etc.).

## Communication & Execution
- Respond in the same language as the user (usually PT-BR), keeping code, commits, file names, and technical identifiers in English unless requested otherwise.
- Be concise, direct, and factual. Always verify changes with tests or commands before concluding.
- Avoid emojis in Markdown documentation (`README.md`, guides, `AGENTS.md`, etc.) — keep headings, callouts, and lists clean and text-only unless explicitly requested.
- Write primary Markdown documentation (`README.md`, guides, `AGENTS.md`, etc.) in English, and provide Portuguese versions in separate `*.pt-BR.md` files (e.g., `README.pt-BR.md`) linked at the top.
- Prefer CLI tools already installed (`gh`, `gcloud`, `nix`, `uv`, `rg`, `fd`) over heavy MCP servers when both can solve the task.

## Long-Term Memory & Cross-Agent Continuity
- Never rely on chat history alone for durable project knowledge or state.
- Persist important project context in versioned Markdown files inside the workspace:
  - `AGENTS.md` — concise project architecture, rules, and folder map.
  - `PROGRESS.md` — current status, milestones, and open questions.
  - `HANDOFF.md` — compact session handoff (goal, completed work, files changed, next steps) when switching between agents (e.g., `agy` ↔ `opencode`).
- When resuming work in a project, check `HANDOFF.md`, `PROGRESS.md`, and `git status` first.

## Dotfiles & Nix Conventions (`~/.config/home-manager`)
- Nix flakes only see git-tracked files: always `git add` new files before running `./switch.sh`.
- Every module in `programs/<name>.nix` requires a matching test in `tests/programs/test_<name>.py`.
- Keep secrets in `sops-nix` (referenced by path / `{file:...}`), never hardcoded in `/nix/store`.
- Global skills live in `~/.agents/skills/<name>/SKILL.md` with directory name strictly matching the YAML frontmatter `name:` field.
- After modifying global rules or skills in `~/.agents`, commit and push the changes to `origin/main`.
