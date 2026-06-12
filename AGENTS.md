# TestForge v1 - Project AGENTS.md

## Project Overview
TestForge is an AI-driven development environment integrating OpenCode, OpenHarness, BMAD Method, and MCP infrastructure.

## Architecture
```
testforge-v1/
├── .config/opencode/     # OpenCode agent configuration
│   └── opencode.jsonc    # MCP servers, agents, permissions
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
| **File System MCP** | Mass refactoring, directory analysis | Configured |
| **Context7 MCP** | Technical documentation, reduces hallucinations | Configured |
| **Playwright MCP** | Browser automation, E2E testing | Configured |
| **Sentry MCP** | Real-time error monitoring pipeline | Configured |

To enable an MCP server, set `"enabled": true` in the MCP config section of `opencode.jsonc`.

### Agent Team:
| Agent | Role | Mode |
|-------|------|------|
| `build` | Primary development agent with auto-versioning | Primary |
| `git` | Version control guardian - ensures all code is committed | Subagent |
| `bmad` | BMAD Method agile workflows | Subagent |
| `general` | General purpose assistant | Primary |
| `explore` | Code exploration and analysis | Subagent |

---

## Development Workflow

### Iniciando uma tarefa:
1. `@bmad` para planejar com BMAD Method
2. `@build` para implementar (sempre commita ao final)
3. `@git` para verificar e commitar mudanças
4. Testar com Playwright MCP quando aplicável

### Ferramentas Disponíveis:
- **OpenHarness** (`oh`): CLI para agent harness com 43+ tools
- **BMAD Method** (`npx bmad-method`): Workflows ágeis com IA
- **MCP Servers**: File System, Context7, Playwright, Sentry

### Comandos Úteis:
```bash
opencode              # Iniciar OpenCode TUI
oh                    # Iniciar OpenHarness
npx bmad-method install  # Instalar/atualizar BMAD
```

---

## Environment Setup

### Required Tools:
- Node.js >= 20.12
- Python >= 3.10
- uv (Python package manager)
- Git

### Optional but Recommended:
- Docker (for isolated environments)
- Playwright browsers (`npx playwright install`)
