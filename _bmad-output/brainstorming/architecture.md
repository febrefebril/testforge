---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/brainstorming/product-brief.md
  - _bmad-output/brainstorming/failure-analysis-five-whys.md
  - conhecimento_ancestral/planejamento/arquitetura-selfhealing.md
  - conhecimento_ancestral/planejamento/prompt-pack-v2/prompt-pack.md
  - conhecimento_ancestral/projeto-anterior/.opencode/project-context.md
workflowType: 'architecture'
project_name: 'TestForge'
user_name: 'Andre'
date: '2026-06-13'
---

# Arquitetura — TestForge v1

## 1. Visao Geral

TestForge grava intencao do usuario em paginas web e gera scripts de teste com self-healing deterministico.

**Fluxo principal:**
```
Recorder Sensorial → SemanticTestCase → Compiler Playwright → Runner + Healing
```

**Fonte de verdade:** O `SemanticTestCase` (contrato semantico). O script Playwright gerado e artefato derivado — pode ser regenerado a qualquer momento.

---

## 2. Componentes

### 2.1 Recorder Sensorial

Responsavel por capturar eventos do usuario no navegador. NAO gera script final. NAO escolhe locator definitivo.

**Implementacao:** Playwright API nativa (`page.on('pointerup')`, `page.on('input')`, `page.on('keydown')`). Zero extensao de browser.

| Decisao | Justificativa |
|---------|--------------|
| `pointerup` em vez de `click` | Chromium nao dispara eventos de mouse em elementos `disabled`. So `pointerup` funciona consistentemente. |
| Listener no `window` | Evita que handlers de pagina em capture phase no `document` bloqueiem a captura. |
| Fill: `input` + `keydown` + `change` + polling 500ms | Campos com mascara JS nao disparam `input` — precisam de `keydown` + verificacao periodica. |

**Estrategia de captura (do projeto-anterior funcional):**
- **Evidence Collector**: captura TODOS os atributos (id, class, data-*, aria-*, role, rect, parentChain, framework)
- **N Strategies por step**: data-testid, id, name, aria-label, placeholder, has-text, href, alt, class, dom-path
- **Primary selector**: melhor strategy (ID > data-testid > name > aria-label > ...)
- **Framework detection**: `_tf_detectPageTech()` + `detectFramework(el)` por DOM inspection
- **Modo `shortcuts`**: sem UI DOM, apenas listeners — zero interferencia visual

**Artefatos gerados:**
```
recordings/{recording_id}/
├── recording_metadata.json
├── raw_events.jsonl
├── network_log.json
├── sensitive_data_alert.json
├── screenshots/evt_NNNN.png
├── dom_snapshots/evt_NNNN.html
└── ax_snapshots/evt_NNNN.json
```

### 2.2 Modelo Intermediario Semantico (MIS)

Converte `RawRecordedSession` em `SemanticTestCase` — o contrato semantico que e a fonte de verdade.

**Por que existe:** Separar captura sensorial de execucao. O recorder captura TUDO. O MIS extrai o que importa: intencao, alvo semantico, contexto, candidatos.

**Estrutura do SemanticTestCase:**
```yaml
semantic_test_case:
  metadata:
    test_id: "ST-20260613-001"
    source_recording: "REC-20260613-001"
  preconditions: []
  steps:
    - action: fill
      target:
        role: "textbox"
        accessible_name: "CPF"
        label: "CPF"
        placeholder: "000.000.000-00"
      candidates:
        - strategy: "label"
          selector: "label:has-text('CPF') + input"
          score: 0.95
        - strategy: "placeholder"
          selector: "[placeholder='000.000.000-00']"
          score: 0.85
      context:
        form: "Consulta de Cliente"
        url: "/consulta"
      post_action:
        expected_after: "Resultado da consulta visivel"
```

**Camada fina:** O MIS nao e um mega-schema. Captura o minimo necessario: acao, alvo semantico, candidatos (max 3-5), contexto, oracle esperado.

### 2.3 LocatorCandidateGenerator + Scorer

Gera multiplos candidatos de locator ordenados por score deterministico.

| Estrategia | Peso | Exemplo |
|-----------|------|---------|
| role + accessible_name | 0.95 | `getByRole('button', {name: 'Pesquisar'})` |
| label | 0.90 | `getByLabel('CPF')` |
| placeholder | 0.85 | `getByPlaceholder('000.000.000-00')` |
| test_id | 0.80 | `getByTestId('btn-pesquisar')` |
| visible_text | 0.70 | `text=Salvar` |
| stable_dom_attr | 0.60 | `[data-field='cpf']` |
| contextual_anchor | 0.50 | `form#consulta >> input` |
| css_simple | 0.30 | `.form-control` |
| xpath | 0.10 | ultimo recurso |

**Uniqueness:** cardinalidade, contexto, gap semantico, estabilidade cross-snapshot.

### 2.4 Compiler Playwright

Le `SemanticTestCase` → gera script Playwright Python com fallback loop.

**Template gerado (exemplo):**
```python
def test_consulta_cliente(page):
    # Step 1: fill CPF
    for _sel in ['[placeholder="000.000.000-00"]', 'label:has-text("CPF") + input']:
        try:
            page.fill(_sel, "12345678900")
            break
        except Exception:
            continue
    else:
        raise AssertionError("fill CPF falhou")
    
    # Step 2: click Pesquisar
    for _sel in ['button:has-text("Pesquisar")', 'getByRole("button", {name: "Pesquisar"})']:
        try:
            page.click(_sel)
            break
        except Exception:
            continue
    else:
        raise AssertionError("click Pesquisar falhou")
```

O script gerado e artefato derivado. Se o MIS mudar, o script e regenerado.

### 2.5 Runner + Fallback Loop

Executa o script Playwright. Se um passo falha:

| Layer | Custo | O que faz |
|-------|-------|-----------|
| **L0 — Recipe Catalog** | <50ms, jsonl | Match exato por familia + sintoma. Receitas pre-geradas por LLM ou seed manual. |
| **L1 — Specialist Agent** | ~200 tok | Agente por framework (PrimeFaces, Angular, jQuery UI). Ex: `_try_primefaces_select()` |
| **L2 — Evidence Collector** | sem LLM | Coleta DOM, screenshot, console, network, contexto do elemento |
| **L3 — LLM Healer** | ~500 tok | So quando L0-L2 falham. Recebe payload estruturado, nao prompt aberto |

**Fill Strategy (do projeto-anterior):**
1. Pre-check: ler `el.value` via JS — se ja igual, pular
2. `page.fill()` — rapido (15% timeout)
3. Re-check: se OK apos fill, pular
4. `pressSequentially` — digita caractere por caractere (30ms delay)
5. Native setter: `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)` + InputEvent + change

**PrimeFaces SelectOneMenu:**
1. `select_option(force=True)` no hidden `<select>`
2. Trigger click no `.ui-selectonemenu-trigger`
3. Item click no `.ui-selectonemenu-item` com `:has-text()`
4. JS setter: `sel.selectedIndex = i` + dispatch `change`

### 2.6 Self-Healing Pipeline

Quando o runner encontra falha no locator:

1. **Classificar falha** (taxonomia): locator_resolution, actionability, synchronization, oracle, environment, context
2. **Tentar fallback deterministico**: candidatos alternativos do MIS em ordem de score
3. **Re-executar com oracle**: so considera sucesso se oracle passar
4. **Registrar**: sugestao de healing, evidencias, oracles
5. **Promotion Gate**: experimental → shadow_validated → canary → trusted

**LLM so como curador:** off critical path, apenas quando deterministico esgota opcoes. Recebe `EvidencePackage` estruturado.

---

## 3. Stack Tecnologica

| Camada | Tecnologia | Justificativa |
|--------|-----------|--------------|
| Runtime | Python 3.10+ | Playwright API nativa, typer CLI, ast module |
| Browser | Playwright (Chromium) | API rica de eventos, `page.on()`, `add_init_script()` |
| CLI | Typer | Leve, rapido, Python nativo |
| Storage | JSONL + filesystem | Simples, auditavel, zero dependencia de DB no MVP |
| LLM (quando necessario) | OpenAI-compatible API | Azure, OpenAI, ou local |
| Testes | pytest + Playwright | Mesmo stack dos testes gerados |
| Serializacao | YAML (MIS) + JSONL (events) | Legivel, versionavel, diffable |

---

## 4. Diretorios Normativos

```
src/testforge/
├── recorder/          # Recorder Sensorial (Playwright nativo)
├── semantic/          # MIS: RecordingNormalizer, CandidateGenerator
├── compiler/          # PlaywrightPythonCompiler
├── runner/            # Runner + FallbackRunner
├── healing/           # Classifier, Curator, LLM Healer, Recipe Catalog
├── evidence/          # EvidenceCollector, EvidenceStore
├── oracle/            # OracleRunner (visual_dom, business_state)
├── promotion/         # PromotionGate
├── taxonomy/          # FailureTaxonomy, FailureClassifier
├── metrics/           # MetricsRepository
├── models/            # Dataclasses: Step, Test, Artifact, Fingerprint, etc
├── config/            # Loader, Defaults, Schema
├── cli/               # Comandos: record, run, report, healing
└── logging/           # Logger estruturado

recordings/            # Sessoes de gravacao (JSONL + screenshots)
semantic_tests/        # Contratos semanticos (YAML)
generated_tests/       # Scripts Playwright gerados (Python)
evidence/              # Evidencias de execucao (JSONL)
policies/              # Politicas versionadas (YAML)
schemas/               # Contratos de schema (YAML)
adrs/                  # Architecture Decision Records
synthetic_lab/         # App falsa + mutation matrix
tests/                 # Testes unitarios e integracao
```

---

## 5. ADRs (Architecture Decision Records)

### ADR-0001: Recorder via Playwright nativo, sem extensao browser

**Decisao:** Usar `page.on('pointerup')`, `page.on('input')`, `page.on('keydown')` nativos do Playwright. NAO usar extensao Chrome.

**Motivo:** Restricao de seguranca corporativa impede extensoes de browser. Playwright API e suficiente e mais controlavel.

**Consequencia:** Perde-se o overlay UI (botoes, painel) — usa-se modo `shortcuts` (apenas listeners). Ganha-se seguranca e simplificacao.

### ADR-0002: SemanticTestCase como fonte de verdade

**Decisao:** O contrato semantico (YAML) e a fonte de verdade do teste. O script Playwright Python e artefato derivado, regeneravel.

**Motivo:** Separar intencao de implementacao. Se o compiler melhorar, todos os scripts sao regenerados sem perder a intencao original.

### ADR-0003: JSONL + filesystem no MVP, sem SQLite

**Decisao:** Usar JSONL e diretorios para storage no MVP. SQLite para versao futura.

**Motivo:** Zero dependencias, auditavel via git diff, simples de debugar. JSONL permite append-only writes.

### ADR-0004: LLM apenas como curador, off critical path

**Decisao:** LLM so e acionado quando os Layers 0-2 (Recipe Catalog, Specialist Agent, Evidence Collector) falham.

**Motivo:** Custo, latencia, nao-determinismo. O healing primario deve ser deterministico e previsivel.

### ADR-0005: Fallback loop no codigo gerado

**Decisao:** O compiler gera `for/else/try/except/continue/break` no proprio script Playwright, tentando todas as strategies em ordem.

**Motivo:** O script gerado funciona standalone (via pytest) e tem fallback proprio sem depender do runner especializado.

---

## 6. Decisoes Pendentes

| # | Decisao | Impacto |
|---|---------|---------|
| 1 | SQLite vs JSONL para evidence store | Medio — JSONL funciona, SQLite escalaria melhor |
| 2 | Synthetic lab: React fake app ou PrimeFaces stub? | Alto — PrimeFaces e o target real, mas React e mais simples |
| 3 | Como lidar com CSP em aplicacoes reais | Alto — `add_init_script` pode ser bloqueado |
| 4 | Mascaramento de dados sensiveis: quando ativar? | Medio — MVP = alert_only |
| 5 | Pipeline CI: GitHub Actions ou Azure DevOps? | Baixo — ambos via pytest |
