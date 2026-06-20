# TestForge v1 — Governanca do Projeto

## Pipeline Oficial

```
BMAD (Planejar)  →  GSD (Executar)  →  GIT (Versionar)
     ↓                    ↓                    ↓
  brainstorm          discuss             commit
  product-brief       plan                conventional
  arquitetura         execute             commit
                      verify              hooks
                      ship
```

## Regras de Governanca

### 1. Commits
- **Formato:** `tipo: descricao` (conventional commits)
- **Hook:** `.githooks/commit-msg` rejeita fora do padrao
- **Atomicos:** 1 mudanca logica por commit

### 2. Artefatos Obrigatorios por Feature
| Artefato | Formato | Local |
|----------|---------|-------|
| Plano | PLAN.md | `.planning/phases/{N}-{nome}/` |
| Discussao | DISCUSSION.md | `.planning/phases/{N}-{nome}/` |
| Diagrama | PlantUML `.puml` | `docs/diagramas/` |
| Testes | pytest | `tests/` |

### 3. Diagramas — Devem Espelhar o Codigo
- **C4 Context:** visao externa do sistema
- **C4 Container:** componentes internos
- **Sequencia:** fluxos principais
- **Estados:** maquinas de estado

### 4. Code Review
- `@gsd-code-reviewer` apos cada milestone
- Oracle + PromotionGate para healing suggestions

### 5. Quality Gates
| Gate | Ferramenta |
|------|-----------|
| Testes passam | `pytest tests/ -q` |
| Pipeline E2E | `python scripts/test_all.py` |
| Commit format | `.githooks/commit-msg` |
| Diagramas atualizados | `docs/diagramas/` |
| Sem secrets | `.githooks/pre-commit` |

---

## Estado Atual

**31 commits, 93 testes, 1876 linhas de codigo**

| Milestone | Modulo | Status |
|-----------|--------|--------|
| M1 | Fundacao + Synthetic Lab | ✓ |
| M2 | Recorder + Asserts | ✓ |
| M3 | Evidence Collector + Store | ✓ |
| M4 | MIS + Compiler | ✓ |
| M5 | Oracle + PromotionGate | ✓ |
| M6 | Taxonomia + Shadow + Fallback | ✓ |
| M7 | Metricas + Revisao | ✓ |

## Pendente (v0.2.0)

| # | Feature | Impacto |
|---|---------|---------|
| 1 | CLI `testforge` installavel | Alto |
| 2 | Pipeline `run` integrada | Alto |
| 3 | Demo healing real (record → break → heal) | Alto |
| 4 | Prompt pack para GSD sprints | Medio |
