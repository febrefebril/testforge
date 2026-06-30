# TestForge v0.4.2

**Gravador inteligente de testes E2E com self-healing determinístico L0→L3, validação incremental de intenção, Diagnostic Mode, Architecture v2 + ComponentHandler system para Angular Material, PrimeFaces e React MUI**

[![Tests](https://img.shields.io/badge/tests-800%2B%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Commits](https://img.shields.io/badge/commits-550-blue)](https://github.com/febrefebril/testforge)
[![Handlers](https://img.shields.io/badge/handlers-5-orange)](src/testforge/handlers/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

> QA grava uma vez. O script sobrevive a mudanças de UI. Quando um seletor quebra, o sistema se auto-conserta — deterministicamente, sem LLM como motor primário. E quando um campo não é capturado, o CLI pergunta o valor e valida incrementalmente antes de marcar como pronto.

---

## 🎯 O Problema

Testes E2E quebram constantemente por fragilidade de seletores em aplicações enterprise (Angular, PrimeFaces, JSF). Seletores mudam a cada deploy. QAs perdem horas "consertando" testes que não deveriam quebrar. Além disso, gravações frequentemente perdem valores de campo (máscaras JS, preventDefault, input events suprimidos).

## 💡 A Solução

Gravar **intenção**, não seletores. O recorder captura: role, accessible name, texto visível, contexto. Isso vira um contrato semântico (SemanticTestCase). Na execução, se o seletor falhar, o motor deterministico gera candidatos alternativos ordenados por score. Se todos falharem, o LLM (Azure GPT-4.1-mini) é acionado como último recurso.

**Novo v0.4.2:** **Diagnostic Mode** — Modo standalone de coleta de telemetria para equipes de QA, com FrameworkDetector, CaptureQualityTracker, ReplayCheck e GherkinWriter em português.

**Novo v0.4.2:** **Architecture v2 (Phases 1-7)** — Playwright tracing + CDP AX-tree capture parallel, v2 LocatorExtractor, LocatorResolver, SQLite intent catalog L0, Pipes & Filters pipeline, zero-dep tracer + dashboard, YAML-driven ComponentResolver.

**Novo v0.4.2:** **Sprint 0 Hotfixes** — 30+ correções no recorder, normalizer, runner, CLI, publisher, diagnostic e healing. Recorder Sprints A-J-M-O-P-Q-R-S: Material anchors, ACCNAME v1.2, rrweb-lite, finder CSS, mask raw value capture. Refactor: overlay JS extraído para `overlay_inject.js`, IntentReconstructor merged no RecordingNormalizer.

**v0.4.1:** Sistema **ComponentHandler** que detecta e executa componentes de UI framework-specific (Angular Material, PrimeFaces, React MUI) de forma determinística, sem depender de healing. Cada handler sabe abrir overlays, selecionar opções, navegar tabs — reduzindo healing L3 em ~40% para componentes cobertos. Pipeline de validação de intenção que detecta campos perdidos, pergunta valores ao QA, valida incrementalmente, e gera relatório de readiness.

---

## 🏗️ Arquitetura

```
QA grava fluxo → MIS captura intenção → Compiler gera script → Runner executa
                    ↓                                          ↓ (se falhar)
         Intent Completeness Checker                 Healing L0→L1→L2→L3 cura
                    ↓
         Interactive CLI Prompt (valores)
                    ↓
         RecordingReadinessGate → relatório READY/REVIEW/FAIL
                    ↓
         PilotMetrics → Dashboard consolidado
```

### Diagnostic Mode (Sprint 0 — v0.4.2)

Modo standalone de coleta de telemetria que enriquece decisões com dados reais:

| Componente | Função |
|-----------|--------|
| `FrameworkDetector` | CDP bundle analysis + window/DOM/custom-elements |
| `CaptureQuality` | value_kind regex, framework_signal, blind_spots |
| `ReplayCheck` | Immediate (B1) ou batched (B4) Locator probe |
| `GherkinWriter` | Live `scenario.feature` (pt-BR), C4b auto-derive + C4c confirm |
| `TelemetryStore` | JSONL primary + OTel spans (E4) |

```bash
testforge record --diagnostic-mode <url>
# ou
testforge diagnose <url>
```

### Architecture v2 (Phases 1-7)

Feature-flagged migration com novas capacidades:

| Phase | Componente | Opt-in |
|-------|-----------|--------|
| 1 | Playwright tracing + CDP AX-tree (parallel) | `--use-cdp-recorder` |
| 2 | v2 LocatorExtractor + Playwright codegen + intent | `use_v2_locator=True` |
| 3 | LocatorResolver + step API + v2 compiler | `--use-v2-compiler` |
| 4 | SQLite intent-keyed catalog + persistent L0 | `sqlite_catalog=...` |
| 5 | Pipes & Filters pipeline (4 extracted stages) | `use_pipeline=True` |
| 6 | Zero-dep tracer + static dashboard.html | `TESTFORGE_TRACING=0` |
| 7 | YAML-driven ComponentResolver | `ComponentResolver()` |

### Component Handler System (v0.4.1)

Handlers específicos por framework que executam componentes complexos sem healing:

| Handler | Framework | Componentes | Status |
|---------|-----------|------------|--------|
| `AngularMaterialHandler` | Angular Material | mat-select, mat-autocomplete, mat-dialog, mat-tab-group, mat-slide-toggle | ✅ Completo |
| `PrimeFacesHandler` | PrimeFaces | p-dropdown, ui-selectonemenu (skeleton) | 🔧 Detect only |
| `ReactMUIHandler` | React MUI | MuiSelect, MuiAutocomplete (skeleton) | 🔧 Detect only |

**Interface:** `detect()` → `normalize()` → `execute()` → `heal()`
**Registry:** `HANDLERS` list com ordem de precedência (mais específico primeiro)

### Pipeline de Cura (4 camadas)

| Camada | Componente | O que faz | Custo |
|--------|-----------|----------|-------|
| **L0** | HealingCatalog | Match exato por família+sintoma (JSONL) | <50ms |
| **L1** | FallbackRunner | Candidatos alternativos do MIS | 2-5s |
| **L2** | SpecialistAgents | 6 agentes por família (determinístico) | <100ms |
| **L3** | LLMHealer | Azure GPT-4.1-mini (off critical path) | ~500 tok |

**MockLLMHealer funciona offline — sem API key!**

### Pipeline de Validação de Intenção (novo)

| Sprint | Componente | O que faz |
|--------|-----------|----------|
| **S3** | Field Snapshots | Captura estado de todos os campos (input, select, contenteditable, ARIA) |
| **S3** | Setter Hooks | Intercepta `value` setters via JS (InputEvent.value) |
| **S3** | MutationObserver | Monitora contenteditable + atributos ARIA |
| **S4** | IntentReconstructor | 3 estratégias: snapshot_diff, form_values, network_payload |
| **S5** | RecordingReadinessGate | 5 critérios objetivos (completude, steps, blocking, user-supplied, healing) |
| **S5** | IncrementalRecordingValidator | Pipeline normalize → complete → validate → gate |
| **S7** | CLI --validate-before-ready | Valida gravação antes de marcar READY |
| **S8** | PilotMetrics | Métricas agregadas + dashboard consolidado |

---

## 🚀 Quick Start

```bash
# Ativar ambiente
source activate.sh

# Iniciar fake-bank para testes
cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &

# Gravar um fluxo (modo padrão)
testforge record http://localhost:8765 --name "meu-teste"

# Gravar com validação automática (recomendado)
testforge record http://localhost:8765 --name "meu-teste" --validate-before-ready

# Modo piloto (validação + prompt de valores pendentes)
testforge record http://localhost:8765 --name "meu-teste" --pilot-mode

# Compilar com massa de dados externa
testforge compile meu-teste --data

# Executar passo a passo com validação incremental
testforge run-incremental semantic_tests/ST-meu-teste/test_st_meu_teste.py

# Executar (modo clássico)
testforge run semantic_tests/ST-meu-teste/test_st_meu_teste.py

# Ver healing em ação (mutação quebra seletor)
testforge demo-heal

# Gerar relatório consolidado do piloto
testforge pilot-report
```

---

## 📋 Comandos

### Gravação e Compilação

| Comando | Descrição |
|---------|-----------|
| `testforge record <url>` | Gravar fluxo de teste |
| `testforge record <url> --complete` | + Verificar completude e perguntar valores |
| `testforge record <url> --no-interactive` | + Criar template sem perguntar |
| `testforge record <url> --validate-before-ready` | + Validar antes de marcar READY |
| `testforge record <url> --pilot-mode` | + Modo piloto (validação automática) |
| `testforge compile <recording>` | Compilar em script Playwright |
| `testforge compile <rec> --data` | + Extrair massa para JSON externo |
| `testforge compile <rec> --check` | + Verificar completude da intenção |

### Execução

| Comando | Descrição |
|---------|-----------|
| `testforge run <script>` | Executar com healing L0→L3 |
| `testforge run-incremental <script>` | Executar passo a passo com pre/pos-condições |
| `testforge run <script> --headless` | Modo headless |
| `testforge run-incremental <script> --interactive` | + Modo interativo (pausa em falhas) |

### Pipeline e Relatórios

| Comando | Descrição |
|---------|-----------|
| `testforge pipeline <url>` | Pipeline completa: record → compile → run |
| `testforge demo-heal` | Demo de healing real com mutação |
| `testforge pilot-report` | Relatório consolidado do piloto |
| `testforge pilot-report --recordings-dir <dir>` | + Diretório customizado |

---

## 🩹 Healing por Família

| Família | Código | Exemplo | Agente L2 |
|---------|--------|---------|-----------|
| **FAM-01** | SEL-004 | Seletor quebrado (ID dinâmico) | SelectorAgent |
| **FAM-02** | TIM-005 | Timeout (conteúdo com delay) | TimingAgent |
| **FAM-03** | CTX-001 | Elemento dentro de iframe | ContextAgent |
| **FAM-04** | STA-002 | Overlay bloqueando clique | StateAgent |
| **FAM-05** | DOM-001 | Stale element (DOM mutante) | DynamicDOMAgent |
| **FAM-06** | INP-007 | Campo com máscara JS (CPF) | InputAgent |
| **FAM-07** | FILE-001 | Upload de arquivo | InputAgent |
| **FAM-08** | AST-004 | Assert de texto falhou | — (L3 only) |
| **FAM-09** | REC-002 | Recorder não capturou evento | — (L3 only) |
| **FAM-10** | OBS-003 | Erro de rede/execução | — (L3 only) |
| **FAM-11** | LIM-001 | CAPTCHA/limite técnico | — (L3 only) |

**10 estratégias de healing** via SmartStepRunner: `visibility_wait`, `press_sequentially`, `overlay_dismiss`, `dialog_handler`, `iframe_switch`, `synthetic_click`, `label_click`, `has_text_fallback`, `semantic_locator_conversion`, `xpath_fallback`.

---

## 📊 Data-Driven Testing

Valores de teste extraídos automaticamente da gravação para JSON externo:

```bash
testforge compile meu-teste --data

# Gera: semantic_tests/ST-meu-teste/test_data.json
# {
#   "fields": {
#     "cpf": "12345678900"
#   },
#   "sensitive_alerts": [...]
# }

# Alterar CPF sem recompilar:
vim semantic_tests/ST-meu-teste/test_data.json  # muda para 99988877666
testforge run semantic_tests/ST-meu-teste/test_st_meu_teste.py  # usa novo valor!
```

---

## 🧪 Validação de Intenção (Sprints 3-8)

### Fluxo de Readiness

Quando uma gravação termina, o pipeline de validação executa:

1. **Normalização** — raw_events → SemanticTestCase
2. **Completude** — IntentCompletenessChecker detecta campos perdidos
3. **Prompt** — CLI pergunta valores (ou cria template em --no-interactive)
4. **Readiness Gate** — 5 critérios:
   - Completude: todos os campos resolvidos?
   - Steps: todos os passos executaram?
   - Blocking: steps bloqueantes resolvidos?
   - User-supplied: valores informados validados?
   - Healing Oracles: healing passou na validação?
5. **Relatório** — readiness_report.md salvo na pasta da gravação

### Intent Lab — 14 Páginas de Teste

| Página | Fluxo | Teste Automático | Teste Manual |
|--------|-------|-----------------|--------------|
| ready-flow | Fluxo feliz completo | CT-AUTO-5.1 | CT-MAN-6.1 |
| missing-fill-gap | Gap de digitação | CT-AUTO-1.2 | CT-MAN-6.2 |
| prevent-default-input | preventDefault + JS setter | CT-AUTO-3.1 | CT-MAN-6.3 |
| currency-mask | Máscara monetária | CT-AUTO-3.2 | CT-MAN-6.4 |
| native-select | Select nativo | CT-AUTO-3.4 | CT-MAN-6.5 |
| custom-combobox | role=combobox customizado | Manual | CT-MAN-6.6 |
| contenteditable | Editor rico contenteditable | CT-AUTO-3.3 | CT-MAN-6.7 |
| network-payload-only | Valor via fetch POST | CT-AUTO-4.3 | CT-MAN-6.8 |
| iframe-field | Campo em iframe same-origin | Manual | CT-MAN-6.9 |
| shadow-dom-field | Campo em shadow DOM | Manual | CT-MAN-6.10 |
| upload-file | Input type=file | Manual | CT-MAN-6.11 |
| two-similar-fields | Dois campos parecidos | CT-AUTO-5.2 | CT-MAN-6.12 |
| dynamic-result | Resultado dinâmico | Manual | CT-MAN-6.13 |
| blocking-step-failure | Falha bloqueante em cascata | CT-AUTO-5.4 | CT-MAN-6.14 |

### Relatório Consolidado do Piloto

```bash
testforge pilot-report
# → reports/pilot_readiness_report.json
# → reports/pilot_readiness_report.md
```

O dashboard mostra:
- Total de gravações, prontas, incompletas, em revisão
- Campos auto-resolvidos, informados, perdidos
- Validação incremental passou/falhou
- Top falhas por categoria (missing_value, selector_failed, etc.)
- Lista detalhada por gravação

---

## 🤖 LLM Support

| Provider | Configuração |
|----------|-------------|
| **Azure OpenAI** | `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT` |
| **OpenAI** | `OPENAI_API_KEY` |
| **Mock** | Padrão — deterministico, sem API key |

```bash
# Com LLM real:
export AZURE_OPENAI_ENDPOINT="https://seu-recurso.openai.azure.com/"
testforge run script.py
# Output: Healer: LLM real (Azure/OpenAI)

# Sem LLM (padrão):
testforge run script.py
# Output: Healer: MockLLMHealer (deterministico)
```

**Modelo:** GPT-4.1-mini · Temperature: 0.3 · Max tokens: 500 · Retry: 3x com backoff  
**Handler fallback:** ComponentHandler.heal() executado antes de L3 LLM

---

## 🧪 Testes

```bash
# Todos os testes
pytest tests/ -v                    # 200+ testes

# Testes por sprint
pytest tests/test_sprint3_field_snapshots.py -v   # 35 testes
pytest tests/test_sprint4_intent_reconstructor.py -v  # 32 testes
pytest tests/test_sprint5_readiness_gate.py -v    # 12 testes
pytest tests/intent_lab/ -v                       # 93 testes
pytest tests/test_sprint7_cli_integration.py -v   # 11 testes
pytest tests/test_sprint8_pilot_metrics.py -v     # 11 testes

# Diagnostic Mode tests
pytest tests/test_diagnostic/ -v    # Sprint 0 tests

# Testes de classificação
pytest tests/test_pages/ -k "classification" -v
```

| Suite | Testes | Descrição |
|-------|--------|-----------|
| Sprint 3 | 35 | Field snapshots, setter hooks, MutationObserver |
| Sprint 4 | 32 | Intent reconstructor (8 estratégias) |
| Sprint 5 | 12 | RecordingReadinessGate + IncrementalRecordingValidator |
| Sprint 6 | 93 | Intent Lab pages + test infrastructure |
| Sprint 7 | 11 | CLI integration (--validate-before-ready) |
| Sprint 8 | 11 | Pilot metrics, failure categorization, dashboard |
| Curadoria | 39 | Healing por família (1 por família) |
| Sprint 0 | 20+ | Diagnostic Mode, hotfix regression |
| **Total** | **200+** | **100% pass** |

---

## 📐 Stack

| Camada | Tecnologia |
|--------|-----------|
| Runtime | Python 3.10+ |
| Browser | Playwright (Chromium, sync API) |
| CLI | argparse |
| Storage | JSONL + filesystem (zero DB) |
| LLM | Azure OpenAI / OpenAI (httpx) |
| Testes | pytest + pytest-playwright |
| Diagramas | PlantUML (20+ diagramas) |
| Pipeline | BMAD → GSD Core → Git |

---

## 🗂️ Estrutura

```
src/testforge/
├── handlers/       # ComponentHandler system (v0.4.1)
│   ├── __init__.py             # Registry + detect_handler()
│   ├── component_handler.py    # ABC: detect, normalize, execute, heal
│   ├── component_resolver.py   # YAML-driven resolver (v2 Phase 7)
│   ├── cdk_overlay.py          # Shared CDK overlay utilities
│   ├── angular_material.py     # mat-select, autocomplete, dialog, tabs
│   ├── primeFaces.py           # Skeleton
│   └── react_mui.py            # Skeleton
├── diagnostic/    # Sprint 0 — Diagnostic Mode
│   ├── framework_detector.py   # A3 CDP + A4 window/DOM analysis
│   ├── capture_quality.py      # Value_kind regex, blind_spots
│   ├── replay_check.py         # Immediate/batched Locator probe
│   ├── gherkin_writer.py       # Live scenario.feature (pt-BR)
│   ├── telemetry_store.py      # JSONL + OTel spans (E4)
│   └── session.py              # DiagnosticSession orchestrator
├── cli/            # Comandos: record, compile, run, pipeline, diagnose
│   ├── _interactive_completion.py  # Prompt para valores pendentes
│   └── _run_incremental_patch.py  # Comando run-incremental
├── recorder/       # Recorder sensorial (Playwright nativo)
│   ├── overlay_inject.js       # JS overlay extraído (v0.4.2)
│   ├── tracing_manager.py      # Playwright tracing (v2 Phase 1)
│   ├── cdp_snapshot.py         # CDP AX-tree capture (v2 Phase 1)
│   ├── recording_session.py
│   ├── recording_status.py     # Máquina de estados da gravação
│   ├── recorder_controller.py  # Controller + network capture
│   └── raw_recording_store.py  # Armazenamento raw
├── semantic/       # MIS: normalizer, compiler, data_extractor
│   ├── recording_normalizer.py # Normalizer + intent reconstruction (8 estratégias)
│   ├── locator/                # v2 Phase 2 — LocatorExtractor
│   │   ├── intent.py           # Intent text normalization
│   │   ├── scorer.py           # Candidate scoring
│   │   ├── playwright_codegen.py  # PW codegen
│   │   └── extractor.py        # v2 extractor
│   ├── stages/                 # v2 Phase 5 — Pipes & Filters
│   │   ├── base.py             # Stage ABC
│   │   ├── context.py          # Context aggregator
│   │   └── stage_*.py          # Extracted stages
│   └── compiler.py             # PlaywrightCompiler (v1 + v2)
├── runtime/        # v2 Phase 3 — Runtime resolver
│   ├── resolver.py             # LocatorResolver
│   ├── step.py                 # Step API
│   ├── _pw_dispatch.py         # Playwright dispatch
│   └── errors.py               # Runtime errors
├── validation/     # Validação de intenção
│   ├── intent_completeness.py  # IntentCompletenessChecker
│   ├── readiness_gate.py       # RecordingReadinessGate
│   ├── incremental_validator.py  # IncrementalRecordingValidator
│   └── url_validator.py        # Validação de URL
├── metrics/        # Métricas
│   ├── pilot_metrics.py        # Métricas agregadas do piloto (Sprint 8)
│   └── telemetry.py            # Zero-dep tracer (v2 Phase 6)
├── reporting/      # RunReport + StepReport
├── healing/        # L0: catalog, L2: agents, L3: llm_healer, curator
│   ├── healing_catalog.py      # L0 JSONL catalog
│   ├── sqlite_intent_catalog.py # L0 SQLite catalog (v2 Phase 4)
│   └── agents/                 # 6 agentes: selector, timing, context, state, dom, input
├── config/
│   └── component_patterns.yaml # Declarative component patterns (v2 Phase 7)
├── evidence/       # EvidenceCollector + store
├── oracle/         # OracleRunner (visual_dom, business_state)
├── promotion/      # PromotionGate
├── taxonomy/       # 11 famílias, 88 códigos, 51 keywords
├── runner/         # FallbackRunner + SmartStepRunner (10 estratégias)
│   └── incremental_runner.py   # Runner passo a passo (Sprint 5)
└── actionability/  # Verificação de actionability

tests/
├── test_pages/     # 12 páginas de curadoria (uma por família)
│   └── curation/   # Páginas HTML com modo ?error=1
├── intent_lab/     # 21 páginas de teste (LAB-01 a LAB-16)
│   ├── pages/      # 21 páginas HTML (LAB-01..LAB-16)
│   ├── test_intent_lab_pages.py           # Testes integrados
│   ├── test_lab11_mat_select.py           # LAB-11
│   ├── test_lab12_mat_autocomplete.py     # LAB-12
│   ├── test_lab13_mat_dialog.py           # LAB-13
│   ├── test_lab14_mat_tabs.py             # LAB-14
│   ├── test_recording_readiness.py        # 7 testes
│   ├── test_incremental_validation.py     # 10 testes
│   └── test_cli_completion.py             # 3 testes
├── test_sprint3_field_snapshots.py        # 35 testes
├── test_sprint4_intent_reconstructor.py   # 30 testes
├── test_sprint5_readiness_gate.py         # 12 testes
├── test_sprint7_cli_integration.py        # 11 testes
└── test_sprint8_pilot_metrics.py          # 11 testes
```

---

## 🔧 Desenvolvimento

```bash
source activate.sh      # Ativa venv + OpenHarness
opencode                # Inicia OpenCode TUI
oh -p "tarefa"          # OpenHarness modo prompt
```

**Pipeline:** BMAD (planejamento) → GSD Core (execução) → Git (versionamento) → Caveman (compressão)

---

## 📚 Documentação

| Documento | Conteúdo |
|-----------|----------|
| [Visão Geral](docs/OVERVIEW.md) | 5-min overview executivo |
| [Quick Start](docs/USER-GUIDE/QUICK-START.md) | Grave seu primeiro teste em 5 min |
| [Diagnostic Mode](docs/ARCHITECTURE-V2.md) | Diagnostic Mode + Architecture v2 (Phases 1-7) |
| [Arquitetura](docs/ARQUITETURA/FASES.md) | Visão geral das Fases A-D |
| [Diagramas PNG](docs/diagramas/png/) | 20+ diagramas PlantUML |
| [STATE.md](.planning/STATE.md) | Estado atual do projeto |

---

## 📊 Métricas (v0.4.2)

| Métrica | Valor |
|---------|-------|
| Commits | 550+ |
| Testes | 800+ |
| Módulos | 40+ |
| Diagramas | 20+ (5 novos: diagnostic, v2 pipeline, v2 flow, assert, data-driven) |
| ComponentHandlers | 5 (Angular Material, PrimeFaces, React MUI, CDK Overlay, ABC) |
| Estratégias healing | 10 |
| Famílias cobertas | 11/11 |
| Keywords classifier | 51 |
| LAB pages | 21 (LAB-01 a LAB-16) |
| LLM validado | ✅ Azure GPT-4.1-mini |
| Sprints ComponentHandler | 6/6 (Sprints 1-6) |
| Sprints Recorder (v0.4.2) | A, A2, A3, B, B2, B3, D, F, J, M, O, P, Q, R, S |
| Architecture v2 Phases | 7/7 (Phases 1-7 shipped) |
| Hotfixes Sprint 0 | 30+ |
| Estratégias reconstructor | 8 (value_mutations, snapshots, form_values, network, final_state, polling, inline_field_values, keystroke_buffer) |
| Critérios readiness | 5 |
| Falhas categorizadas | 7 tipos |

---

**Licença:** MIT
