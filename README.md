# TestForge v0.4.0

**Gravador inteligente de testes E2E com self-healing determinístico L0→L3 e validação incremental de intenção**

[![Tests](https://img.shields.io/badge/tests-194%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Commits](https://img.shields.io/badge/commits-140-blue)](https://github.com/febrefebril/testforge)
[![Sprints](https://img.shields.io/badge/sprints-8%2F8-success)](docs/testforge_plano_sprints_intent_readiness.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

> QA grava uma vez. O script sobrevive a mudanças de UI. Quando um seletor quebra, o sistema se auto-conserta — deterministicamente, sem LLM como motor primário. E quando um campo não é capturado, o CLI pergunta o valor e valida incrementalmente antes de marcar como pronto.

---

## 🎯 O Problema

Testes E2E quebram constantemente por fragilidade de seletores em aplicações enterprise (Angular, PrimeFaces, JSF). Seletores mudam a cada deploy. QAs perdem horas "consertando" testes que não deveriam quebrar. Além disso, gravações frequentemente perdem valores de campo (máscaras JS, preventDefault, input events suprimidos).

## 💡 A Solução

Gravar **intenção**, não seletores. O recorder captura: role, accessible name, texto visível, contexto. Isso vira um contrato semântico (SemanticTestCase). Na execução, se o seletor falhar, o motor deterministico gera candidatos alternativos ordenados por score. Se todos falharem, o LLM (Azure GPT-4.1-mini) é acionado como último recurso.

**Novo:** Pipeline de validação de intenção que detecta campos perdidos, pergunta valores ao QA, valida incrementalmente, e gera relatório de readiness.

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

## 🔬 Fase B — Pipeline de Intenção

### Fluxo de Dados

```
raw_events.jsonl
field_snapshots.jsonl     ┐
value_mutations.jsonl     ├──► RecordingNormalizer ──► IntentReconstructor
network_log.json          │         │
final_state_snapshot.json ┘         │
                                    ▼
                          SemanticTestCase
                               │
                               ├── steps[]          — ações do QA
                               ├── field_values{}   — valores reconstruídos
                               └── blind_spots[]    — campos não resolvidos
                                    │
                                    ▼
                          PlaywrightCompiler ──► test_st_<nome>.py
```

### Fontes de Evidência — Prioridade

O IntentReconstructor combina múltiplas fontes. Quando duas fontes capturam o
mesmo campo, a de maior prioridade vence.

| Prioridade | Fonte | O que captura | Quando usar |
|-----------|-------|--------------|------------|
| 100 | `form_values` | Valores do submit payload | Fluxos com form HTML clássico |
| 80 | `fill_event` | Eventos input/change nativos | Inputs sem máscara |
| 78 | `setter_hook` | Atribuições `element.value = ...` via JS | Campos com máscara (CPF, moeda) |
| 72 | `checked_transition` | Radio/checkbox marcado | Seleção de opções |
| 70 | `snapshot_diff` | Polling DOM — variação de valor entre snapshots | PreventDefault inputs |
| 60 | `network_payload` | Corpo de POST/PUT/PATCH | Fetch/XHR sem form submit |
| 55 | `final_state` | Dump do estado DOM ao final da sessão | Fallback de último recurso |
| 10 | `missing_fill` | Valor fornecido manualmente pelo QA via CLI | Blind spots irrecuperáveis |

### Confidence Score (network_payload)

A partir da Fase B, o `network_payload` inclui um score de confiança em `identifiers.confidence`:

| Situação | confidence | O que significa |
|---------|-----------|----------------|
| Nome/ID do campo bate com step | 1.0 | Match determinístico |
| URL do payload bate com step | 0.7 | Match por proximidade |
| Sem correspondência | — | Entry não criada |

### Debugging

Ver [docs/PHASE-B-RUNBOOK.md](docs/PHASE-B-RUNBOOK.md) para:
- Como debugar field_values ausentes
- Como inspecionar blind_spots
- Como usar `--data` para missing_fill
- Troubleshooting: campo com máscara não capturado

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

---

## 🧪 Testes

```bash
# Todos os testes
pytest tests/ -v                    # 194 testes

# Testes por sprint
pytest tests/test_sprint3_field_snapshots.py -v   # 35 testes
pytest tests/test_sprint4_intent_reconstructor.py -v  # 32 testes
pytest tests/test_sprint5_readiness_gate.py -v    # 12 testes
pytest tests/intent_lab/ -v                       # 93 testes
pytest tests/test_sprint7_cli_integration.py -v   # 11 testes
pytest tests/test_sprint8_pilot_metrics.py -v     # 11 testes

# Testes de curadoria (por família)
pytest tests/test_pages/ -v         # 39 testes

# Testes de classificação
pytest tests/test_pages/ -k "classification" -v
```

| Suite | Testes | Descrição |
|-------|--------|-----------|
| Sprint 3 | 35 | Field snapshots, setter hooks, MutationObserver |
| Sprint 4 | 32 | Intent reconstructor (3 estratégias) |
| Sprint 5 | 12 | RecordingReadinessGate + IncrementalRecordingValidator |
| Sprint 6 | 93 | Intent Lab pages + test infrastructure |
| Sprint 7 | 11 | CLI integration (--validate-before-ready) |
| Sprint 8 | 11 | Pilot metrics, failure categorization, dashboard |
| Curadoria | 39 | Healing por família (1 por família) |
| **Total** | **194** | **100% pass** |

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
| Diagramas | PlantUML (14 diagramas) |
| Pipeline | BMAD → GSD Core → Git |

---

## 🗂️ Estrutura

```
src/testforge/
├── cli/            # Comandos: record, compile, run, pipeline, demo-heal,
│   │               #      run-incremental, pilot-report
│   ├── _interactive_completion.py  # Prompt para valores pendentes
│   └── _run_incremental_patch.py  # Comando run-incremental
├── recorder/       # Recorder sensorial (Playwright nativo)
│   ├── recording_status.py        # Máquina de estados da gravação
│   ├── recorder_controller.py     # Controller com network capture
│   └── raw_recording_store.py     # Armazenamento raw
├── semantic/       # MIS: normalizer, compiler, data_extractor
│   └── intent_reconstructor.py    # 3 estratégias (Sprint 4)
├── validation/     # (NOVO) Validação de intenção
│   ├── intent_completeness.py     # IntentCompletenessChecker
│   ├── readiness_gate.py          # RecordingReadinessGate
│   ├── incremental_validator.py   # IncrementalRecordingValidator
│   └── url_validator.py           # Validação de URL
├── metrics/        # MetricsRepository + PilotMetrics (Sprint 8)
│   └── pilot_metrics.py           # Métricas agregadas do piloto
├── reporting/      # RunReport + StepReport
├── healing/        # L0: catalog, L2: agents, L3: llm_healer, curator
│   └── agents/     # 6 agentes: selector, timing, context, state, dom, input
├── evidence/       # EvidenceCollector + store
├── oracle/         # OracleRunner (visual_dom, business_state)
├── promotion/      # PromotionGate
├── taxonomy/       # 11 famílias, 88 códigos, 51 keywords
├── runner/         # FallbackRunner + SmartStepRunner (10 estratégias)
│   └── incremental_runner.py      # Runner passo a passo (Sprint 5)
└── actionability/  # Verificação de actionability

tests/
├── test_pages/     # 12 páginas de curadoria (uma por família)
│   └── curation/   # Páginas HTML com modo ?error=1
├── intent_lab/     # (NOVO) 14+ páginas de teste de intenção
│   ├── pages/      # 17 páginas HTML (14 required + 3 extras)
│   ├── test_intent_lab_pages.py           # 26 testes
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
| [SPRINT-REVIEW.md](docs/SPRINT-REVIEW.md) | Roteiro da sprint review |
| [PLANO-DE-TESTE.md](docs/PLANO-DE-TESTE.md) | 27+ casos de teste manuais |
| [PLANO-TESTE-INTENT-LAB.md](docs/PLANO-TESTE-INTENT-LAB.md) | 14 casos manuais do Intent Lab |
| [BUGS.md](docs/BUGS.md) | 5 bugs documentados e corrigidos |
| [TUTORIAL-LLM-HEALING.md](docs/TUTORIAL-LLM-HEALING.md) | Guia de uso do LLM healing |
| [run-incremental.md](docs/run-incremental.md) | Guia do executor incremental |
| [Sprint Plan](docs/testforge_plano_sprints_intent_readiness.md) | Plano completo de 8 sprints |
| [STATE.md](.planning/STATE.md) | Estado atual do projeto |
| [Diagramas PNG](docs/diagramas/png/) | 14 diagramas PlantUML |

---

## 📊 Métricas (v0.4.0)

| Métrica | Valor |
|---------|-------|
| Commits | 140 |
| Testes | 194 (100%) |
| Módulos | 35+ |
| Diagramas | 14 |
| Estratégias healing | 10 |
| Famílias cobertas | 11/11 |
| Keywords classifier | 51 |
| LLM validado | ✅ Azure GPT-4.1-mini |
| Sprints concluídos | 8/8 |
| Páginas Intent Lab | 17 (14 required + 3 extras) |
| Estratégias reconstructor | 3 (snapshot_diff, form_values, network_payload) |
| Critérios readiness | 5 |
| Falhas categorizadas | 7 tipos |

---

**Licença:** MIT
