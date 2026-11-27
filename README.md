# AI Agent Skills, Rules, and Hooks

[Versao em Portugues (PT-BR)](./README.pt-BR.md)

This repository stores shared skills, global rules, lifecycle hooks, and templates for AI coding agents (Antigravity `agy`, opencode, Claude Code, Gemini CLI, and similar tools).

## Installation

Clone this repository into your home directory's `.agents` folder so agents can detect it automatically:

```bash
git clone https://github.com/pedrobrantes/agents.git ~/.agents
```

When using the Nix dotfiles (`~/.config/home-manager`), this is done automatically by `directories/agents.nix`.

## Structure

- **AGENTS.md**: Global rules shared by all agents (symlinked into `~/.gemini/AGENTS.md` and `~/.config/opencode/AGENTS.md`).
- **skills/**: Individual skill definitions. Each subfolder contains a `SKILL.md` whose `name:` matches the folder name.
- **hooks/**: Cross-agent lifecycle hooks (Python 3 stdlib). Safety guardrails, token-efficiency guards, output compaction, Nix/Markdown checks, auto-format, audit telemetry, session context, quality gate, and auto-handoff. See [hooks/README.md](./hooks/README.md).
- **templates/**: Reusable project templates, such as `lefthook.yml` for heavy checks kept outside the agent loop.
- **.skill-lock.json**: Lockfile for skill versions and dependencies.

## Usage

- Skills are discovered from `skills/` on demand.
- Hooks are wired per agent by thin adapters. For `agy`, `~/.config/home-manager/programs/antigravity.nix` generates `~/.gemini/config/hooks.json`.
- Inspect local hook telemetry: `python3 ~/.agents/hooks/stats.py --days 7`.
- Run hook tests: `uv run --with pytest pytest ~/.agents/hooks/tests -q`.
