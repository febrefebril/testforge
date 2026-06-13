# Pipeline de Curadoria — Visão Geral

> Pipeline de healing automático de scripts Playwright. Ordem: **Classifier → L1 (Catálogo) → L2 (Agentes) → L3 (LLM Healer)**.

---

## 1. Arquitetura

```
cure(step_data, error_message, evidence)
  │
  ├── 1. FailureClassifier.classify(error, evidence)
  │     ├── keyword matching  (regex, word-boundary, ~30 keywords) → confidence 0.9
  │     ├── group fallback    (SEL/TIM/INP/CTX/STA regex)         → confidence 0.7
  │     └── LLM fallback      (~100 tok JSON)                     → confidence variável
  │
  ├── 2. _try_layer1_catalog(family, step_data, evidence, error)
  │     └── HealingCatalog.match(family, error_message)
  │         → se achar entry com fix_type pre_populated|reviewed|learned → PULA
  │         → se falhar na execução → cai para L2
  │
  ├── 3. _try_layer2_agents(family, step_data, evidence, error)
  │     └── route_to_agent(family) → SelectorAgent|TimingAgent|...
  │         → agent.heal(evidence, error_message) → LLMHealingProposal
  │         → tenta executar step com proposal.new_locator
  │         → se PASSED_STEP → registra como learned, PULA
  │         → se falhar → cai para L3
  │
  └── 4. _run_healing_cycle(step_data, evidence, error)
        └── LLMHealer.heal_or_unresolved(evidence, error) → proposal
            → valida confiança >= 0.5
            → valida taxonomy_id/family contra FAMILIES/TAXONOMIES
            → tenta executar step patcheado
            → se PASSED_STEP → registra learned
            → se ERROR_CHANGED → retry recursivo (max depth 1)
            → se REGRESSED/STAGNATED → rollback
```

---

## 2. FailureClassifier (`classifier.py`)

### Keyword Matching

Lista ordenada por tamanho decrescente (longest match first). Usa word boundaries manuais:

```python
# Antes de aceitar match, verifica:
pos > 0 and msg_lower[pos - 1].isalnum()   → rejeita (prefixo colado)
end < len(msg) and msg_lower[end].isalnum() → rejeita (sufixo colado)
```

Isso previne falsos positivos como `"expect"` dentro de `"unexpected"`.

### Group Fallback

Regex por prefixo de taxonomy_id:

| Prefixo | Pattern | Family |
|---------|---------|--------|
| SEL | `timeout.*locator\|strict locator\|intercepted\|multiple elements` | FAM-01 |
| TIM | `loading\|stale element\|net::ERR_\|timeout\|wait` | FAM-02 |
| INP | `fill\|clear\|editable\|masked` | FAM-06 |
| CTX | `frame\|shadow\|cross-origin` | FAM-03 |
| STA | `dialog\|alert\|confirm\|session\|overlay` | FAM-04 |

### LLM Fallback

Prompt JSON (~100 tok). Só roda se `llm_healer` foi injetado. Parseia:

```json
{"family": "FAM-01", "taxonomy_id": "SEL-004", "confidence": 0.85}
```

Valida contra `FAMILIES`/`TAXONOMIES` — se family ou taxonomy_id não existir, retorna vazio.

### Retorno vazio

Se nada match, retorna `ClassificationResult(taxonomy_id="", family="", confidence=0.0, matched_by="")`. L1 e L2 são pulados (não há family para rotear), mas L3 roda igual.

---

## 3. Catálogo (L1)

**Arquivo:** `storage.py` (`HealingCatalog`)

**Matching:** exato por `family` + substring no campo `symptom` vs `error_message`.

**Fix types relevantes:** `pre_populated` (catálogo inicial), `reviewed` (aprovado manualmente), `learned` (aprendido por healing automático).

**Custo:** zero LLM, <50ms.

Se `step_runner` não está configurado, L1 sempre retorna PASSED_STEP sem executar (otimização para catálogo pré-povoado com fixes confiáveis).

---

## 4. Agentes Especialistas (L2)

Roteamento via `FAMILY_AGENT_MAP`:

| Family | Agent Key | Classe real | O que faz |
|--------|-----------|-------------|-----------|
| FAM-01 | `selector` | `SelectorAgent` | Fallback chain: `data-testid` > `id` > `name` > `aria-label` > `placeholder` > `has-text` > `href` > `alt` > `class` > XPath |
| FAM-02 | `timing` | `TimingAgent` | Detecta network errors → networkidle; senão → wait for visibility/function |
| FAM-03 | `context` | `ContextAgent` | iframe switch, shadow DOM, cross-origin, popup detection |
| FAM-04 | `state` | `StateAgent` | Dialog auto-accept, overlay close, session refresh |
| FAM-05 | `dynamic_dom` | `DynamicDOMAgent` | Stale element recovery, DOM reorder, lazy load wait |
| FAM-06 | `input` | `InputAgent` | Masked input → pressSequentially; file upload → setInputFiles; date picker |
| FAM-07 | `input` | `InputAgent` | Mesmo que FAM-06 (FILE mapeado para InputAgent) |

Todos os agentes em produção são **determinísticos** (zero LLM calls). A classe base `SpecialistAgent` requer implementação de `heal(payload, error_message) → LLMHealingProposal`.

**Nota:** FAM-08 (asserts) e FAM-09/10/11 não têm agentes — caem direto para L3.

---

## 5. LLM Healer (L3)

**Arquivo:** `llm/healer.py` (`LLMHealer`, `MockLLMHealer`)

### Ativação Automática

O LLM Healer real é ativado automaticamente quando as env vars `AZURE_OPENAI_KEY` e `AZURE_OPENAI_ENDPOINT` estão definidas. A detecção ocorre em `CuradorAutomatico.__init__()`:

```python
config = load_llm_config()  # lê AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_MODEL
if config.api_key and config.azure_endpoint:
    self.healer = LLMHealer(config)       # real Azure OpenAI
else:
    self.healer = MockLLMHealer()          # fallback determinístico
    logger.warning("AZURE_OPENAI_KEY/AZURE_OPENAI_ENDPOINT não definidos")
```

Sem essas env vars, o pipeline funciona normalmente com `MockLLMHealer` — propostas genéricas de baixa confiança, sem chamada externa.

### Prompts Especializados por Família

O `_build_prompt()` em `LLMHealer` aceita `family=""` e seleciona template de `FAMILY_PROMPTS` (11 prompts, cada um ≤1500 chars) se disponível. Cada prompt inclui:

- Estratégias válidas para aquela família
- Sintomas típicos
- Exemplo de resposta JSON esperada

Se a família não for conhecida, cai no template genérico `CURATION_PROMPT_TEMPLATE`.

### Agentes L2 com Fallback LLM

Todos os 6 agentes especialistas (`SelectorAgent`, `TimingAgent`, `InputAgent`, `ContextAgent`, `StateAgent`, `DynamicDOMAgent`) agora possuem `_llm_fallback()` no final do `heal()`. Quando as regras determinísticas do agente não produzem uma proposta de alta confiança (≥0.7), o fallback invoca o LLM via `_build_prompt()` do próprio agente.

### Pipeline dentro de `_run_healing_cycle`:

1. `healer.heal_or_unresolved(evidence, error_message)` → proposal
2. Se `proposal.confidence < 0.5` → UNRESOLVED
3. Se `proposal.family ∉ FAMILIES` ou `proposal.taxonomy_id ∉ TAXONOMIES` → UNRESOLVED
4. Patch: copia step_data, substitui `selector` por `proposal.new_locator`
5. Executa step patcheado via `step_runner`
6. Classifica resultado:
   - `PASSED_STEP` → registra learned no catálogo
   - `ERROR_CHANGED` (e não é retry) → retry recursivo (max 1, depth++)
   - `REGRESSED` ou `STAGNATED` → rollback (UNRESOLVED)

---

## 6. Contagem de Falhas e Review

Após `cure()`:

| Status | Ação |
|--------|------|
| `PASSED_STEP` | `catalog.reset_failure_count(taxonomy_id)` |
| `UNRESOLVED` | `catalog.increment_failure_count(taxonomy_id)` |

Se `count >= TF_REVIEW_THRESHOLD` (default 5):

- Tenta `notify_all()` (email + Teams) se configurado
- Fallback: `logger.warning` com mensagem

Persistência em sidecar: `<catalog_path>.meta.json`

```json
{
  "failure_counts": {"SEL-004": 3, "TIM-001": 7}
}
```

---

## 7. CLI — Filtros de Relatório

```bash
testforge report --history --taxonomy SEL-004 --family FAM-01
```

Flags:

- `--taxonomy`: filtra por taxonomy_id (exato)
- `--family`: filtra por family (exato)
- Output mostra tag `[FAM-01/SEL-004]` ao lado de cada entrada
- Extrai `classification_layer` e `classification_confidence` dos `CurationRecord`

---

## 8. Diagrama de Estados

```
                   ┌──────────┐
                   │  Error   │
                   └────┬─────┘
                        │
              ┌─────────▼─────────┐
              │   Classifier      │ ← keyword → group → LLM
              │  (family + tid)   │
              └─────────┬─────────┘
                        │
              ┌─────────▼─────────┐
         ┌────│   L1: Catalog     │──── family + symptom match?
         │    └─────────┬─────────┘
         │              │ fail
         │    ┌─────────▼─────────┐
         │    │  L2: Agent        │──── route_to_agent(family)
         │    └─────────┬─────────┘
         │              │ fail
         │    ┌─────────▼─────────┐
         │    │  L3: LLM Healer   │──── heal_or_unresolved()
         │    └─────────┬─────────┘
         │              │
         │    ┌─────────▼─────────┐
         │    │  Execute +        │
         └────│  Classify result  │
              └─────────┬─────────┘
                   │    │
            ┌──────┘    └──────┐
            ▼                   ▼
      PASSED_STEP          UNRESOLVED
      (reset count)        (increment count)
```

---

## 9. Casos Especiais

### L1 sem `step_runner`
Se `step_runner` não foi injetado, L1 pula a execução e retorna `PASSED_STEP` direto — útil para catálogo pré-povoado com fixes validados.

### Family vazia
Se classifier não achou family, L1 e L2 são pulados (`if family` guard). L3 roda normalmente.

### Proposal com taxonomy inválida
Agentes e LLM podem retornar proposals com `taxonomy_id`/`family` que não existem em `FAMILIES`/`TAXONOMIES`. Ambos os níveis filtram antes de executar.

### Rollback automático
Se o step patcheado resulta em `REGRESSED` ou `STAGNATED`, o outcome marca `rollback_applied=True` e o erro original é preservado.

---

## 10. Arquivos Relevantes

| Arquivo | Função |
|---------|--------|
| `core/healing/classifier.py` | `FailureClassifier`, keywords, groups, LLM fallback |
| `core/healing/curator.py` | `CuradorAutomatico.cure()`, pipeline orchestration, review threshold |
| `core/healing/storage.py` | `HealingCatalog`, persistence, failure counts |
| `core/healing/models.py` | `FAMILIES`, `TAXONOMIES`, `HealingEntry` |
| `core/healing/agents/__init__.py` | `route_to_agent()`, `FAMILY_AGENT_MAP` |
| `core/healing/agents/selector_agent.py` | `SelectorAgent` com fallback chain |
| `core/healing/agents/*_agent.py` | Demais agentes especialistas |
| `core/healing/llm/healer.py` | `LLMHealer`, `MockLLMHealer` |
| `core/healing/collector.py` | `EvidenceCollector`, `EvidencePayload` |
| `core/models/report.py` | `HealingSummary`, `LayersUsed`, `CurationRecord` |
| `core/cli/report.py` | `--taxonomy`/`--family` filters |
