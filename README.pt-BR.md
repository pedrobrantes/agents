# Skills, Regras e Hooks para Agentes de IA

[English version](./README.md)

Este repositorio guarda skills, regras globais, hooks de ciclo de vida e templates compartilhados entre agentes de IA (Antigravity `agy`, opencode, Claude Code, Gemini CLI e similares).

## Instalacao

Clone o repositorio na pasta `.agents` do seu home para que os agentes o detectem automaticamente:

```bash
git clone https://github.com/pedrobrantes/agents.git ~/.agents
```

Com os dotfiles Nix (`~/.config/home-manager`), isso e feito automaticamente por `directories/agents.nix`.

## Estrutura

- **AGENTS.md**: Regras globais compartilhadas por todos os agentes (com symlink em `~/.gemini/AGENTS.md` e `~/.config/opencode/AGENTS.md`).
- **skills/**: Definicoes de skills. Cada subpasta contem um `SKILL.md` cujo `name:` corresponde ao nome da pasta.
- **hooks/**: Hooks de ciclo de vida cross-agent (Python 3 stdlib). Guardrails de seguranca, economia de tokens, compactacao de saida, checagens Nix/Markdown, auto-format, telemetria, contexto de sessao, quality gate e auto-handoff. Veja [hooks/README.pt-BR.md](./hooks/README.pt-BR.md).
- **templates/**: Templates reutilizaveis, como `lefthook.yml` para checagens pesadas fora do loop do agente.
- **.skill-lock.json**: Lockfile de versoes e dependencias das skills.

## Uso

- Skills sao descobertas sob demanda a partir de `skills/`.
- Hooks sao conectados a cada agente por adaptadores finos. No `agy`, `~/.config/home-manager/programs/antigravity.nix` gera `~/.gemini/config/hooks.json`.
- Telemetria local dos hooks: `python3 ~/.agents/hooks/stats.py --days 7`.
- Testes dos hooks: `uv run --with pytest pytest ~/.agents/hooks/tests -q`.
