# TestForge v1 - Project AGENTS.md

## Project Overview
TestForge is an AI-driven development environment integrating OpenCode, OpenHarness, BMAD Method, GSD Core, and MCP infrastructure.

## Architecture
```
testforge-v1/
├── .config/opencode/     # OpenCode agent configuration
│   ├── opencode.jsonc    # MCP servers, agents, permissions
│   ├── agents/           # GSD Core subagents (67 agents)
│   ├── command/          # GSD Core slash commands (67 commands)
│   └── skills/           # GSD Core skills (67 skills)
├── .agents/skills/       # Custom agent skills and BMAD skills
├── .opencode/commands/   # OpenCode slash commands (BMAD)
├── .venv/                # Python venv (OpenHarness SDK)
├── _bmad/                # BMAD Method core modules
├── _bmad-output/         # BMAD artifacts (planning/implementation)
├── src/                  # Source code
├── tests/                # Test suite
├── docs/                 # Documentation
├── AGENTS.md             # This file - agent instructions
├── activate.sh           # Dev environment activation script
└── .gitignore
```

---

## CRITICAL: VERSION CONTROL POLICY

> ⚠️ **DAYS OF WORK WERE LOST BECAUSE CODE WAS NOT COMMITTED. THIS MUST NEVER HAPPEN AGAIN.**

### Mandatory Commit Rules:

1. **COMMIT AFTER EVERY FILE CHANGE.** No exceptions. After any edit, write, or code generation, you MUST commit immediately.

2. **NEVER END A SESSION WITH UNCOMMITTED CHANGES.** Always run `git status` before concluding work.

3. **ATOMIC COMMITS.** One logical change per commit with descriptive messages following conventional commits:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `refactor:` - Code refactoring
   - `docs:` - Documentation
   - `test:` - Tests
   - `chore:` - Maintenance
   - `infra:` - Infrastructure/MCP/agent config

4. **COMMIT WORKFLOW:**
   ```bash
   git add <changed-files>
   git commit -m "type: description"
   git log --oneline -1  # Verify commit succeeded
   ```

5. **PRE-PUSH VERIFICATION:**
   ```bash
   git status              # Must show clean working tree
   git log --oneline -5    # Verify recent commits
   ```

6. **INVOKE THE GIT AGENT** after any code change. Use `@git` to invoke the version control subagent which will handle commits.

### What To Do If Changes Are Lost:
1. Check `git reflog` for dangling commits
2. Check the `.trash/` directory for recent file versions
3. NEVER force push or rewrite history unless absolutely necessary

---

## MCP Infrastructure

### Active MCP Servers:
| Server | Purpose | Status |
|--------|---------|--------|
| **File System MCP** | Mass refactoring, directory analysis | Disabled (OpenCode has native tools) |
| **Context7 MCP** | Technical documentation, reduces hallucinations | **Enabled** |
| **Playwright MCP** | Browser automation, E2E testing | Disabled (enable when needed) |
| **Sentry MCP** | Real-time error monitoring pipeline | Disabled (requires credentials) |

To enable an MCP server, set `"enabled": true` in `opencode.jsonc` → `mcp` section.

---

## Agent Team

### Primary Agents:
| Agent | Role | Mode |
|-------|------|------|
| `build` | Primary development agent with auto-versioning | Primary |
| `general` | General purpose assistant | Primary |
| `explore` | Code exploration and analysis | Subagent |

### Subagents:
| Agent | Role | Mode |
|-------|------|------|
| `git` | Version control guardian - prevents code loss | Subagent |
| `bmad` | BMAD Method agile workflows | Subagent |
| `gsd-executor` | GSD plan execution with atomic commits | Subagent |
| `gsd-code-reviewer` | GSD code review | Subagent |
| `gsd-code-fixer` | GSD bug fixing | Subagent |
| `gsd-debugger` | GSD debugging sessions | Subagent |
| `gsd-codebase-mapper` | Codebase analysis and mapping | Subagent |
| `gsd-domain-researcher` | Domain and technical research | Subagent |
| `gsd-doc-writer` | Documentation writing | Subagent |
| `gsd-doc-verifier` | Documentation verification | Subagent |
| `gsd-assumptions-analyzer` | Assumptions analysis | Subagent |
| `gsd-eval-planner` | Evaluation planning | Subagent |
| `gsd-eval-auditor` | Evaluation auditing | Subagent |
| `gsd-integration-checker` | Integration verification | Subagent |
| `gsd-framework-selector` | Framework selection | Subagent |
| `gsd-ai-researcher` | AI research | Subagent |
| `gsd-advisor-researcher` | Advisory research | Subagent |
| `gsd-nyquist-auditor` | Nyquist auditing | Subagent |
| `gsd-doc-classifier` | Document classification | Subagent |
| `gsd-doc-synthesizer` | Document synthesis | Subagent |
| `gsd-intel-updater` | Intelligence updates | Subagent |

---

## Development Pipeline

### Full Workflow:
```
BMAD (Planning)              GSD Core (Execution)          Versioning
─────────────                ──────────────────            ──────────
Brainstorming                /gsd-discuss-phase            @git
  ↓                          ↓
PRD / PRFAQ                  /gsd-plan-phase
  ↓                          ↓
Architecture                 /gsd-execute-phase
  ↓                          ↓
Epics & Stories              /gsd-verify-work
  ↓                          ↓
Implementation               /gsd-ship
  ↓
Retrospective
```

### Fase 1: Planejamento (BMAD Method)
1. `@bmad` → `/bmad-brainstorming` — Gerar e organizar ideias
2. `@bmad` → `/bmad-product-brief` — Brief do produto
3. `@bmad` → `/bmad-prd` ou `/bmad-create-prd` — PRD detalhado
4. `@bmad` → `/bmad-create-architecture` — Arquitetura do sistema
5. `@bmad` → `/bmad-create-epics-and-stories` — Épicos e histórias
6. `@bmad` → `/bmad-sprint-planning` — Planejamento de sprint

### Fase 2: Execução (GSD Core Loop)
1. `/gsd-new-milestone` — Criar milestone
2. `/gsd-discuss-phase` — Capturar decisões de implementação (subagentes com contexto fresco)
3. `/gsd-plan-phase` — Pesquisar, decompor, verificar plano
4. `/gsd-execute-phase` — Executar em ondas paralelas (cada executor com 200k tokens limpos)
5. `/gsd-verify-work` — Validar o que foi construído, diagnosticar e corrigir
6. `/gsd-ship` — Criar PR, arquivar fase, repetir

### Fase 3: Versionamento (Git Guardian)
1. `@git` — Invocar após cada mudança de arquivo
2. Commits atômicos com conventional commits
3. Working tree sempre limpo ao final da sessão

---

## Comandos Principais

### GSD Core (67 commands):
| Command | Purpose |
|---------|---------|
| `/gsd-new-project` | Iniciar novo projeto GSD |
| `/gsd-new-milestone` | Criar milestone |
| `/gsd-phase` | Gerenciar fases |
| `/gsd-discuss-phase` | Discutir implementação |
| `/gsd-plan-phase` | Planejar fase |
| `/gsd-execute-phase` | Executar fase |
| `/gsd-verify-work` | Verificar trabalho |
| `/gsd-ship` | Enviar/entregar |
| `/gsd-progress` | Ver progresso |
| `/gsd-config` | Configurar GSD |
| `/gsd-code-review` | Revisão de código |
| `/gsd-debug` | Debugging |
| `/gsd-capture` | Capturar decisões |
| `/gsd-cleanup` | Limpeza |
| `/gsd-fast` | Modo rápido |
| `/gsd-explore` | Exploração |

### BMAD Method (44 commands):
| Command | Purpose |
|---------|---------|
| `/bmad-help` | Ajuda e orientação |
| `/bmad-brainstorming` | Brainstorming estruturado |
| `/bmad-create-prd` | Criar PRD |
| `/bmad-create-architecture` | Criar arquitetura |
| `/bmad-create-epics-and-stories` | Criar épicos e histórias |
| `/bmad-dev-story` | Desenvolver história |
| `/bmad-sprint-planning` | Planejar sprint |
| `/bmad-code-review` | Revisão de código |
| `/bmad-retrospective` | Retrospectiva |
| `/bmad-document-project` | Documentar projeto |
| `/bmad-ux` | Design UX |

---

## Ferramentas Disponíveis:
- **OpenHarness** (`oh`): CLI para agent harness com 43+ tools
- **BMAD Method** (`npx bmad-method`): Workflows ágeis com IA
- **GSD Core** (`npx @opengsd/gsd-core`): Pipeline Discuss→Plan→Execute→Verify→Ship
- **MCP Servers**: File System, Context7, Playwright, Sentry

### Comandos Úteis:
```bash
opencode              # Iniciar OpenCode TUI
oh                    # Iniciar OpenHarness
source activate.sh    # Ativar ambiente de desenvolvimento
npx bmad-method install  # Instalar/atualizar BMAD
npx @opengsd/gsd-core@latest --opencode --global  # Atualizar GSD Core
```

---

## Environment Setup

### Required Tools:
- Node.js >= 20.12 (installed: v24.14.0)
- Python >= 3.10 (installed: 3.13.13)
- uv (Python package manager)
- Git

### Optional but Recommended:
- Docker (for isolated environments)
- Playwright browsers (`npx playwright install`)
