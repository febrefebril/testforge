# TestForge — Visão Geral das Fases A-D

**Versão:** 0.4.0  
**Última atualização:** 2026-06-20  
**Status:** Fase A concluída, Fase B implementada, Fase C/D planejadas

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

### Estatísticas (v0.3.1)

- **Testes gravados:** 162
- **Taxa de passa:** 100% (162/162)
- **Famílias cobertas:** 11/11 (FAM-01 a FAM-11)
- **Keywords de classificação:** 51

### Bugs Conhecidos

Veja [Bugs Conhecidos](../REFERENCIA/BUGS-KNOWNS.md) para lista completa.

**P0 (Críticos para Fase C):**
- BUG-001: `<select>` gera seletor de `<input>` ❌
- BUG-002: DOM snapshots com 0 bytes ❌
- BUG-003: Contagem de steps inconsistente ❌
- BUG-006: Browser bloqueado em ambiente corporativo ❌

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
│   ├── recorder/
│   │   ├── __init__.py
│   │   ├── event_capture.py       # [Fase A] Captura de eventos
│   │   ├── evidence_collector.py  # [Fase A] Screenshots, DOM, logs
│   │   └── ...
│   │
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── intent_reconstructor.py   # [Fase B] 5 estratégias
│   │   ├── compiler.py               # [Fase C] Playwright code gen
│   │   └── ...
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── intent_completeness.py    # [Fase B] Gate 0.70
│   │   ├── classifier.py             # [Fase D] FAM-01 a FAM-11
│   │   └── ...
│   │
│   ├── healing/
│   │   ├── __init__.py
│   │   ├── step_runner.py        # [Fase D] Executa steps + healing
│   │   ├── agents/               # [Fase D] L2 agents (routing)
│   │   └── ...
│   │
│   └── cli/
│       ├── __init__.py
│       └── app.py                # CLI: record, compile, run, heal
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
│   ├── test_phase_a_*.py
│   ├── test_phase_b_*.py
│   ├── test_phase_c_*.py
│   └── test_phase_d_*.py
│
├── CHANGELOG.md                  # Histórico de releases
├── README.md                      # Overview principal
└── AGENTS.md                      # Governance GSD
```

---

## 📋 Requisitos para Promoção entre Fases

### Fase A → B (Concluído)

- [x] 162 testes gravando sem crashes
- [x] 11/11 famílias cobertas
- [x] Evidência coletada (screenshots, DOM, logs)
- [x] Bugs P0 corrigidos

### Fase B → C (Concluído)

- [x] IntentReconstructor implementado com 5 estratégias
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

**Última atualização:** 2026-06-20  
**Próxima review:** Após Fase C concluída  
**Responsável:** André PN
