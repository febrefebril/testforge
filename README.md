# TestForge v0.3.1

**Gravador inteligente de testes E2E com self-healing determinístico L0→L3**

[![Tests](https://img.shields.io/badge/tests-162%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Commits](https://img.shields.io/badge/commits-100-blue)](https://github.com/febrefebril/testforge)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

> QA grava uma vez. O script sobrevive a mudanças de UI. Quando um seletor quebra, o sistema se auto-conserta — deterministicamente, sem LLM como motor primário.

---

## 🎯 O Problema

Testes E2E quebram constantemente por fragilidade de seletores em aplicações enterprise (Angular, PrimeFaces, JSF). Seletores mudam a cada deploy. QAs perdem horas "consertando" testes que não deveriam quebrar.

## 💡 A Solução

Gravar **intenção**, não seletores. O recorder captura: role, accessible name, texto visível, contexto. Isso vira um contrato semântico (SemanticTestCase). Na execução, se o seletor falhar, o motor deterministico gera candidatos alternativos ordenados por score. Se todos falharem, o LLM (Azure GPT-4.1-mini) é acionado como último recurso.

---

## 🏗️ Arquitetura

```
QA grava fluxo → MIS captura intenção → Compiler gera script → Runner executa
                                                              ↓ (se falhar)
                                              Healing L0→L1→L2→L3 cura
```

### Pipeline de Cura (4 camadas)

| Camada | Componente | O que faz | Custo |
|--------|-----------|----------|-------|
| **L0** | HealingCatalog | Match exato por família+sintoma (JSONL) | <50ms |
| **L1** | FallbackRunner | Candidatos alternativos do MIS | 2-5s |
| **L2** | SpecialistAgents | 6 agentes por família (determinístico) | <100ms |
| **L3** | LLMHealer | Azure GPT-4.1-mini (off critical path) | ~500 tok |

**MockLLMHealer funciona offline — sem API key!**

---

## 🚀 Quick Start

```bash
# Ativar ambiente
source activate.sh

# Iniciar fake-bank para testes
cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &

# Gravar um fluxo
testforge record http://localhost:8765 --name "meu-teste"
# Preencha CPF, clique em Pesquisar, Shift+S para parar

# Compilar com massa de dados externa
testforge compile meu-teste --data

# Executar
testforge run semantic_tests/ST-meu-teste/test_st_meu_teste.py

# Ver healing em ação (mutação quebra seletor)
testforge demo-heal
```

---

## 📋 Comandos

| Comando | Descrição |
|---------|-----------|
| `testforge record <url>` | Gravar fluxo de teste |
| `testforge compile <recording>` | Compilar em script Playwright |
| `testforge compile <rec> --data` | + Extrair massa para JSON externo |
| `testforge compile <rec> --data --scenarios` | + Suporte a múltiplos cenários |
| `testforge run <script>` | Executar com healing L0→L3 |
| `testforge run <script> --headless` | Modo headless |
| `testforge pipeline <url>` | Pipeline completa: record → compile → run |
| `testforge demo-heal` | Demo de healing real com mutação |

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
vim semantic_tests/ST-meu-teste/test_data.json  # muda para 99988877766
testforge run semantic_tests/ST-meu-teste/test_st_meu_teste.py  # usa novo valor!
```

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
pytest tests/ -v                    # 162 testes

# Testes de curadoria (por família)
pytest tests/test_pages/ -v         # 39 testes

# Testes de classificação
pytest tests/test_pages/ -k "classification" -v

# Testes de healing pipeline
pytest tests/test_pages/ -k "heal_error" -v
```

| Suite | Testes | Descrição |
|-------|--------|-----------|
| Unitários | 124 | Módulos core |
| Curation Pipeline | 38 | 1 por família (classificação, agentes, evidência, healing) |
| E2E | 3 | Healing integração |
| **Total** | **162** | **100% pass** |

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
├── cli/            # Comandos: record, compile, run, pipeline, demo-heal
├── recorder/       # Recorder sensorial (Playwright nativo)
├── semantic/       # MIS: normalizer, compiler, data_extractor
├── healing/        # L0: catalog, L2: agents, L3: llm_healer, curator
│   └── agents/     # 6 agentes: selector, timing, context, state, dom, input
├── evidence/       # EvidenceCollector + store
├── oracle/         # OracleRunner (visual_dom, business_state)
├── promotion/      # PromotionGate
├── taxonomy/       # 11 famílias, 88 códigos, 51 keywords
├── runner/         # FallbackRunner + SmartStepRunner (10 estratégias)
└── metrics/        # MetricsRepository

tests/
├── test_pages/     # 12 páginas de curadoria (uma por família)
│   └── curation/   # Páginas HTML com modo ?error=1
└── test_curation_pipeline.py  # 39 testes parametrizados
```

---

## 🐛 Bugs Conhecidos

**Todos os 5 bugs encontrados foram corrigidos.** Veja [docs/BUGS.md](docs/BUGS.md) para o histórico completo.

- ✅ BUG-STA-001: Overlay blocking → SmartStepRunner overlay_dismiss
- ✅ BUG-INP-001: Masked input → SmartStepRunner press_sequentially
- ✅ BUG-TIM-001: Timeout → SmartStepRunner visibility_wait
- ✅ BUG-DOM-001: Stale DOM → SmartStepRunner has_text_fallback
- ✅ BUG-CLS-001: Classification net::ERR_ → keyword fix

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
| [PLANO-DE-TESTE.md](docs/PLANO-DE-TESTE.md) | 27 casos de teste manuais |
| [BUGS.md](docs/BUGS.md) | 5 bugs documentados e corrigidos |
| [TUTORIAL-LLM-HEALING.md](docs/TUTORIAL-LLM-HEALING.md) | Guia de uso do LLM healing |
| [STATE.md](.planning/STATE.md) | Estado atual do projeto |
| [Diagramas PNG](docs/diagramas/png/) | 14 diagramas PlantUML |

---

## 📊 Métricas (v0.3.1)

| Métrica | Valor |
|---------|-------|
| Commits | 100 |
| Testes | 162 (100%) |
| Módulos | 28 |
| Diagramas | 14 |
| Estratégias healing | 10 |
| Famílias cobertas | 11/11 |
| Keywords classifier | 51 |
| LLM validado | ✅ Azure GPT-4.1-mini |

---

**Licença:** MIT
