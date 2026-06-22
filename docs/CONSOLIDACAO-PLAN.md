# TestForge — Plano de Consolidação de Documentação

**Data:** 2026-06-20  
**Versão:** v0.4.0  
**Status:** Auditoria completa — Pronto para implementação

---

## 1. Resumo Executivo

A documentação do TestForge está **espalhada e redundante**:
- **23 arquivos .md** na raiz, `docs/`, e subpastas
- **Conteúdo duplicado:** BUGS.md vs docs/BUGS.md, FASE-B-PLAN.md vs FASE-B-COMPLETION-REPORT.md
- **Falta de hierarquia:** Sem índice claro, sem separação usuário vs desenvolvedor
- **Conhecimento disperso:** histórico em `docs/conhecimento_ancestral/`, outputs em `_bmad-output/`

**Objetivo:** Consolidar em estrutura clara (docs/ organizada) mantendo integridade histórica.

---

## 2. AUDITORIA — Mapa de Arquivos

### ROOT (5 arquivos)

| Arquivo | Linhas | Status | Ação |
|---------|--------|--------|------|
| `README.md` | 462 | ✅ Ativo | MANTER |
| `CHANGELOG.md` | 20 | ✅ Ativo | MANTER |
| `AGENTS.md` | 300 | ✅ Ativo (GSD) | MANTER |
| `FASE-B-PLAN.md` | 627 | ⚠️ Redundante | MOVER para .planning/ARCHIVE/ |
| `FASE-B-COMPLETION-REPORT.md` | 211 | ⚠️ Redundante | MOVER + CONSOLIDAR em docs/ARQUITETURA/FASES.md |

### DOCS — 22 arquivos ativos + histórico

#### CORE — Documentação Ativa

| Arquivo | Linhas | Tipo | Ação |
|---------|--------|------|------|
| `GUIA_TESTER.md` | 53 | User-facing | REESCREVER em docs/USER-GUIDE/GRAVAR-FLUXO.md |
| `TUTORIAL.md` | 437 | Tutorial | DIVIDIR entre docs/TUTORIAIS/ |
| `TUTORIAL-LLM-HEALING.md` | 241 | Tutorial | MOVER → docs/TUTORIAIS/05-llm-healing.md |
| `run-incremental.md` | 53 | Reference | MOVER → docs/TUTORIAIS/06-incremental-execution.md |
| `PHASE-B-RUNBOOK.md` | 311 | Reference | MOVER → docs/TUTORIAIS/09-debugging-fase-b.md |
| `BUGS.md` | 184 | Reference | CONSOLIDAR com bugs.md → docs/REFERENCIA/BUGS-KNOWNS.md |
| `DIAGRAMA-VERSIONING.md` | 157 | Reference | MOVER → docs/DIAGRAMAS/ |
| `GOVERNANCA.md` | 73 | Developer | MOVER → docs/REFERENCIA/GOVERNANCE.md |

#### FASE-A HISTÓRICO — 14 arquivos

| Arquivo | Linhas | Ação |
|---------|--------|------|
| `BUG-FIX-PLAN.md` | 381 | MOVER para .planning/ARCHIVE/ |
| `BUG-FIX-PLAN-v2.md` | 615 | MOVER para .planning/ARCHIVE/ |
| `PLANO-DE-TESTE.md` | 744 | MOVER para .planning/ARCHIVE/ |
| `PLANO-TESTE-INTENT-LAB.md` | 274 | MOVER para .planning/ARCHIVE/ |
| `SPRINT-REVIEW.md` | 283 | MOVER para .planning/ARCHIVE/ |
| `SPRINT-REVIEW-SLIDES.md` | 303 | MOVER para .planning/ARCHIVE/ |
| `PRESERVACAO-CONHECIMENTO.md` | 80 | MOVER → docs/PESQUISA/PRESERVED-INTENT.md |
| `ANALISE-LLM.md` | 333 | MOVER → docs/PESQUISA/ANALISE-LLM.md |
| `testforge_plano_sprints_intent_readiness.md` | 935 | MOVER para .planning/ARCHIVE/ |
| `testforge_plano_consolidado_2026-06-16.md` | 798 | MOVER para .planning/ARCHIVE/ |
| `plano-de-teste-recorder.md` | 139 | MOVER para .planning/ARCHIVE/ |
| `2026-06-18-registro-diario.md` | 292 | MOVER para .planning/ARCHIVE/ |
| `bugs.md` | 1713 | CONSOLIDAR em BUGS-KNOWNS.md, depois DELETAR |

---

## 3. REDUNDÂNCIAS CRÍTICAS

### Redundância #1: BUGS.md + bugs.md

- `BUGS.md`: Sumário limpo (184 linhas)
- `bugs.md`: Log detalhado (1713 linhas)
- **Problema:** Duplicação, lowercase confunde

**Solução:** 
```
docs/REFERENCIA/BUGS-KNOWNS.md ← consolidar ambos
├── Seção 1: Resumo por Família (de BUGS.md)
├── Seção 2: Bugs Corrigidos (de bugs.md sumário)
└── Seção 3: Logs Completos (referência para bugs.md histórico)
```

### Redundância #2: FASE-B-PLAN.md vs FASE-B-COMPLETION-REPORT.md

- `FASE-B-PLAN.md` (627 linhas): Plano inicial
- `FASE-B-COMPLETION-REPORT.md` (211 linhas): Implementação

**Solução:**
```
docs/ARQUITETURA/FASES.md ← merge de:
├── Objetivo (de PLAN)
├── Entradas/Saídas (de PLAN)
├── 6 PRs Implementadas (de REPORT)
├── Testes (de ambos)
└── Status: Concluída
```

### Redundância #3: 3 TUTORIAL*.md + run-incremental.md

- `TUTORIAL.md`: Manual de componentes
- `TUTORIAL-LLM-HEALING.md`: Healing com LLM
- `run-incremental.md`: Executor passo a passo

**Solução:**
```
docs/TUTORIAIS/
├── 01-setup-ambiente.md (novo)
├── 02-gravar-seu-primeiro-teste.md (de GUIA + TUTORIAL)
├── 03-compilar-executar.md (novo)
├── 04-healing-deterministico.md (novo)
├── 05-llm-healing.md (de TUTORIAL-LLM-HEALING.md)
├── 06-incremental-execution.md (de run-incremental.md)
└── [mais]
```

### Redundância #4: GOVERNANCA.md vs AGENTS.md

- `GOVERNANCA.md`: Governance rules
- `AGENTS.md`: Tem mesma governance + instruções GSD

**Solução:**
- AGENTS.md fica em root (obrigatório)
- GOVERNANCA.md → docs/REFERENCIA/GOVERNANCE.md com link de volta

---

## 4. ESTRUTURA NOVA

```
docs/
├── INDEX.md ......................... índice navegável
├── OVERVIEW.md ...................... visão geral para novo visitante
│
├── USER-GUIDE/
│   ├── QUICK-START.md
│   ├── GRAVAR-FLUXO.md (de GUIA_TESTER + TUTORIAL)
│   └── TROUBLESHOOTING.md
│
├── TUTORIAIS/
│   ├── 01-setup-ambiente.md
│   ├── 02-gravar-seu-primeiro-teste.md
│   ├── 03-compilar-executar.md
│   ├── 04-healing-deterministico.md
│   ├── 05-llm-healing.md (move)
│   ├── 06-incremental-execution.md (move)
│   ├── 07-data-driven-testing.md
│   └── 08-modo-piloto.md
│
├── ARQUITETURA/
│   ├── FASES.md (consolidar FASE-B)
│   ├── FLUXO-SEMANTIC-MIS.md
│   ├── HEALING-L0-L3.md
│   ├── INTENT-RECONSTRUCTION.md
│   ├── FIELD-VALUES-MAPPING.md
│   └── ORACLE-PROMOTION-GATE.md
│
├── REFERENCIA/
│   ├── CLI.md (de README § Comandos)
│   ├── BUGS-KNOWNS.md (consolidar BUGS.md + bugs.md)
│   ├── GLOSSARIO.md
│   ├── GOVERNANCE.md (move GOVERNANCA.md)
│   ├── ADR-INDEX.md (novo: links aos ADRs)
│   └── STACK-TECNOLOGICO.md (de README § Stack)
│
├── DIAGRAMAS/
│   ├── DIAGRAMA-VERSIONING.md (move)
│   └── DIAGRAMA-HEALING.md (novo)
│
├── PESQUISA/
│   ├── ANALISE-LLM.md (move)
│   └── PRESERVED-INTENT.md (move PRESERVACAO-CONHECIMENTO.md)
│
└── CONSOLIDACAO-PLAN.md ........... este plano

.planning/
├── [existentes: PROJECT.md, ROADMAP.md, STATE.md, ...]
└── ARCHIVE/ (novo)
    ├── FASE-B-PLAN.md
    ├── FASE-B-COMPLETION-REPORT.md
    ├── BUG-FIX-PLAN.md
    ├── BUG-FIX-PLAN-v2.md
    ├── PLANO-DE-TESTE.md
    ├── PLANO-TESTE-INTENT-LAB.md
    ├── SPRINT-REVIEW.md
    ├── SPRINT-REVIEW-SLIDES.md
    ├── testforge_plano_*.md
    ├── plano-de-teste-recorder.md
    ├── 2026-06-18-registro-diario.md
    └── README.md (índice de arquivo)
```

---

## 5. CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Preparação (5 min)

```bash
mkdir -p docs/{USER-GUIDE,TUTORIAIS,ARQUITETURA,REFERENCIA,DIAGRAMAS,PESQUISA}
mkdir -p .planning/ARCHIVE
```

- [ ] Diretórios criados
- [ ] Commit: `docs: create directory structure for consolidation`

### Fase 2: Consolidação de Duplicatas (20 min)

- [ ] Criar `docs/REFERENCIA/BUGS-KNOWNS.md` (merge BUGS.md + bugs.md)
- [ ] Criar `docs/ARQUITETURA/FASES.md` (consolidar FASE-B-PLAN + REPORT)
- [ ] Criar `docs/REFERENCIA/GOVERNANCE.md` (move GOVERNANCA.md)
- [ ] Commit: `docs: consolidate duplicate documentation`

### Fase 3: Mover Documentação Ativa (15 min)

```bash
mv docs/TUTORIAL-LLM-HEALING.md docs/TUTORIAIS/05-llm-healing.md
mv docs/run-incremental.md docs/TUTORIAIS/06-incremental-execution.md
mv docs/PHASE-B-RUNBOOK.md docs/TUTORIAIS/09-debugging-fase-b.md
mv docs/DIAGRAMA-VERSIONING.md docs/DIAGRAMAS/
```

- [ ] Documentação ativa movida
- [ ] Commit: `docs: move active documentation to TUTORIAIS/`

### Fase 4: Reescrever Documentação de Usuário (15 min)

- [ ] Reescrever `docs/USER-GUIDE/GRAVAR-FLUXO.md` (GUIA_TESTER + TUTORIAL)
- [ ] Commit: `docs: rewrite user guide for clarity`

### Fase 5: Arquivar Histórico (15 min)

```bash
mv docs/BUG-FIX-PLAN.md .planning/ARCHIVE/
mv docs/BUG-FIX-PLAN-v2.md .planning/ARCHIVE/
mv docs/PLANO-*.md .planning/ARCHIVE/
# [etc: mover 12 arquivos]
mv FASE-B-PLAN.md FASE-B-COMPLETION-REPORT.md .planning/ARCHIVE/
```

- [ ] Histórico arquivado
- [ ] Commit: `docs: archive phase-a planning documents`

### Fase 6: Criar Índices (20 min)

- [ ] Criar `docs/INDEX.md` com mapa navegável
- [ ] Criar `docs/OVERVIEW.md` com visão geral
- [ ] Criar `docs/REFERENCIA/ADR-INDEX.md` com links aos ADRs
- [ ] Commit: `docs: create navigation indexes`

### Fase 7: Validação (10 min)

- [ ] Testar links em INDEX.md (buscar 404s)
- [ ] Verificar que README.md aponta para docs/INDEX.md
- [ ] Verificar que .planning/ARCHIVE/README.md existe
- [ ] `git log` confirmar commits lógicos

---

## 6. DELETÁVEIS COM SEGURANÇA

```bash
# Após consolidação:
rm docs/bugs.md                                    # conteúdo em BUGS-KNOWNS.md
rm docs/GOVERNANCA.md                              # conteúdo em docs/REFERENCIA/GOVERNANCE.md
rm docs/GUIA_TESTER.md                             # conteúdo em USER-GUIDE/
rm docs/TUTORIAL.md                                # conteúdo em TUTORIAIS/
rm docs/ANALISE-LLM.md                             # conteúdo em PESQUISA/
rm docs/PRESERVACAO-CONHECIMENTO.md                # conteúdo em PESQUISA/
rm _bmad-output/brainstorming/*
rmdir _bmad-output/
```

---

## 7. EXEMPLO: docs/INDEX.md

```markdown
# Documentação TestForge v0.4.0

## Novo por Aqui?

[OVERVIEW.md](OVERVIEW.md) — Visão geral em 5 min

## Para Testers / Usuários

| Link | Descrição |
|------|-----------|
| [Quick Start](USER-GUIDE/QUICK-START.md) | 5 min para gravar seu 1º teste |
| [Guia Completo](USER-GUIDE/GRAVAR-FLUXO.md) | Como gravar, compilar, executar |
| [Troubleshooting](USER-GUIDE/TROUBLESHOOTING.md) | Problemas comuns |

## Tutoriais Passo a Passo

1. [Setup do Ambiente](TUTORIAIS/01-setup-ambiente.md)
2. [Seu Primeiro Teste](TUTORIAIS/02-gravar-seu-primeiro-teste.md)
3. [Compilar e Executar](TUTORIAIS/03-compilar-executar.md)
4. [Healing Determinístico](TUTORIAIS/04-healing-deterministico.md)
5. [Healing com LLM](TUTORIAIS/05-llm-healing.md)
6. [Execução Incremental](TUTORIAIS/06-incremental-execution.md)
7. [Data-Driven Testing](TUTORIAIS/07-data-driven-testing.md)
8. [Modo Piloto](TUTORIAIS/08-modo-piloto.md)

## Arquitetura (Para Desenvolvedores)

- [Fases A-D](ARQUITETURA/FASES.md) — Visão geral
- [Pipeline Semantic MIS](ARQUITETURA/FLUXO-SEMANTIC-MIS.md)
- [Healing L0→L3](ARQUITETURA/HEALING-L0-L3.md)
- [Intent Reconstruction](ARQUITETURA/INTENT-RECONSTRUCTION.md)
- [Field Values Mapping](ARQUITETURA/FIELD-VALUES-MAPPING.md)
- [Incremental Runner](ARQUITETURA/INCREMENTAL-RUNNER.md)
- [Oracle e Promotion Gate](ARQUITETURA/ORACLE-PROMOTION-GATE.md)

## Referência Rápida

- [Todos os Comandos CLI](REFERENCIA/CLI.md)
- [Bugs Conhecidos e Resolvidos](REFERENCIA/BUGS-KNOWNS.md)
- [Glossário de Termos](REFERENCIA/GLOSSARIO.md)
- [Governance e Processo](REFERENCIA/GOVERNANCE.md)
- [Decisões de Arquitetura (ADRs)](REFERENCIA/ADR-INDEX.md)
- [Stack Tecnológico](REFERENCIA/STACK-TECNOLOGICO.md)

## Pesquisa e Desenvolvimento

- [Análise de Validação LLM](PESQUISA/ANALISE-LLM.md)
- [Preservação de Contexto de Intenção](PESQUISA/PRESERVED-INTENT.md)

## Histórico

- [Planos Anteriores](.../.planning/ARCHIVE/)
- [Conhecimento Ancestral](conhecimento_ancestral/)

## Mapas de Arquivo

| Antigo | Novo | Status |
|--------|------|--------|
| `BUGS.md` | `REFERENCIA/BUGS-KNOWNS.md` | Consolidado |
| `FASE-B-PLAN.md` | `.planning/ARCHIVE/` | Arquivado |
| `TUTORIAL-LLM-HEALING.md` | `TUTORIAIS/05-llm-healing.md` | Movido |
| [mais...] | | |
```

---

## 8. MAPA DETALHADO: OLD → NEW

```
ROOT
  README.md                              → STAY
  CHANGELOG.md                           → STAY
  AGENTS.md                              → STAY
  FASE-B-PLAN.md                         → .planning/ARCHIVE/
  FASE-B-COMPLETION-REPORT.md            → .planning/ARCHIVE/ + consolidar em docs/ARQUITETURA/FASES.md

docs/
  GUIA_TESTER.md                         → reescrever em docs/USER-GUIDE/GRAVAR-FLUXO.md
  TUTORIAL.md                            → dividir em TUTORIAIS/
  TUTORIAL-LLM-HEALING.md                → docs/TUTORIAIS/05-llm-healing.md
  run-incremental.md                     → docs/TUTORIAIS/06-incremental-execution.md
  PHASE-B-RUNBOOK.md                     → docs/TUTORIAIS/09-debugging-fase-b.md
  BUGS.md                                → docs/REFERENCIA/BUGS-KNOWNS.md (consolidar)
  bugs.md                                → consolidar em BUGS-KNOWNS.md + DELETAR
  DIAGRAMA-VERSIONING.md                 → docs/DIAGRAMAS/
  GOVERNANCA.md                          → docs/REFERENCIA/GOVERNANCE.md
  ANALISE-LLM.md                         → docs/PESQUISA/ANALISE-LLM.md
  PRESERVACAO-CONHECIMENTO.md            → docs/PESQUISA/PRESERVED-INTENT.md
  BUG-FIX-PLAN.md                        → .planning/ARCHIVE/
  BUG-FIX-PLAN-v2.md                     → .planning/ARCHIVE/
  PLANO-DE-TESTE.md                      → .planning/ARCHIVE/
  PLANO-TESTE-INTENT-LAB.md              → .planning/ARCHIVE/
  SPRINT-REVIEW.md                       → .planning/ARCHIVE/
  SPRINT-REVIEW-SLIDES.md                → .planning/ARCHIVE/
  testforge_plano_consolidado_2026-06-16.md → .planning/ARCHIVE/
  testforge_plano_sprints_intent_readiness.md → .planning/ARCHIVE/
  plano-de-teste-recorder.md             → .planning/ARCHIVE/
  2026-06-18-registro-diario.md          → .planning/ARCHIVE/

DELETAR (após consolidação):
  docs/bugs.md
  _bmad-output/ (vazio)
```

---

## 9. BENEFÍCIOS DA CONSOLIDAÇÃO

| Métrica | Antes | Depois |
|---------|-------|--------|
| Docs dispersos | 23 em múltiplas pastas | 30+ em hierarquia clara |
| Redundância | BUGS.md + bugs.md, FASE-B duplicado | 1 canonical por tópico |
| Índice | Não existe | INDEX.md navegável |
| Onboarding | Novo perdido em docs/ | INDEX guia por audiência |
| Links quebrados | Comuns | Consisten + testável |
| Manutenção | Atualizar em múltiplos locais | 1 local principal |
| Histórico | Espalhado | .planning/ARCHIVE/ centralizado |

---

## 10. CONCLUSÃO

Este plano consolida **23 documentos** em **estrutura navegável** sem perder informação.

**7 fases atômicas** (Preparação → Consolidação → Limpeza → Validação), cada uma revertível via git.

**Próximo passo:** Executar Fase 1 (criar estrutura).
