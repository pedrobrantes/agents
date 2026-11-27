# Hooks de Ciclo de Vida Cross-Agent

[English version](./README.md)

Hooks de ciclo de vida agnosticos de agente implementados em Python 3 stdlib (zero dependencias externas), com adaptadores finos de protocolo para Antigravity (`agy`), Claude Code e Gemini CLI.

## Arquitetura

- `dispatch.py`: Entrypoint unico (`--agent agy|claude|gemini --hook <name>`).
- `adapters/`: Tradutores de protocolo (`agy.py`, `claude.py`, `gemini.py`).
- `core/`: Logica e politicas compartilhadas:
  - `safety.py`: Espelha a denylist de `~/.config/home-manager/programs/opencode.nix`, detecta segredos hardcoded em escritas/edicoes e exige `force_ask` em pushes/deploys. Falha fechado (`force_ask`) em caso de erro interno.
  - `token_guard.py` + `compact_cmd.py`: Bloqueia leitura de pastas de build/cache/lockfiles, barra comandos explosivos e envolve comandos verbosos simples (`pytest`, `cargo test`, `go test`, `npm test`, `git diff`, `nix flake check`) com um compactador estilo RTK.
  - `engineering.py`: Garante prontidao de Nix flakes (`git add` e `tests/programs/test_<name>.py` antes de `./switch.sh`) e documentacao Markdown sem emojis.
  - `auto_format.py`: Formatador silencioso por arquivo no `PostToolUse` (timeout <2s, zero tokens).
  - `audit.py` + `stats.py`: Log JSONL com redacao de segredos e estimativa de tokens em `~/.local/share/agent-hooks/` (retencao de 30 dias).
  - `session_start.py`: Injeta contexto enxuto de repositorio e handoff com teto de 30 linhas (~400 tokens).
  - `stop_gate.py`: Gate leve de lint e higiene sobre o `git diff` no `Stop` (protegido por `continuationActive`, no maximo 1x por turno).
  - `notify_handoff.py`: Notificacoes desktop (`notify-send`) e snapshots determinísticos de auto-handoff sem criar arquivos untracked em repositorios.

## Uso

Consultar telemetria local:

```bash
python3 ~/.agents/hooks/stats.py --days 7
```

Executar testes unitarios:

```bash
pytest ~/.agents/hooks/tests -q
```

Variaveis de ambiente opcionais:
- `AGENT_HOOKS_DISABLE_COMPACT=1`: Desativa a compactacao de saida de comandos.
- `AGENT_HOOKS_DISABLE_NOTIFY=1`: Desativa notificacoes desktop.
- `ALLOW_MD_EMOJI=1`: Permite emojis em arquivos Markdown.
