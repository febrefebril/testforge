# Plano de Correção de Rota — Arquitetura TestForge vs Estado da Arte (2026)

**Data:** 2026-06-24
**Autor:** análise técnica
**Branch base:** `refactor/recorder-playwright`
**Pesquisa de referência:** [.planning/research-modern-healing-tools.md](research-modern-healing-tools.md)

---

## 0. Diagnóstico em uma frase

> TestForge tenta resolver no Python o que o ecossistema moderno (Playwright codegen + AX tree + MCP/Stagehand) já resolve no protocolo do navegador. O resultado é um pipeline de 1.300 linhas (`recording_normalizer.py`) que **reimplementa, pior, o que Playwright codegen produz em ~80 linhas de configuração**, e ainda assim cada passo gravado quebra na reprodução.

A causa primária dos passos não passarem **não é falta de healing**. É:

1. **A camada de captura** (JS overlay + sessionStorage) é incompleta e perde estado (shadow DOM, iframes, eventos sintéticos, navegação).
2. **A camada de extração de seletor** (16 estratégias hand-rolled em `_build_target`) gera candidatos como **strings planas** sem identidade estável — quando o DOM muda 5%, todos os candidatos quebram juntos.
3. **A camada de fallback** está **hard-coded no script Python gerado** (try/except aninhados). Não dá para iterar/melhorar o fallback sem recompilar todos os testes.
4. **O healing L0/L2/L3** opera por *casamento de mensagem de erro* (substring), não por *intenção* — então ele aprende sintomas, não conceitos.

Isso configura quatro anti-padrões clássicos de design:

| Anti-padrão | Onde aparece | Sintoma |
|---|---|---|
| **Reinventando a roda** | `recording_normalizer.py:1184-1368` reimplementa o que `playwright codegen` faz | Bugs de bordo (Angular Material, mat-select, postback) viram fixes manuais infinitos |
| **God Object** | `RecordingNormalizer` faz: load, dedup, compact, intent reconstruction, scoring, ranking, compound candidates, blind-spot audit | Mudança em um lugar quebra outro — `BUG-FIX-PLAN.md` tem 47KB |
| **Tight coupling no artefato gerado** | `compiler.py` emite try/except inline; runtime não pode trocar estratégia sem regenerar `.py` | A cada mudança no fallback você reprocessa todos os testes |
| **Abstração errada do seletor** | `LocatorCandidate` é `(strategy: str, value: str, score: float)` | Sem `backendNodeId`, sem `ax_path`, sem `intent_text` — o catálogo L0 não sabe o que está rejeitando |

Resultado prático: 16 estratégias × 10 estratégias de runtime × 6 agentes L2 × 1 LLM = **muitos níveis, pouca convergência**. Cada nível introduz bugs próprios (BUG-FIX-PLAN cita 16 bugs em 1 sprint). É o que o paper arXiv 2603.20358 (mar/2026) chama de "self-healing inflation": time gasta corrigindo o healer, não o teste.

---

## 1. Comparativo direto: TestForge × ferramentas modernas

### 1.1 Captura de evento

| Aspecto | TestForge atual | Playwright codegen | Playwright MCP | Stagehand | browser-use |
|---|---|---|---|---|---|
| Transporte | JS injection + sessionStorage polling (`overlay_inject.js`) | CDP nativo | MCP server + CDP | CDP (v3) | CDP raw |
| Snapshot por ação | DOM HTML (texto) | AX tree YAML (3 snapshots: before/at/after) | AX tree YAML com `[ref=eN]` | AX tree estruturada | super-selector `(targetId, frameId, backendNodeId, position, fallback)` |
| Eventos especiais | click/fill/keypress/submit/postback (manuais) | tudo via tracing | tudo | tudo | tudo |
| Identidade do nó | XPath + atributos extraídos do JS | nenhuma persistente (regenera no replay) | `[ref=eN]` válido só na sessão | resolvido por intent | `backendNodeId` persistente na sessão |
| Shadow DOM / iframe | Auditado mas heurístico (`recorder_controller.py`) | suporte nativo | suporte nativo | suporte nativo | suporte nativo |
| Custo de manutenção | **Alto** (JS injetado precisa rastrear mudanças em frameworks) | Zero (mantido pela Microsoft) | Zero | Zero | Médio |

**Crítica:** TestForge mantém JS injetado próprio em vez de usar `playwright codegen` ou um trace `.zip`. Cada framework novo (Angular Material, PrimeFaces, React MUI) virou um *handler* manual (5 arquivos em `handlers/`). Isso **não escala**.

### 1.2 Extração de candidatos

| Aspecto | TestForge | Playwright codegen | mabl | Testim | Healenium | Stagehand |
|---|---|---|---|---|---|---|
| Estratégia | 16 heurísticas em Python | 8 priorizadas (role>label>placeholder>testid>css) | 30+ atributos + ancestor N níveis | "centenas" + pesos aprendidos | XPath + per-node attrs (LCS depois) | role/name via AX tree |
| Forma do candidato | `(strategy, value: str, score)` | string Playwright-locator | dict de atributos + history | dict + score 0-100 | XPath + attr snapshot | intent + cache do call resolvido |
| Compound | sim (`_compound_candidates`) | encadeamento `.filter().getBy()` | sim (subset estável) | sim | não | sim |
| Score | determinístico, hand-tuned (0.10-0.95) | implícito (primeiro que casa) | per-attr stability | numérico exposto (70% threshold) | weighted LCS | confiança da LLM |
| Stable id | **não tem** | não tem | `data-mabl-element-id` interno | id interno | XPath canonical | intent text + URL signature |

**Crítica:** o `LocatorCandidate` de TestForge é **mais rico que codegen** (compound + scoring) mas **mais pobre que todos os comerciais** (sem ancestor, sem `backendNodeId`, sem score por atributo). Pior: o score é hand-tuned (`0.95`, `0.92`, `0.87`...) sem dado para calibrar. Isso é **magic number** clássico.

### 1.3 Ordenação e fallback chain

| Aspecto | TestForge | Stagehand | Playwright MCP | Healenium |
|---|---|---|---|---|
| Onde mora a chain | **Hard-coded no .py compilado** (`compiler.py:538-678`) | runtime (cache → LLM) | runtime (ref → fallback) | runtime (LCS → DB) |
| Trocar a chain | regerar TODOS os testes | mudar config | mudar config | mudar config |
| Logs do que tentou | só dá pra ver no traceback | trace estruturado | trace MCP | DB com confidence |
| Aprende a chain | catalog L0 aprende sintomas (`record_success`), não ordem | cache de intent → resolved call | snapshot por ação | DB com heal history |

**Crítica:** essa é provavelmente a maior dor estrutural. Cada teste compilado **congela a estratégia daquele dia**. Quando você melhora a chain (ex: nova heurística para mat-select), os testes antigos não pegam o ganho. É como compilar a query SQL no aplicativo em vez de mandar pro banco em runtime.

### 1.4 Healing

| Camada | TestForge | Stagehand | mabl | Healenium | arXiv 2603.20358 |
|---|---|---|---|---|---|
| Cache (L0) | JSONL com substring de erro | intent + URL → call resolvido | element history | Postgres com per-attr snapshot | AX-tree priority hierarchy |
| Determinístico (L1+L2) | 6 agentes + 10 estratégias SmartStepRunner | n/a | per-attr stability rerun | LCS weighted | re-extract só o quebrado |
| LLM (L3) | Azure GPT-4.1-mini | GPT-4 mini com cache | "generative auto-heal" | n/a | **zero LLM** (100% pass em 31 testes) |
| Persistência do heal | JSONL append | cache key | UI mabl | Postgres + dashboard | recomputa do AX tree |
| Reviewer humano | não tem | não tem | sim | sim | n/a |

**Crítica:** TestForge fica entre dois mundos. O catálogo L0 imita Healenium mas sem o rigor (substring vs LCS+atributos). O L3 imita Stagehand mas sem o cache de intenção. **Nenhuma das duas analogias está terminada**, e os bugs vivem no meio.

### 1.5 Saúde do código

Olhando os números:

- `recording_normalizer.py`: **1.368 linhas, 16 estratégias, ~80 branches**. Não é só god object — é god module.
- `compiler.py`: **678+ linhas emitindo Python como string**. Toda mudança de chain altera a string. Toda mudança na string vira teste novo (`BUG-FIX-PLAN.md` aponta 7 bugs SEL-004).
- `BUG-FIX-PLAN.md`: **47 KB**, 9 bugs ativos + 6 fechados na branch. Sinaliza ciclo curto fix→break→fix.
- `healing-catalog.jsonl`: **291 entradas** no projeto + **175** em test_pages. Sem dedup nem TTL.
- `recordings/` + `runs/`: artefatos crescem sem rotação.

---

## 2. O que TestForge faz BEM (não jogar fora)

Antes do plano de migração, registrar o que está validado pelo estado da arte:

1. **Pipeline staircase L0→L3** — é o padrão moderno (Stagehand, Healenium, arXiv 2603.20358 confirmam). Manter.
2. **Taxonomia de 11 famílias × 88 códigos** — nenhuma ferramenta comercial publica taxonomia tão granular. Manter; vai virar feature de produto.
3. **`get_by_role` fuzzy com regex (L0.5)** — não existe em ninguém. Manter, virar opção configurável.
4. **Intent reconstruction (Sprint 4)** — `value_mutations` + `snapshot_diff` + `form_values` + `network_payload` é uma boa ideia. Manter, mas mudar o transporte (ver §3.1).
5. **Readiness Gate com 5 critérios + relatório md** — UX boa, não jogar fora.

---

## 3. Plano de migração em 8 fases

**Princípio guia:** *deletar antes de adicionar*. Cada fase substitui código próprio por biblioteca/protocolo estável. Em ordem decrescente de ROI.

> Cada fase é uma branch independente, mergeable separadamente, com testes de regressão. Nenhuma fase quebra a anterior — feature-flag até cutover.

---

### Fase 1 — Substituir overlay JS por captura via Playwright Tracing + CDP (ROI altíssimo)

**Problema atual:** `overlay_inject.js` (530 linhas), `recorder_controller.py` polling sessionStorage. Bugs: postback IE, contenteditable mutation timing, shadow DOM, value setters interceptados de forma frágil.

**Substituir por:**

- **`playwright.context.tracing.start({ snapshots: true, sources: true })`** — Playwright já grava DOM antes/durante/depois de cada ação, network, console, screenshots, em um `.zip`.
- **`page.on('request' | 'response' | 'console' | 'dialog')`** — eventos nativos em vez de polling.
- **`CDPSession` direto** para `Accessibility.getFullAXTree()` e `DOM.getDocument({ pierce: true })` — pega shadow DOM e iframes sem heurística.
- **Manter** somente um overlay JS mínimo (≤50 linhas) que **só** captura eventos do usuário (mouse/keyboard) — não snapshot, não atributo, não estado. O snapshot vem do CDP em paralelo.

**Bibliotecas:**
- `playwright` 1.50+ (já temos)
- usar `page.context().new_cdp_session(page)` para CDP raw quando necessário

**O que deletar:**
- `_extractTarget()`, `_extractValue()`, MutationObserver de contenteditable, Proxy hooks de `HTMLInputElement.prototype.value`, postback detection — Playwright tracing já entrega tudo isso.

**O que ganhar:**
- Shadow DOM e iframe corretos out-of-the-box.
- DOM snapshots antes/durante/depois (3 por ação) em formato Playwright trace — abre em `trace.playwright.dev` para triagem.
- Network/console correlacionados por timestamp sem código próprio.

**Esforço:** 1-2 sprints. Alto ROI.

---

### Fase 2 — Substituir extração de seletores hand-rolled por Playwright codegen + AX tree

**Problema atual:** `recording_normalizer.py:1184-1368` tem 16 estratégias, magic numbers, regras por framework. **Reinventa codegen.**

**Substituir por:**

- **Playwright codegen como motor de extração** — invocar via API (`page.locator().get_attribute()` + `internal/locatorGenerator`) ou simplesmente chamar `npx playwright codegen` em modo headless e capturar o output.
- **AX tree YAML do CDP** como representação intermediária. Cada ação grava o snapshot AX no estilo Playwright MCP: cada elemento com `[ref=eN]`, role, name, state, parent path.
- **Estrutura nova do candidato** (super-selector tuple, inspirado em browser-use + mabl):

```python
@dataclass
class LocatorCandidate:
    # Identidade estável intra-sessão
    backend_node_id: int        # CDP — único na sessão
    frame_id: str               # CDP

    # Localizador Playwright nativo (prioritário)
    playwright_call: str | None # ex: "get_by_role('button', name='Salvar')"

    # AX tree
    role: str
    accessible_name: str | None
    ax_path: list[str]          # caminho de roles na árvore

    # Atributos completos (snapshot mabl-style)
    attributes: dict[str, str]  # 30+ atributos
    ancestor_roles: list[str]   # roles dos 5 antecessores
    visible_text: str | None

    # Localizadores derivados (fallback)
    css_candidates: list[tuple[str, float]]   # CSS + score
    xpath: str
    test_id: str | None

    # Per-attribute confidence
    attribute_stability: dict[str, float]   # ex: {"id": 0.3, "aria-label": 0.9}

    # Cache key
    intent_text: str            # ex: "click save button in dialog"
```

**Bibliotecas:**
- Já temos `playwright` — usar a API nativa de locator generation.
- Considerar `playwright-mcp` (Microsoft) como referência de YAML AX format. Não precisa rodar MCP server, só copiar o formato.

**O que deletar:**
- `_build_target` inteiro (1.184-1.368) — ~200 linhas vão pra fora.
- `_attr_css_variants`, `_compound_candidates`, regras Angular Material hard-coded.

**O que ganhar:**
- Playwright codegen é mantido pela Microsoft. Bugs futuros viram bugs da Microsoft, não nossos.
- AX tree YAML é o formato que LLMs (L3) consomem hoje sem tradução.
- Candidate tem identidade (`backend_node_id`) que sobrevive a mutações cosméticas.

**Esforço:** 2-3 sprints. ROI altíssimo.

---

### Fase 3 — Mover fallback chain do .py compilado para runtime configurável

**Problema atual:** `compiler.py` emite try/except aninhados no script. Cada teste congela a estratégia daquele dia.

**Substituir por:**

- **Compilador emite só a intenção semântica** + lista de candidates serializada (JSON inline ou arquivo paralelo).
- **Runtime resolve** chamando um `LocatorResolver` único, configurável, versionado.

Estrutura proposta do script compilado:

```python
# semantic_tests/ST-foo/test_st_foo.py
from testforge.runtime import step, resolver

def test_foo(page):
    step.go(page, "http://localhost:8765")
    step.click(page, intent="login button",
               candidates_file="step_001.json")  # << só intent + candidates
    step.fill(page, intent="username", value="alice",
              candidates_file="step_002.json")
```

`step.click()` chama `LocatorResolver.resolve()` que **em runtime**:

1. L0: lookup por `intent_text` no catálogo (cache à la Stagehand).
2. L1: percorre `candidates` ordenados por `attribute_stability`.
3. L2: dispara agente especialista pela família detectada.
4. L3: chama LLM com **YAML AX tree + intent** (não DOM HTML cru).
5. **Persiste o caminho que funcionou** com confidence + atributos que mudaram.

**Bibliotecas:**
- Nada novo. Só refatoração interna.

**O que deletar:**
- `_fallback_selector()`, `_top_selectors()`, todos os emissores de string-Python no `compiler.py`.

**O que ganhar:**
- Mudou a chain? Reinicia o runtime. Testes antigos pegam o ganho sem recompilar.
- Trace estruturado de qual nível resolveu (telemetria fica trivial).
- Compiler vira ~100 linhas (era 678+).

**Esforço:** 2 sprints. ROI alto.

---

### Fase 4 — Redesenhar o catálogo L0: intent-keyed, não substring-keyed

**Problema atual:** `HealingCatalog.match_recipes` casa por substring no error_message + código de família. Aprende sintomas, não conceitos.

**Substituir por:** chave composta `(intent_text_normalized, url_signature, action_type)`, à la Stagehand cache.

Estrutura nova:

```jsonc
{
  "intent_text": "click save button in dialog",
  "url_signature": "host=app.example.com path=/orders/* hash=*",
  "action": "click",
  "resolved": {
    "playwright_call": "get_by_role('button', name='Salvar')",
    "fallback_chain_taken": ["L0_miss", "L1_candidate_2", "L2_state_agent"],
    "confidence": 0.92,
    "attributes_at_heal": { "aria-label": "Salvar", "data-testid": null },
    "attributes_at_first_record": { "aria-label": "Save", "data-testid": "save-btn" }
  },
  "usage_count": 14,
  "success_count": 13,
  "last_used": "2026-06-24T12:00:00Z"
}
```

**Por que importa:** o mesmo intent ("click save button in dialog") em duas páginas diferentes do mesmo app vira **um único** registro, não dois. Quando a UI muda o label de "Save" para "Salvar", **um heal** resolve para todos os testes que usam aquele intent.

**Bibliotecas:**
- `sqlite3` (stdlib) substituindo JSONL para queries indexadas. Permanece migrável para Postgres se escala exigir (Healenium pattern).

**O que deletar:**
- `HealingCatalog.match_recipes()` substring matching. Vira lookup indexado por intent.

**Esforço:** 1-2 sprints. ROI médio-alto.

---

### Fase 5 — Refatorar `RecordingNormalizer` (God Module) — separação por responsabilidade

**Problema atual:** 1.368 linhas com:

1. IO de jsonl
2. dedup de snapshots
3. compactação de keypress
4. compactação de fill
5. conversão raw→semantic
6. intent reconstruction (4 estratégias)
7. blind-spot audit (shadow/iframe/mask)
8. detecção de overlay/dependency/navigation
9. scoring + ranking + compound

Quebrar em módulos com **interfaces claras** (Strategy + Pipeline patterns):

```
src/testforge/semantic/
├── pipeline.py            # orquestrador (50 lines)
├── stages/
│   ├── load.py            # IO
│   ├── dedup.py           # snapshot + event dedup
│   ├── compact.py         # keypress + fill collapse
│   ├── convert.py         # raw → semantic
│   └── audit.py           # blind-spots
├── intent/
│   ├── reconstructor.py   # já existe, só consumir Pipeline
│   └── strategies/        # snapshot_diff, form_values, network_payload, polling
├── locator/
│   ├── extractor.py       # Playwright codegen wrapper (Fase 2)
│   ├── scorer.py          # attribute_stability per-field
│   └── compound.py        # compound builder
└── model.py               # SemanticTestCase, SemanticAction, LocatorCandidate
```

Cada stage é uma classe com `def run(self, ctx: Context) -> Context`. Pipeline é uma lista de stages. Testar uma stage isolada vira trivial. Adicionar uma stage nova (ex: detector de tabela) não toca as outras.

**Padrão:** Pipes & Filters / Chain of Responsibility.

**Bibliotecas:**
- `pydantic` v2 (já é dependência indireta via Playwright) para `Context` validado entre stages.

**Esforço:** 2 sprints. ROI estrutural.

---

### Fase 6 — Trace Viewer + telemetria estruturada (substitui readiness_report.md como única visualização)

**Problema atual:** `readiness_report.md` por gravação. Bom pra triagem manual, ruim para escala.

**Adicionar:**

- **Exportar trace Playwright nativo** (`.zip`) por execução. Abre direto em `trace.playwright.dev` — ninguém precisa instalar nada.
- **OpenTelemetry** com span por step + atributo `resolved_at_level=L0|L1|L2|L3` + `attribute_changed=aria-label`. Exporta JSON ou para coletor (Jaeger, Honeycomb, etc).
- **`reports/dashboard.html` estático** servindo o resumo agregado, com gráficos via `chart.js` (zero infra).

**Bibliotecas:**
- `opentelemetry-api` + `opentelemetry-sdk` (OSS) — exporter JSON local sem servidor.

**Esforço:** 1 sprint. ROI moderado.

---

### Fase 7 — Substituir 5 ComponentHandlers por extensão do AX tree mapping

**Problema atual:** `handlers/` virou catch-all para frameworks (Angular Material, PrimeFaces, React MUI). Cada um repete o problema de "como localizar elemento composto?".

**Substituir por:**

- **AX tree já traz `role=combobox`, `role=listbox`, `aria-controls`** corretamente para mat-select e ui-selectonemenu desde 2024 (Angular Material 18+, PrimeFaces 14+).
- **Mapeamento declarativo** em vez de handler-por-framework:

```yaml
# config/component_patterns.yaml
- name: "Material Select"
  detect:
    role: combobox
    has_attribute: "aria-controls"
  open:
    action: click
    target: self
  pick:
    role: option
    by: accessible_name == "{value}"
```

Um único `ComponentResolver` lê esse YAML e roda em runtime. Adicionar PrimeFaces vira **5 linhas de YAML**, não 200 linhas de Python.

**Esforço:** 1 sprint depois da Fase 2 (AX tree disponível).

---

### Fase 8 — L4 visão (opcional, baixa prioridade)

**Apenas se**, após as fases 1-7, ainda houver falhas de canvas/Flash/legacy. Adicionar:

- **`screenshot_path` por candidato** já é fácil (Playwright tem `element.screenshot()`).
- **Template matching com OpenCV** (`cv2.matchTemplate`) como L4 antes do LLM-vision (Skyvern style).

Não é prioritário — paper arXiv 2603.20358 mostra que AX tree resolve 100% dos 31 testes sem visão.

---

## 4. Tabela executiva — mudanças concretas por arquivo

| Arquivo / módulo | Ação | Fase |
|---|---|---|
| `recorder/overlay_inject.js` | Reduzir de 530 para ≤50 linhas (só mouse/keyboard) | 1 |
| `recorder/recorder_controller.py` | Substituir polling sessionStorage por `tracing.start` + CDP events | 1 |
| `semantic/recording_normalizer.py` | Quebrar em 8 módulos (`semantic/stages/`, `semantic/locator/`) | 5 |
| `semantic/recording_normalizer.py:1184-1368` (`_build_target`) | Deletar; substituir por `locator/extractor.py` usando Playwright codegen + AX tree | 2 |
| `semantic/compiler.py:538-678` | Deletar emissão de try/except; emitir só intent + candidates JSON | 3 |
| `semantic/compiler.py` | Encolher de 678 para ~100 linhas | 3 |
| `runner/fallback_runner.py` | Virar `runtime/resolver.py` (LocatorResolver L0→L3) | 3 |
| `healing/healing_catalog.py` | Migrar de JSONL substring → SQLite intent-keyed | 4 |
| `handlers/*.py` (5 arquivos) | Deletar; substituir por `config/component_patterns.yaml` + 1 ComponentResolver | 7 |
| `validation/readiness_gate.py` | Manter; adicionar exportação OpenTelemetry | 6 |
| `metrics/pilot_metrics.py` | Adicionar dashboard.html estático | 6 |

**Linhas removidas estimadas:** ~3.000. **Linhas adicionadas:** ~800. **Net delete:** ~2.200 linhas, todas substituídas por libs/protocolos estáveis.

---

## 5. Stack final recomendada

| Camada | Hoje | Proposto |
|---|---|---|
| Captura | JS overlay próprio + sessionStorage | `playwright.tracing` + CDPSession nativo |
| Snapshot | DOM HTML em texto | AX tree YAML (formato Playwright MCP) |
| Identidade do elemento | XPath + atributos | `backendNodeId` + `(role, name, ax_path)` + 30 atributos |
| Extração de seletor | 16 heurísticas em Python | Playwright codegen API + AX tree |
| Score | hand-tuned magic numbers | per-attribute stability + intent confidence |
| Fallback chain | hard-coded no .py | runtime `LocatorResolver` configurável |
| L0 cache | JSONL substring | SQLite intent-keyed |
| L1 candidates | flat strings | super-selector tuple |
| L2 agents | 6 (manter) | 6 + ComponentResolver YAML-driven |
| L3 LLM | gpt-4.1-mini com prompt template | gpt-4.1-mini com **AX tree YAML + intent** (mais barato e preciso) |
| Telemetria | readiness_report.md | OpenTelemetry + Playwright trace.zip + dashboard.html |
| Persistência | JSONL no FS | SQLite + JSONL exportável |

---

## 6. Ordem de execução sugerida (8 sprints, ~12 semanas)

```
Sprint 1-2: Fase 1  (captura via Playwright tracing/CDP)
Sprint 3-5: Fase 2  (extração via codegen + AX tree, novo LocatorCandidate)
Sprint 6-7: Fase 3  (runtime LocatorResolver, compilador encolhido)
Sprint 8:   Fase 4  (catálogo L0 intent-keyed em SQLite)
Sprint 9-10: Fase 5 (refatoração RecordingNormalizer em stages)
Sprint 11:  Fase 6  (OpenTelemetry + trace viewer + dashboard)
Sprint 12:  Fase 7  (ComponentResolver YAML)
Fase 8:     backlog (visão opcional)
```

**Feature flag em cada fase:** `--use-new-recorder`, `--use-new-locator`, `--use-runtime-chain`. Rodar em paralelo até paridade nos 194 testes atuais, depois cutover.

---

## 7. Métricas de sucesso (gate por fase)

| Métrica | Hoje (estimado) | Meta pós-migração |
|---|---|---|
| % de passos que passam na primeira execução pós-record | <50% (fonte: queixa do usuário) | >85% |
| Taxa L0/L1/L2/L3 (distribuição) | desconhecida | L0+L1 ≥ 80%, L3 ≤ 5% |
| Tempo médio de healing por step | ~500ms (LLM) | ≤100ms (intent-cache hit) |
| Linhas de código próprias no pipeline de seletor | ~3.000 | ≤800 |
| Bugs abertos no BUG-FIX-PLAN | 9 ativos | ≤2 |
| Custo LLM por execução (1000 steps) | ~$0.50 | ≤$0.05 |

---

## 8. O que **NÃO** mudar

Para reduzir risco e preservar valor:

- **Taxonomia de 11 famílias + 88 códigos** — único diferencial vs comerciais. Manter, exportar como JSON Schema, virar feature.
- **Intent reconstruction (4 estratégias)** — boa ideia, só mudar transporte de dados (Fase 1).
- **Readiness Gate UX** — `READY/REVIEW/FAIL` + relatório md ficam.
- **CLI argparse** — funciona. Não migrar para Typer/Click sem necessidade.
- **MockLLMHealer offline** — diferencial real, manter.
- **Storage layout** (`recordings/`, `semantic_tests/`, `reports/`) — só adicionar `traces/` ao lado.

---

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Quebrar os 194 testes durante migração | Feature flag por fase; runs paralelos comparando outputs até paridade |
| Perder o diferencial "self-healing determinístico" | L2 (6 agentes) e taxonomia continuam — só muda a forma como L1 alimenta L2 |
| Dependência maior do Playwright (que pode mudar API) | Pin de versão; encapsular CDP raw em adapter testável |
| AX tree não exposto consistentemente em todos os frameworks | Manter fallback CSS (mais simples que hoje, mas presente) |
| Time precisa aprender Playwright tracing + CDP | 1 ADR + 1 doc + um pareamento por fase |

---

## 10. Decisões que precisam de aprovação antes de começar

1. **Mover catálogo de JSONL para SQLite** — implica migração de dados existentes. OK aprovar?
2. **Compilador emite candidates como JSON ao lado do .py** — quebra reprodução de testes antigos sem migrar. Estratégia: script de migração automático.
3. **Substituir `handlers/` por YAML** — deleta código de Sprints 1-6 do M12 (v0.4.1). OK aprovar?
4. **Adicionar OpenTelemetry como dep** — primeira dep "pesada". OK?
5. **Manter MockLLMHealer ou tornar o L3 configurável (incluindo "nenhum")** — paper arXiv 2603.20358 mostra 100% sem LLM em 31 testes. Considerar L3 opcional.

---

## Apêndice A — Por que cada caminho atual quebra

Para fechar com prova concreta, três falhas comuns que o desenho atual garante:

**Falha 1: SELECT muda valor mas mantém label.** Hoje: 16 candidatos baseados em label/name. Label muda no deploy → todos quebram. Pós-migração: `backend_node_id` válido na sessão + AX tree `role=combobox` → resolve em L1 sem precisar de catálogo.

**Falha 2: Botão "Salvar" virou ícone só.** Hoje: candidato `text=Salvar` quebra, `aria-label=Salvar` salva se existir, senão falha L0-L2. Pós-migração: `attribute_stability` rebaixa peso de `text` no record, prioriza `role=button + aria-label`; intent-cache hit no L0 do segundo run em diante.

**Falha 3: Mat-dialog abre e elemento é o `Salvar` interno.** Hoje: precisa de `AngularMaterialHandler` próprio. Pós-migração: `ancestor_roles=[..., dialog]` resolve disambiguação via `page.get_by_role('dialog').get_by_role('button', name='Salvar')` — Playwright codegen já gera esse encadeamento.

---

**Fim do plano.** Recomendação: aprovar Fases 1-3 como bloco mínimo viável; reavaliar 4-8 depois de medir o ganho da Fase 3.
