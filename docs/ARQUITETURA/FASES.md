# TestForge — Visão Geral das Fases A-D

**Versão:** 0.4.2  
**Última atualização:** 2026-06-30  
**Status:** Fase A concluída, Fase B implementada, Fase C/D em progresso, Sprint 0 concluído (Diagnostic Mode + 30+ hotfixes), ComponentHandler system implementado (Sprints 1-6), Architecture v2 (Phases 1-7)

---

## Resumo Executivo

O TestForge é estruturado em **4 fases sequenciais**:

| Fase | Objetivo | Status | Entrada | Saída |
|------|----------|--------|---------|-------|
| **A** | **Recorder** — Capturar intenção do usuário via eventos brutos | ✅ Concluída | Browser + usuário | raw_events.jsonl + snapshots |
| **B** | **Intent Reconstructor** — Normalizar eventos em `SemanticTestCase` | ✅ Implementada | raw_events + evidência | SemanticTestCase + field_values |
| **C** | **Compiler** — Gerar código Playwright executável | ⏳ Em progresso | SemanticTestCase | script.py + test runner |
| **D** | **Executor + Healer** — Executar testes com self-healing L0-L3 | 🎯 Planejada | script.py + SPA | execution_report + healing_metrics |

---

## 📍 Fase A: Recorder (Concluída)

### Objetivo

Gravar a intenção do usuário durante navegação em SPA, capturando:
- Cliques, preenchimentos, seleções
- Submits e navegações
- Estado visual (screenshots, DOM snapshots)
- Evidência (logs de rede, console, estado de formulário)

### Entradas

- Browser (Playwright)
- Navegação interativa do usuário
- URLs da aplicação

### Saídas

1. **raw_events.jsonl** — Eventos brutos (click, fill, submit, navigate)
2. **steps.jsonl** — Steps manuais curados (opcional)
3. **field_snapshots.jsonl** — Snapshots de campo em tempo real
4. **value_mutations.jsonl** — Setter hooks e mutações JS
5. **network_log.json** — Requisições POST/PUT com payloads
6. **dom_snapshots/** — HTML snapshots antes/depois de ações
7. **final_state_snapshot.json** — Estado final de todos os campos

### Estatísticas (v0.4.2)

- **Testes gravados:** 800+
- **Taxa de passa:** 100%
- **Famílias cobertas:** 11/11 (FAM-01 a FAM-11)
- **Keywords de classificação:** 51
- **Novo:** Diagnostic Mode (Sprint 0) — coleta de telemetria QA
- **Novo:** Architecture v2 (Phases 1-7) — tracing, CDP, v2 locator, resolver, SQLite, P&F, telemetry
- **Novo:** 30+ hotfixes — recorder, normalizer, runner, CLI, publisher, diagnostic, healing

### Bugs Conhecidos

Veja [Bugs Conhecidos](../REFERENCIA/BUGS-KNOWNS.md) para lista completa.

**Sprint 0 (30+ bugs corrigidos):** Veja [CHANGELOG v0.4.2](../CHANGELOG.md) para lista completa.

---

## 🔄 Fase B: Intent Reconstructor (Implementada)

### Objetivo

Transformar eventos brutos em `SemanticTestCase` estruturado, fechando gaps onde a intenção era perdida entre clique e submit.

### Arquitetura

```
raw_events.jsonl
    ↓
[5 Estratégias de Reconstrução]
    ├── 1. Setter hooks (value_mutations.jsonl)
    ├── 2. Snapshot diff (field_snapshots.jsonl)
    ├── 3. Checked transitions (radio/checkbox)
    ├── 4. Network payload (POST/PUT analysis)
    └── 5. Final state (fallback)
    ↓
[Dedup + Priority ordering]
    ↓
field_values: dict[field_key → FieldValueMap]
    ↓
SemanticTestCase (YAML)
    ├── steps: [lista de ações normalizadas]
    ├── field_values: [mapa campo → fonte de evidência]
    ├── blind_spots: [padrões onde intenção foi perdida]
    └── metadados (test_id, source_recording_id, base_url)
```

### Entradas (de Fase A)

1. **raw_events.jsonl** — eventos brutos
2. **value_mutations.jsonl** — setter hooks (JS mutações)
3. **field_snapshots.jsonl** — snapshots antes/depois
4. **network_log.json** — payloads POST/PUT
5. **final_state_snapshot.json** — estado final

### Saídas

1. **SemanticTestCase** (YAML)
   - `steps`: ações normalizadas (click, fill, assert, select_option)
   - `field_values`: mapa campo → {value, source, confidence, is_masked}
   - `blind_spots`: [padrões de intenção perdida]
   - `completeness_score`: 0.0-1.0 (gate ≥ 0.70)

2. **IntentCompletenessValidator** — Gate de qualidade
   - Score = resolved_fields / total_fields
   - Bloqueador: score < 0.70 impede promoção para Fase C

### PRs Implementados (6 PRs)

#### PR 1 — Compiler `field_values` passthrough

Integração `PlaywrightCompiler` ↔ `FieldValueMap`.

**O que foi feito:**
- Parâmetro `field_values: dict[str, FieldValueMap]` adicionado ao `compile()`
- Parâmetro `data_file_dict` para injeção externa via `--data JSON`
- Valores do `FieldValueMap` substituem `step.value` nos `fill()` gerados

**Arquivo:** `src/testforge/semantic/compiler.py`

---

#### PR 2 — `IntentCompletenessValidator` (Gate 0.70)

Validação de completude antes de promoção para Fase C.

**O que foi feito:**
- `validate()` — calcula score por SemanticTestCase
- Score = `campos_resolvidos / total_campos` (0.0-1.0)
- Gate: score < 0.70 reprova promoção
- Relatório: `missing_fields`, `blind_spots_count`, `reason`

**Arquivos:** 
- `src/testforge/validation/intent_completeness.py`
- `src/testforge/validation/__init__.py`

---

#### PR 3 — Polling strategy + Detecção de campo mascarado

Novas estratégias de reconstrução.

**O que foi feito:**
- `_reconstruct_from_polling()` — lê entradas `"polling"` do field_snapshots.jsonl
- Heurísticas de campo mascarado: moeda, CPF, CNPJ, telefone, data
- Flag `is_masked` propagada para identifiers
- Score de prioridade para polling: 50 (abaixo de final_state = 55)

**Arquivo:** `src/testforge/semantic/intent_reconstructor.py`

---

#### PR 4 — Network URL fallback + Confidence score

Melhoria na correlação de payload de rede.

**O que foi feito:**
- `_correlate_payload_key()` — fallback por URL quando sem timestamp
- Confidence score em identifiers:
  - 1.0 para match direto por nome
  - 0.6 para match via URL fallback
- `docs/PHASE-B-RUNBOOK.md` — guia de debugging
- `README.md` — diagrama do pipeline

**Arquivos:** 
- `src/testforge/semantic/intent_reconstructor.py`
- `docs/PHASE-B-RUNBOOK.md`
- `README.md`

---

#### PR 5 — Suite de validação E2E

Testes de integração de ponta a ponta.

**O que foi feito:**
- `tests/test_phase_b_e2e_validation.py` — batch normalize gravações
- `tests/test_phase_b_compiler_e2e.py` — compilação de gravações
- Cobertura de field_values e blind_spots

**Arquivos criados:**
- `tests/test_phase_b_e2e_validation.py`
- `tests/test_phase_b_compiler_e2e.py`

---

#### PR 6 — Documentação de conclusão

Artefatos de fechamento da Fase B.

**O que foi feito:**
- `FASE-B-COMPLETION-REPORT.md` — este documento
- `adrs/ADR-006-phase-b-evidence-consumption.md` — ADR formal

---

### Gaps Fechados

| Gap | Prioridade | Status |
|-----|-----------|--------|
| Compiler `field_values` passthrough | P1 (crítico) | ✅ Fechado |
| Intent completeness gate 0.70 | P2 | ✅ Fechado |
| Polling strategy | P2 | ✅ Fechado |
| Masked field heuristics | P2 | ✅ Fechado |
| Network URL fallback | P2 | ✅ Fechado |
| Network confidence score | P2 | ✅ Fechado |

### Métricas (Fase B)

| Métrica | Valor |
|---------|-------|
| Testes pré-PRs 1-5 | 741 |
| Testes passando | 563 |
| Testes adicionados (PRs 1-5) | ~60 |
| Testes Fase B específicos (final) | 136 |

### Módulos Atualizados

| Módulo | Estratégias adicionadas |
|--------|------------------------|
| `IntentReconstructor` | polling, masked field heuristics, URL fallback, confidence score |
| `PlaywrightCompiler` | field_values passthrough, data_file_dict injection |
| `IntentCompletenessValidator` | scoring completo + gate 0.70 |

---

## 🎬 Fase C: Compiler (Em Progresso)

### Objetivo

Compilar `SemanticTestCase` em código Playwright executável, com suporte a field_values e data files.

### Entradas (de Fase B)

1. **SemanticTestCase** (YAML) — steps + field_values
2. **--data JSON** (opcional) — dados externos para missing_fill
3. **--headless flag** (configurável)

### Saídas

1. **script.py** — Código Playwright executável
   - Função de teste nomeada por test_id
   - Steps compilados em Playwright API
   - Field values injetados nos `fill()` correspondentes
   - Fallback para `data_file_dict` se field_value vazio

2. **test_runner.py** — Executável com CLI
   - `--recording X` — execute teste X
   - `--headless` — rodar em background
   - `--data file.json` — injetar dados externos
   - Saída: `execution_report.json`

### Roadmap Fase C

- [ ] Integração completa com Fase B SemanticTestCase
- [ ] Suporte a data files (`--data`)
- [ ] Geração de assertions robustas (semânticas, não estruturais)
- [ ] Tratamento de waiters (esperas por navegação, estado, etc)
- [ ] CLI: `compile`, `run`, `debug`

---

## ⚙️ Fase D: Executor + Healer (Planejada)

### Objetivo

Executar testes compilados contra SPA real com self-healing automático (L0-L3).

### Arquitetura de Healing

```
STEP EXECUTION
    ↓
[L0: Retry simples]
    ├─ Timeout simples? → wait_for_selector + retry
    ├─ Stale element? → refind element + retry
    
[L1: Classifier + Agent roteamento]
    ├─ Erro? → Classify (FAM-01 a FAM-11)
    ├─ Route para Agent (SelectorAgent, TimingAgent, etc)
    
[L2: Healing proposal]
    ├─ Agent propõe novo seletor, estratégia, ou ação
    ├─ step_runner aplica proposta
    
[L3: Oracle + Validation (futuro)]
    ├─ Oracle valida resultado do healing
    ├─ Armazena em healing_report.md

Healing Metrics
    └─ healings_tentados, aplicados, validados
    └─ Relatório: true_heals vs false_heals
```

### Entradas (de Fase C)

1. **script.py** — Código compilado
2. **SPA em execução** — aplicação web alvo
3. **Evidence package** (opcional) — screenshots, DOM snapshots

### Saídas

1. **execution_report.json**
   - `steps_total`, `steps_passed`, `steps_failed`
   - `steps_healed`: quantos falharam mas foram curados
   - `healing_metrics`: precision, recall, F1-score

2. **healing_report.md**
   - Detalhes de cada step curado
   - Propostas aceitas vs rejeitadas
   - Reasoning do healing

3. **Artefatos de debug**
   - Screenshots de failures
   - DOM diffs antes/depois
   - Logs de healing por step

### 🔬 Diagnostic Mode (Sprint 0 — v0.4.2)

Modo standalone de coleta de telemetria para equipes de QA. Ativado via:
```bash
testforge record --diagnostic-mode <url>
# ou
testforge diagnose <url>
```

**Componentes em `src/testforge/diagnostic/`:**
- `framework_detector.py` — A3 CDP bundle analysis + A4 window/DOM/custom-elements
- `capture_quality.py` — value_kind regex, framework_signal, blind_spots
- `replay_check.py` — immediate (B1) ou batched (B4) Locator probe
- `gherkin_writer.py` — live `scenario.feature` (pt-BR)
- `telemetry_store.py` — JSONL primary + OTel spans (E4)
- `session.py` — DiagnosticSession orchestrator

**Publisher:** Azure DevOps (G4 + Z1+Z5) via `src/testforge/publisher/azure_devops.py`

### 🏗️ Architecture v2 (Phases 1-7)

Feature-flagged migration. Todas as mudanças são aditivas.

| Phase | Componente | Opt-in |
|-------|-----------|--------|
| 1 | Playwright tracing + CDP AX-tree (parallel) | `--use-cdp-recorder` |
| 2 | v2 LocatorExtractor + Playwright codegen + intent | `use_v2_locator=True` |
| 3 | LocatorResolver + step API + v2 compiler | `--use-v2-compiler` |
| 4 | SQLite intent-keyed catalog + persistent L0 | `sqlite_catalog=...` |
| 5 | Pipes & Filters pipeline (4 extracted stages) | `use_pipeline=True` |
| 6 | Zero-dep tracer + static dashboard.html | `TESTFORGE_TRACING=0` |
| 7 | YAML-driven ComponentResolver | `ComponentResolver()` |

### 🧩 ComponentHandler System (v0.4.1)

Sistema de handlers para componentes de UI framework-specific (Angular Material, PrimeFaces, React MUI).

#### Arquitetura

```
src/testforge/handlers/
├── __init__.py              # Registry + detect_handler()
├── component_handler.py     # Abstract base class (ABC)
├── cdk_overlay.py           # Shared CDK overlay utilities
├── angular_material.py      # mat-select, mat-autocomplete, mat-dialog,
│                            # mat-tab-group, mat-slide-toggle
├── primeFaces.py            # Skeleton (detect only)
└── react_mui.py             # Skeleton (detect only)
```

#### Interface ComponentHandler

| Método | Quando chamado | Retorno |
|--------|---------------|---------|
| `detect(candidates, element_id, tag)` | Antes de cada step | `bool` — handler é dono deste step? |
| `normalize(steps)` | Durante normalização (in-place) | `None` — colapsa/dedup steps |
| `execute(page, step)` | Durante execução | `str` — selector usado |
| `heal(evidence, error)` | Se step falhou | `Optional[LLMHealingProposal]` |

#### Registry (ordem importa)

```python
HANDLERS: list[ComponentHandler] = [
    AngularMaterialHandler(),  # mat-* selectors sao unambiguous
    PrimeFacesHandler(),       # ui-* class names sao PF-specific
    ReactMUIHandler(),
]

def detect_handler(step) -> ComponentHandler | None:
    """Primeiro handler que reivindica ownership do step target."""
```

#### Sprints Implementados

| Sprint | Componente | Status |
|--------|-----------|--------|
| **Sprint 1** | Foundation + mat-select (LAB-11) | ✅ |
| **Sprint 2** | mat-autocomplete + keypress→fill collapse (LAB-12) | ✅ |
| **Sprint 3** | mat-dialog + mat-tab-group + mat-slide-toggle (LAB-13, LAB-14) | ✅ |
| **Sprint 4** | Normalizer migration — `_dedup_datepicker_sequences` → `handler.normalize()` | ✅ |
| **Sprint 5** | PrimeFaces handler skeleton (LAB-15) | ✅ |
| **Sprint 6** | React MUI handler skeleton (LAB-16) | ✅ |

#### Fluxo de Delegacao

```
Step
  ↓
detect_handler(step)
  ├─ AngularMaterialHandler → handler.execute()
  │   ├─ mat-select: click → wait overlay → find option → click → close
  │   ├─ mat-autocomplete: fill → wait options → select match
  │   ├─ mat-dialog: detect dialog context → scope selectors
  │   ├─ mat-tab: click tab → wait panel
  │   └─ mat-slide-toggle: click → read aria-checked
  ├─ PrimeFacesHandler → stub (NotImplementedError → fallback)
  ├─ ReactMUIHandler → stub (NotImplementedError → fallback)
  └─ None → fallback Playwright padrao
```

### Estratégias de Healing

| Estratégia | Quando usar | Status |
|-----------|------------|--------|
| `visibility_wait` | Elemento fora de tela | ✅ Implementada |
| `press_sequentially` | Masked input (CPF, moeda) | ✅ Implementada |
| `overlay_dismiss` | Popup/modal cobrindo elemento | ✅ Implementada |
| `dialog_handler` | Alert/confirm | ✅ Implementada |
| `iframe_switch` | Elemento dentro de iframe | ✅ Implementada |
| `synthetic_click` | Click via JS | ✅ Implementada |
| `label_click` | Clica em label (radio/checkbox) | ✅ Implementada |
| `semantic_locator_conversion` | Novo seletor proposto | ✅ Implementada |
| `has_text_fallback` | Seletor por texto/conteúdo | ✅ Implementada |
| `xpath_fallback` | Fallback via XPath | ✅ Implementada |

---

## 🗂️ Estrutura de Arquivos

```
testforge/
├── src/testforge/
│   ├── handlers/               # [v0.4.1] ComponentHandler system
│   │   ├── __init__.py         # Registry + detect_handler()
│   │   ├── component_handler.py   # ABC
│   │   ├── component_resolver.py  # [v2 P7] YAML-driven
│   │   ├── cdk_overlay.py      # CDK overlay utilities
│   │   ├── angular_material.py # mat-select, autocomplete, dialog, etc
│   │   ├── primeFaces.py       # Skeleton
│   │   └── react_mui.py        # Skeleton
│   │
│   ├── diagnostic/             # [v0.4.2] Sprint 0 — Diagnostic Mode
│   │   ├── framework_detector.py
│   │   ├── capture_quality.py
│   │   ├── replay_check.py
│   │   ├── gherkin_writer.py
│   │   ├── telemetry_store.py
│   │   └── session.py
│   │
│   ├── recorder/
│   │   ├── overlay_inject.js       # [v0.4.2] JS overlay extraído
│   │   ├── tracing_manager.py      # [v2 P1] Playwright tracing
│   │   ├── cdp_snapshot.py         # [v2 P1] CDP AX-tree
│   │   ├── recorder_controller.py
│   │   ├── recording_session.py
│   │   └── ...
│   │
│   ├── semantic/
│   │   ├── recording_normalizer.py # [Fase B] + intent reconstruction (8 estratégias)
│   │   ├── locator/                # [v2 P2] v2 LocatorExtractor
│   │   ├── stages/                 # [v2 P5] Pipes & Filters
│   │   ├── compiler.py             # [Fase C] Playwright code gen
│   │   └── ...
│   │
│   ├── runtime/                # [v2 P3] Runtime resolver
│   │   ├── resolver.py         # LocatorResolver
│   │   ├── step.py             # Step API
│   │   └── ...
│   │
│   ├── validation/
│   │   ├── intent_completeness.py    # [Fase B] Gate 0.70
│   │   ├── readiness_gate.py
│   │   └── ...
│   │
│   ├── healing/
│   │   ├── healing_catalog.py        # [L0] JSONL catalog
│   │   ├── sqlite_intent_catalog.py  # [v2 P4] SQLite L0
│   │   ├── agents/                   # [Fase D] L2 agents
│   │   └── ...
│   │
│   ├── metrics/
│   │   ├── pilot_metrics.py          # [Sprint 8]
│   │   └── telemetry.py              # [v2 P6] Zero-dep tracer
│   │
│   └── cli/
│       ├── app.py                # CLI: record, compile, run, heal, diagnose
│
├── docs/
│   ├── ARQUITETURA/
│   │   ├── FASES.md                  # ← Este documento
│   │   ├── FLUXO-SEMANTIC-MIS.md
│   │   ├── HEALING-L0-L3.md
│   │   └── ...
│   │
│   ├── TUTORIAIS/
│   │   ├── 01-setup-ambiente.md
│   │   ├── 02-gravar-seu-primeiro-teste.md
│   │   └── ...
│   │
│   └── REFERENCIA/
│       ├── BUGS-KNOWNS.md        # Bugs conhecidos consolidados
│       ├── CLI.md
│       └── ...
│
├── tests/
│   ├── intent_lab/
│   │   ├── pages/              # 21 LAB pages (LAB-01 a LAB-16)
│   │   └── test_lab*.py        # Testes por LAB page
│   ├── diagnostic/             # Sprint 0 tests
│   ├── test_phase_a_*.py
│   ├── test_phase_b_*.py
│   ├── test_phase_c_*.py
│   ├── test_phase_d_*.py
│   └── test_sprint*.py        # Sprints 3-8
│
├── CHANGELOG.md                  # Histórico de releases
├── README.md                      # Overview principal
└── AGENTS.md                      # Governance GSD
```

---

## 📋 Requisitos para Promoção entre Fases

### Fase A → B (Concluído)

- [x] 800+ testes gravando sem crashes
- [x] 11/11 famílias cobertas
- [x] Evidência coletada (screenshots, DOM, logs)
- [x] Bugs P0 corrigidos

### Fase B → C (Concluído)

- [x] IntentReconstructor implementado com 8 estratégias (merged em RecordingNormalizer)
- [x] SemanticTestCase gerado com field_values
- [x] IntentCompletenessValidator com gate 0.70
- [x] Compiler integrado com field_values passthrough
- [x] Testes E2E passando

### Fase C → D (Próximo)

- [ ] Compiler gera 100% scripts Playwright válidos
- [ ] Integração com Fase D executor
- [ ] Test runner CLI: `record`, `compile`, `run`, `heal`
- [ ] Healing L0 (retry simples) implementado

### Fase D → Release (Futuro)

- [ ] Healing L0-L3 completo
- [ ] Execution report com métricas
- [ ] Healing report com detalhes
- [ ] Documentação de distribuição

---

## 📚 Referência Histórica

Este documento consolida:
- `FASE-B-PLAN.md` (627 linhas) — Plano inicial da Fase B
- `FASE-B-COMPLETION-REPORT.md` (211 linhas) — Relatório de conclusão

**Arquivos originais para histórico:** `.planning/ARCHIVE/FASE-B-*.md`

---

**Última atualização:** 2026-06-30  
**Próxima review:** Após Sprints 7-8 (ComponentHandler execute completo)  
**Responsável:** André PN
