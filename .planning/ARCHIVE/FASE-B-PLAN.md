# Fase B — Plano de Execução: Consumir Evidência em Módulos Downstream

**Data:** 2026-06-20  
**Versão do Projeto:** TestForge v0.3.1  
**Status:** Congelada (Fase A shipada com 162 testes passando)  
**Objetivo:** Normalizer + Reconstructor + Evidence consumption

---

## 1. ESCOPO — Entradas e Saídas

### 1.1 Entradas

De Fase A (Recorder), os módulos downstream recebem:

1. **raw_events.jsonl** — eventos brutos (click, fill, keypress, submit, navigation)
2. **steps.jsonl** — asserções curadas manualmente (opcional)
3. **value_mutations.jsonl** — mutações de valor programáticas (setter hooks, currency masks)
4. **field_snapshots.jsonl** — snapshots de campo em tempo de gravação (value, checked, timestamps)
5. **network_log.json** — requisições POST/PUT com payloads de formulário
6. **final_state_snapshot.json** — dump JSON do estado final de todos os campos

### 1.2 Saídas

Fase B produz:

1. **SemanticTestCase** (YAML) contendo:
   - **steps**: ações semânticas normalizadas (click, fill, assert, select_option)
   - **field_values**: mapa de campo → FieldValueMap com fonte de evidência
   - **blind_spots**: padrões onde intenção foi perdida (gap timing, missing_fill, etc.)
   - Metadados (test_id, source_recording_id, base_url, preconditions)

2. **EvidencePackage** (para healing L3 em fases futuras):
   - Screenshots associados a passos
   - Snapshots de DOM (before/after)
   - Logs de console
   - Logs de rede

---

## 2. GAPS ENCONTRADOS E IMPACTO

### 2.1 Gaps Implementados (Código Funcional)

| Gap | Impacto | Status |
|-----|---------|--------|
| **IntentReconstructor.reconstruct_all()** — integra 5 fontes de evidência | ✅ Implementado | ✅ **FEITO** |
| **Setter hook (value_mutations.jsonl)** — currency masks, polyfill fill | ✅ Implementado | ✅ **FEITO** |
| **Snapshot diff** — text input value transitions | ✅ Implementado | ✅ **FEITO** |
| **Checked transitions** — radio/checkbox click intent recovery | ✅ Implementado | ✅ **FEITO** |
| **Network payload analysis** — POST/PUT form field extraction | ✅ Implementado | ✅ **FEITO** |
| **Final state snapshot** — fallback para campos não capturados | ✅ Implementado | ✅ **FEITO** |
| **RecordingNormalizer._reconstruct_intents()** — hookup com IntentReconstructor | ✅ Implementado | ✅ **FEITO** |
| **Field value map construction** — FieldValueMap dedup by element_id | ✅ Implementado | ✅ **FEITO** |
| **Blind spot detection** — padrões onde evidência falha | ✅ Implementado | ✅ **FEITO** |

### 2.2 Gaps de Completude (Melhorias)

| Gap | Impacto | Prioridade |
|-----|---------|-----------|
| **Timestamp correlation em network payload** — alguns payloads sem timestamp | Baixo | P3 |
| **Masked field heuristics** — detectar campos com mascara (currency, phone) | Médio | P2 |
| **Polling strategy** — implementar captura periódica de valor (não apenas transitions) | Médio | P2 |
| **Data file injection** — --data JSON para preencher missing_fill | Médio | P2 |
| **Scenario variability** — múltiplos datasets por teste | Baixo | P3 |
| **Integration com Compiler** — passthrough de field_values ao código gerado | **CRÍTICO** | **P1** |
| **Intent completeness validation** — Fase C validator para field_values | Médio | P2 |

### 2.3 Funções/Métodos Implementados (100%)

#### IntentReconstructor (20 métodos)

1. ✅ `reconstruct_all()` — orquestrador de 5 estratégias
2. ✅ `_dedupe_entries()` — dedup por field_key + source priority
3. ✅ `_reconstruct_from_value_mutations()` — setter hooks
4. ✅ `_reconstruct_from_snapshots()` — snapshot_diff + checked_transitions
5. ✅ `_reconstruct_from_form_values()` — submit payload values
6. ✅ `_reconstruct_from_network()` — POST/PUT body parsing
7. ✅ `_reconstruct_from_final_state()` — fallback final state
8. ✅ `_make_snapshot_entry()` — factory para snapshot entries
9. ✅ `_find_nearest_step_index()` — timestamp correlation
10. ✅ `_parse_payload()` — JSON / form-urlencoded parser
11. ✅ `_build_field_identifiers()` — map steps → identifiers
12. ✅ `_correlate_payload_key()` — network key → step matching
13. ✅ `_canonical_key()` — normalization helper

#### RecordingNormalizer (integração Phase B)

1. ✅ `_reconstruct_intents()` — hookup com IntentReconstructor
2. ✅ `_build_field_value_map()` — agregação + dedup de field_values
3. ✅ `_detect_missing_fills()` — detector de gaps (running AFTER reconstruction)
4. ✅ `_audit_blind_spots()` — reportagem de padrões perdidos
5. ✅ `_dedup_datepicker_sequences()` — collapse Material calendar nav
6. ✅ `_eliminate_prefill_clicks()` — mark click-before-fill noise

---

## 3. TESTES ATUAIS E COBERTURA

### 3.1 Test Suite: test_phase_b_evidence.py

**Total:** 9 testes  
**Status:** Aguardando `pytest` no venv

| Teste | Cobertura | Status |
|-------|-----------|--------|
| `TestSetterHookReconstruction::test_value_mutations_currency_mask` | value_mutations.jsonl parsing | ✅ Codificado |
| `TestSetterHookReconstruction::test_value_mutations_last_wins` | dedup by fingerprint | ✅ Codificado |
| `TestCheckedTransition::test_radio_checked_transition` | radio field snapshot diff | ✅ Codificado |
| `TestCheckedTransition::test_checkbox_checked_transition` | checkbox checked transition | ✅ Codificado |
| `TestFinalState::test_final_state_fallback` | final_state_snapshot fallback | ✅ Codificado |
| `TestReconstructAllPriority::test_form_values_beats_final_state` | SOURCE_PRIORITY ordering | ✅ Codificado |
| `TestNormalizerPhaseB::test_setter_hook_resolves_missing_fill` | e2e: setter_hook → field_values | ✅ Codificado |
| `TestNormalizerPhaseB::test_radio_label_resolved_via_checked_transition` | e2e: radio value recovery | ✅ Codificado |
| `TestNormalizerPhaseB::test_blind_spots_stored_on_stc` | blind_spots list on SemanticTestCase | ✅ Codificado |

### 3.2 Cobertura de Casos de Uso

| Caso | Teste | Gap |
|------|-------|-----|
| Currency mask (input setada via JS) | test_value_mutations_currency_mask | ✅ OK |
| Radio button label recovery | test_radio_checked_transition | ✅ OK |
| Checkbox consent recovery | test_checkbox_checked_transition | ✅ OK |
| Form submit payload parsing | test_form_values_beats_final_state | ✅ OK |
| Missing fill detection | test_setter_hook_resolves_missing_fill | ✅ OK |
| Network POST body extraction | **NÃO TEM TESTE ESPECÍFICO** | ⚠️ FALTA |
| Polling strategy (incremental reads) | **NÃO IMPLEMENTADO** | ⚠️ FALTA |
| Data file injection (--data) | **NÃO TEM TESTE** | ⚠️ FALTA |

---

## 4. BREAKDOWN DE TASKS

### Epic 1: Validação de Completude (P1 - CRÍTICO)

**Objetivo:** Garantir field_values é consumido end-to-end

#### Story 1.1: Compiler Integration — Passthrough Field Values

**Descrição:** Playwright compiler deve usar field_values na geração de código Playwright.

- [ ] Task 1.1.1: Revisar PlaywrightCompiler.compile() — adicionar field_value context
- [ ] Task 1.1.2: Gerar fallback textual para missing_fill + data file support
- [ ] Task 1.1.3: Teste E2E: RecodingNormalizer → PlaywrightCompiler com field_values

**Aceitação:**
- Compiler acessa `stc.field_values[field_key].value`
- Se valor vazio, busca em --data antes de usar fill=""
- Teste gera script Playwright válido com valores

**Dependências:** Implementado RecordingNormalizer + IntentReconstructor (✅ FEITO)

**Estimativa:** 4 horas

#### Story 1.2: Intent Completeness Validator

**Descrição:** Fase C validator verifica se field_values tem cobertura mínima.

- [ ] Task 1.2.1: Implementar IntentCompletenessValidator (verificar stc.blind_spots)
- [ ] Task 1.2.2: Regra: if blind_spot.typing_not_captured, require --data file
- [ ] Task 1.2.3: Teste: 162 semantic tests com completude >= 80%

**Aceitação:**
- Validator retorna `{ completeness_score: 0.85, missing_fields: [...] }`
- Se score < 0.70, bloqueiar promoção (gate)

**Dependências:** RecordingNormalizer (✅ FEITO)

**Estimativa:** 6 horas

---

### Epic 2: Melhorias de Reconstrução (P2)

**Objetivo:** Aumentar taxa de sucesso de field_value recovery sem dados externos

#### Story 2.1: Polling Strategy

**Descrição:** Implementar captura periódica de valor (não apenas transitions).

- [ ] Task 2.1.1: Estender FieldSnapshot para incluir `polling_interval_ms`
- [ ] Task 2.1.2: Estender IntentReconstructor com `_reconstruct_from_polling()`
- [ ] Task 2.1.3: Teste: currency field com polling a cada 500ms

**Aceitação:**
- Polling entries produzem field_values com source="polling"
- Score: 50 (abaixo de snapshot_diff: 70)

**Dependências:** field_snapshots.jsonl captura polling (Fase A)

**Estimativa:** 5 horas

#### Story 2.2: Masked Field Heuristics

**Descrição:** Detectar e-marcar campos com máscara (currency, phone, date).

- [ ] Task 2.2.1: Heurística: value_mutations com padrão numérico + pontuação = masked field
- [ ] Task 2.2.2: Adicionar flag `is_masked` a FieldValueMap.identifiers
- [ ] Task 2.2.3: Teste: renda "10000" → "10.000,00" reconhecido como masked

**Aceitação:**
- FieldValueMap.identifiers["is_masked"] = true
- Compiler gera fill() com valor bruto, não formatado

**Dependências:** value_mutations.jsonl parsing (✅ FEITO)

**Estimativa:** 3 horas

#### Story 2.3: Network Timestamp Correlation Improvement

**Descrição:** Melhorar matching entre payloads e steps quando timestamp falta.

- [ ] Task 2.3.1: URL-based fallback em _correlate_payload_key()
- [ ] Task 2.3.2: Teste: payload sem timestamp, match via URL

**Aceitação:**
- Se timestamp faltar, usa URL matching
- Score de confiança reduzido em identifiers

**Dependências:** network_log.json com POST entries

**Estimativa:** 2 horas

---

### Epic 3: Testing & Documentation (P1)

**Objetivo:** Cobertura completa + docs para maintainability

#### Story 3.1: Test Coverage Expansion

**Descrição:** Adicionar testes faltantes + fix venv pytest.

- [ ] Task 3.1.1: Setup pytest no .venv (uv add pytest)
- [ ] Task 3.1.2: Test: network_payload extraction → field_values
- [ ] Task 3.1.3: Test: data file injection (--data json)
- [ ] Task 3.1.4: Test: scenario variability (múltiplos datasets)
- [ ] Task 3.1.5: Rodada: 162 testes base + 15 novos = 177 testes
- [ ] Task 3.1.6: Report: cobertura ≥ 85%

**Aceitação:**
- `pytest tests/ --cov=testforge.semantic --cov-report=html`
- 177+ testes passando
- Coverage ≥ 85%

**Dependências:** RecordingNormalizer + IntentReconstructor (✅ FEITO)

**Estimativa:** 8 horas

#### Story 3.2: Documentation

**Descrição:** Documentar Phase B para team de testers e developers.

- [ ] Task 3.2.1: README update: Phase B pipeline (normalizer → reconstructor → compiler)
- [ ] Task 3.2.2: PHASE-B-RUNBOOK.md: how to debug field_values + blind_spots
- [ ] Task 3.2.3: ADR-000X: Phase B evidence consumption strategy

**Aceitação:**
- README descreve flow completo
- Runbook tem exemplos de debugging

**Dependências:** Código implementado (✅ FEITO)

**Estimativa:** 4 horas

---

### Epic 4: Integration & Validation (P1)

**Objetivo:** Validar end-to-end com suite de 162 semantic tests

#### Story 4.1: E2E Validation Suite

**Descrição:** Rodar normalizer + reconstructor em todos os 162 semantic tests.

- [ ] Task 4.1.1: Batch normalize: ST-simulador-credito6..10 (4 apps)
- [ ] Task 4.1.2: Validar field_values > 70% completude por app
- [ ] Task 4.1.3: Coletar blind_spots statistics
- [ ] Task 4.1.4: Report: gaps por app + resoluções sugeridas

**Aceitação:**
- 162/162 testes normalizam com 0 erros
- field_values: média 75%+ cobertura
- blind_spots < 10% por teste

**Dependências:** RecordingNormalizer (✅ FEITO)

**Estimativa:** 6 horas

#### Story 4.2: Compiler Integration Test

**Descrição:** Gerar + executar scripts Playwright a partir de 4 semantic tests.

- [ ] Task 4.2.1: Compilar 4 semantic tests com field_values
- [ ] Task 4.2.2: Executar 4 scripts em fake-bank (verificar values filled)
- [ ] Task 4.2.3: Coletar coverage: elementos reached / total elements

**Aceitação:**
- 4 scripts geram + executam sem erro
- Fill rate ≥ 85% (valor correto capturado)

**Dependências:** Compiler integration (Story 1.1)

**Estimativa:** 5 horas

---

## 5. CRITÉRIOS DE ACEITAÇÃO — FASE B COMPLETA

### 5.1 Funcional

1. **RecordingNormalizer.normalize() produz SemanticTestCase com:**
   - ✅ steps normalizados (click, fill, assert)
   - ✅ field_values preenchidos (mínimo 5 campos por teste)
   - ✅ blind_spots documentados
   - ✅ sem exceções (0 crashes)

2. **IntentReconstructor funciona com 5 fontes:**
   - ✅ value_mutations.jsonl (setter hooks)
   - ✅ field_snapshots.jsonl (snapshot_diff + checked_transition)
   - ✅ form_values (submit payload)
   - ✅ network_log.json (POST/PUT bodies)
   - ✅ final_state_snapshot.json (fallback)

3. **Priorização de evidência:**
   - ✅ form_values (100) > fill_event (80) > setter_hook (78) > snapshot_diff (70) > network_payload (60) > final_state (55)
   - ✅ Dedup por field_key + element_id

4. **PlaywrightCompiler consome field_values:**
   - ✅ Usa valor de field_values se disponível
   - ✅ Suporta --data injection para missing_fill
   - ✅ Gera scripts válidos (sem erros de sintaxe)

5. **Teste Coverage:**
   - ✅ 177 testes passando (162 base + 15 novos)
   - ✅ Coverage ≥ 85%
   - ✅ 0 flaky tests

### 5.2 Qualidade

1. **Blind Spots Reportagem:**
   - ✅ Cada teste identifica padrões perdidos
   - ✅ Sugestões de resolução (data-file, evidence-review)
   - ✅ Menos de 10% blind_spots por teste

2. **Documentação:**
   - ✅ README updated
   - ✅ PHASE-B-RUNBOOK.md com exemplos
   - ✅ Inline docstrings em RecordingNormalizer + IntentReconstructor

3. **Performance:**
   - ✅ normalize() em < 2 segundos por recording
   - ✅ reconstruct_all() em < 500ms por recording
   - ✅ Sem memory leaks (batch de 162 testes)

### 5.3 Métricas

- **Field Value Recovery Rate:** ≥ 75% (média de todos os tests)
- **Intent Completeness Score:** ≥ 0.70 (antes de Fase C)
- **Blind Spot Density:** ≤ 0.10 (spots / total steps)
- **False Negatives (missing field_value que deveria ter sido capturada):** < 5%

---

## 6. ESTIMATIVA DE TEMPO — ROADMAP FASE B

### Por Epic (sem paralelização)

| Epic | Stories | Estimativa | Dependências |
|------|---------|-----------|--------------|
| **1. Validação de Completude (P1)** | 2 | 10h | ✅ Code ready |
| **2. Melhorias de Reconstrução (P2)** | 3 | 10h | ✅ Code ready |
| **3. Testing & Docs (P1)** | 2 | 12h | ✅ Code ready |
| **4. Integration & Validation (P1)** | 2 | 11h | Story 1.1 |
| **TOTAL FASE B** | **9** | **43h** | |

### Timeline Estimado (1 pessoa, 8h/dia)

- **Dia 1-2 (16h):** Epics 1+2 + test setup
- **Dia 3 (8h):** Epic 3 (tests + docs)
- **Dia 4-5 (16h):** Epic 4 (E2E validation + compiler integration)
- **Dia 6 (3h):** Buffer + review

**Total: ~5.5 dias** (ou 1 semana com overhead)

---

## 7. PRs PLANEJADAS

### PR 1: Compiler Integration + Field Values Passthrough

**Branch:** `feat/phase-b-compiler-integration`  
**Escopo:** Story 1.1 + Task 3.1.1 (pytest setup)

```
src/testforge/semantic/compiler.py
  - Adicionar field_values parameter a compile()
  - Implementar fallback textual para missing_fill
  - Data file support (--data json)

tests/test_semantic.py
  - Add 3 testes de compiler integration
```

**Commits:**
1. `feat: compiler — accept field_values + data file`
2. `test: compiler integration with field_values`
3. `chore: pytest setup in .venv`

---

### PR 2: Intent Completeness Validator

**Branch:** `feat/phase-b-intent-completeness`  
**Escopo:** Story 1.2

```
src/testforge/validation/intent_completeness.py
  - IntentCompletenessValidator class
  - Scoring logic (field_values / total_inputs)
  - Gate: score < 0.70 blocks promotion

tests/test_validation_intent_completeness.py
  - 5 testes de scoring + gate
```

**Commits:**
1. `feat: intent completeness validator`
2. `test: completeness scoring + gate`

---

### PR 3: Polling Strategy + Masked Fields

**Branch:** `feat/phase-b-polling-masked-fields`  
**Escopo:** Story 2.1 + 2.2

```
src/testforge/semantic/intent_reconstructor.py
  - _reconstruct_from_polling() method
  - Masked field heuristics

tests/test_phase_b_evidence.py
  - 2 testes: polling + masked fields
```

**Commits:**
1. `feat: polling strategy in IntentReconstructor`
2. `feat: masked field detection heuristics`
3. `test: polling + masked scenarios`

---

### PR 4: Network Correlation Improvement + Docs

**Branch:** `feat/phase-b-network-timestamp-docs`  
**Escopo:** Story 2.3 + 3.2

```
src/testforge/semantic/intent_reconstructor.py
  - URL-based fallback in _correlate_payload_key()

docs/PHASE-B-RUNBOOK.md (NEW)
README.md
  - Phase B pipeline diagram
  - Field values consumption flow

tests/test_phase_b_evidence.py
  - 1 teste: network timestamp fallback
```

**Commits:**
1. `feat: network payload timestamp correlation improvement`
2. `docs: Phase B runbook + pipeline description`

---

### PR 5: E2E Validation Suite

**Branch:** `feat/phase-b-e2e-validation`  
**Escopo:** Epic 4

```
tests/test_phase_b_e2e_validation.py (NEW)
  - Batch normalize all 162 semantic tests
  - Validate field_values coverage
  - Collector blind_spots stats

tests/test_phase_b_compiler_integration.py (NEW)
  - Compile 4 semantic tests
  - Execute against fake-bank
  - Verify fill rate
```

**Commits:**
1. `test: E2E validation — batch normalize 162 tests`
2. `test: compiler integration E2E with 4 real tests`
3. `feat: E2E validation report — coverage stats`

---

### PR 6: Documentation + Final Report

**Branch:** `docs/phase-b-completion`  
**Escopo:** Story 3.2 + final summary

```
README.md
  - Phase B section
  - Architecture diagram (normalizer → reconstructor → compiler)

PHASE-B-COMPLETION-REPORT.md (NEW)
  - Métricas: field_values recovery, blind_spots density
  - Test coverage: 177+ tests, ≥ 85%
  - Próximos passos (Fase C)

adrs/ADR-000X-phase-b-evidence-consumption.md (NEW)
```

**Commits:**
1. `docs: Phase B completion report`
2. `docs: Phase B architecture + runbook`

---

## 8. DEPENDÊNCIAS INTERNAS

```
Fase B Dependencies
====================

┌─ Phase A (✅ CONGELADA)
│  ├─ raw_events.jsonl
│  ├─ value_mutations.jsonl
│  ├─ field_snapshots.jsonl
│  ├─ network_log.json
│  └─ final_state_snapshot.json
│
├─ Story 1.1 (Compiler Integration)
│  ├─ RecordingNormalizer (✅)
│  ├─ IntentReconstructor (✅)
│  └─ PlaywrightCompiler (🔧 needs update)
│
├─ Story 1.2 (Intent Completeness)
│  └─ RecordingNormalizer (✅) → blind_spots
│
├─ Story 2.1 (Polling)
│  └─ field_snapshots.jsonl (extensão)
│
├─ Story 2.2 (Masked Fields)
│  └─ value_mutations.jsonl (✅)
│
├─ Story 3.1 (Tests)
│  ├─ Story 1.1 ← Story 4.2 depends on this
│  └─ Story 1.2 ← Story 4.1 depends on this
│
└─ Story 4.1 + 4.2 (E2E)
   ├─ Story 1.1 (Compiler)
   ├─ Story 1.2 (Validator)
   └─ All Epic 2 stories (preferred, not required)
```

---

## 9. CHECKLIST FINAL — ANTES DE MERGEAR

### PR 1: Compiler Integration

- [ ] `pytest tests/test_semantic.py -v` — 3 novos testes passando
- [ ] `pytest tests/test_phase_b_evidence.py -v` — 9 testes ainda passando
- [ ] Compiler produz script Playwright válido (py syntax check)
- [ ] Manual: rodar script gerado em fake-bank — fill rate ≥ 85%

### PR 2: Intent Completeness

- [ ] IntentCompletenessValidator.validate() retorna dict correto
- [ ] Gate logic: score < 0.70 blocks promotion
- [ ] 5 testes passando

### PR 3: Polling + Masked

- [ ] value_mutations com currency parsed como masked
- [ ] Polling entries criadas com source="polling"
- [ ] 2 novos testes passando

### PR 4: Network + Docs

- [ ] _correlate_payload_key() falls back to URL if no timestamp
- [ ] PHASE-B-RUNBOOK.md readable
- [ ] README tem diagrama atualizado

### PR 5: E2E Validation

- [ ] Batch normalize 162 testes com 0 crashes
- [ ] field_values coverage report (média ≥ 75%)
- [ ] Compiler E2E: 4 testes geram + executam

### PR 6: Final Docs

- [ ] All PRs merged to main
- [ ] PHASE-B-COMPLETION-REPORT.md pronto
- [ ] 177+ testes passando
- [ ] Coverage ≥ 85%

---

## 10. PRÓXIMOS PASSOS (Fase C)

1. **Intent Completeness Validation** (Fase C)
   - Executar IntentCompletenessValidator em todos os 162 testes
   - Coletar fail rate por tipo de app (simulador_credito vs outro)
   - Planejar data file requirements por cenário

2. **Sandbox Piloto** (Fase C)
   - Testar field_values injection em 4 apps reais
   - Medir healing rate com dados externos (vs sem dados)
   - Refinar heurísticas baseado em feedback

3. **Fase D: Distribuição**
   - Package testforge v0.3.2 com Phase B completo
   - Release notes: "field values recovery + intent completeness validation"

---

**Última atualização:** 2026-06-20  
**Responsável:** André PN  
**Status:** Pronto para Execução
