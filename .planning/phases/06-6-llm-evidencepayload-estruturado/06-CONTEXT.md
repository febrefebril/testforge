# Phase 6: LLM EvidencePayload Estruturado - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Criar `EvidencePayload` dataclass que alimenta o LLM Healer (L3) com DOM snippet,
console errors, network state e screenshot base64. Adaptar `EvidenceCollector` com
método `build_llm_payload()` para gerar payloads estruturados sob demanda.

**Escopo:** Dataclass + sanitização + integração com coletor existente.
**Fora do escopo:** Chamada ao LLM (Fase 3), pipeline de cura (Fase 4).
</domain>

<decisions>
## Implementation Decisions

### D-01: Sanitização do DOM
- **Estratégia:** Head+tail 1500/1500 chars (total 3000 chars max)
- Remover tags `<script>` e `<style>` antes de truncar
- Não expor atributos `data-*` que contenham PII (cpf, email, token)
- Preservar estrutura HTML: manter tags abertas/fechadas balanceadas
- **Referência:** `projeto-anterior/llm/healer.py:_truncate_dom()`

### D-02: Evidência mínima (is_sufficient)
- **Critério:** DOM snapshot existe (≥100 chars) + pelo menos 1 fonte extra:
  - ≥1 console error, OU
  - ≥1 network request registrada, OU
  - Screenshot base64 presente
- Se DOM ausente ou vazio → `is_sufficient=False`, `insufficiency_reason="DOM snapshot missing"`
- Se DOM existe mas sem fontes extras → `is_sufficient=False`, `insufficiency_reason="Insufficient context"`
- **Referência:** `projeto-anterior/curator.py:cure()` — gate de evidência

### D-03: Console + Network — campos
- **Console errors:** `{text, level, timestamp}` — últimos 5 registros (nível error/warning)
- **Network state:** `{method, url, status, timing_ms}` — últimas 3 requisições
- `level` filtra warnings vs errors para o LLM priorizar
- `timestamp` dá ordem cronológica dos eventos
- `timing_ms` ajuda diagnóstico de lentidão
- URLs truncadas em 120 chars para evitar tokens excessivos
- **Referência:** `projeto-anterior/llm/healer.py:_build_prompt()`

### D-04: Integração com EvidenceCollector
- **Abordagem:** Novo método `build_llm_payload(step_context: dict) -> EvidencePayload` no `EvidenceCollector` existente
- Coletor já tem acesso à `page` (Playwright), screenshots, DOM, network log
- Método monta payload sob demanda — não pré-coleta
- Screenshot base64 via `page.screenshot(type="png")` — opcional, controlado por flag `include_screenshot`
- **Arquivo:** `src/testforge/evidence/evidence_collector.py`
- **Novo arquivo:** `src/testforge/healing/evidence_payload.py` (dataclass)

### the agent's Discretion
- Ordem dos campos no payload (dom, console, network, screenshot) — agente decide
- Nomes exatos de atributos no dict `step_context` — agente decide baseado no uso existente
- Threshold exato de chars para `is_sufficient` (≥100 chars DOM) — agente ajusta se necessário
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Architecture
- `.planning/PROJECT.md` — Visão geral, stack, princípios (determinístico primeiro, LLM off critical path)
- `.planning/REQUIREMENTS.md` — R4: Self-Healing com 4 layers, R5: Evidence + Oracle
- `.planning/ROADMAP.md` — M9: LLM Self-Healing L3, Fase 9.2

### Reference Implementation (projeto-anterior)
- `conhecimento_ancestral/projeto-anterior/packages/core/testforge/core/healing/llm/healer.py` — `_truncate_dom()`, `_build_prompt()`, `LLMHealer`, `MockLLMHealer`
- `conhecimento_ancestral/projeto-anterior/packages/core/testforge/core/healing/collector.py` — `EvidencePayload`, `EvidenceCollector`
- `conhecimento_ancestral/projeto-anterior/docs/pipeline-overview.md` — Pipeline L0→L3, integração

### Planning Docs
- `.planning/EPICOS-STORIES.md` — EP-09: US-09.02 (EvidencePayload), US-09.03 (LLMClient)
- `.planning/SPRINT-PLANNING.md` — Sprint 9, tarefas T-09.02.01 a T-09.02.04
- `docs/diagramas/componentes-llm-healing.puml` — Mapa L0-L3, módulo EvidencePayload
- `docs/diagramas/classes-llm-healing.puml` — Dataclasses: EvidencePayload, LLMHealingProposal

### Existing Code
- `src/testforge/evidence/evidence_collector.py` — `EvidenceCollector` existente (capture_dom, capture_screenshot, capture_network_log)
- `src/testforge/taxonomy/taxonomy.py` — `FailureClassifier`, `FailureClassification` (já expandido Fase 1)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`EvidenceCollector`** (`src/testforge/evidence/evidence_collector.py`): Já possui `capture_dom()`, `capture_screenshot()`, `capture_network_log()`. Adicionar `build_llm_payload()` que compõe esses artefatos.
- **`EvidencePackage`** (`src/testforge/evidence/evidence_collector.py`): Dataclass existente com `steps`, `screenshot_paths`, `dom_paths`, `network_log`. O novo `EvidencePayload` é um subconjunto focado no LLM.
- **`FailureClassification`** (`src/testforge/taxonomy/taxonomy.py`): Já possui `family`, `code`, `taxonomy_id`, `confidence`, `matched_by`. O `EvidencePayload.step_context` referencia esses campos.

### Established Patterns
- **Dataclasses com `to_dict()`/`from_dict()`:** Padrão usado em `HealingRecipe`, `EvidencePackage`. Seguir mesmo padrão no `EvidencePayload`.
- **JSONL + filesystem:** Storage sem DB. Payload é efêmero (não persiste em disco — só o manifest).
- **Sanitização por truncagem:** Padrão do `_truncate_dom()` do projeto anterior. Preservar head+tail.

### Integration Points
- **`EvidenceCollector` → `EvidencePayload`:** Método `build_llm_payload(ctx)` lê artefatos já coletados e monta payload.
- **`EvidencePayload` → `LLMHealer` (Fase 3):** Payload é entrada do `heal(payload, error_message, family)`.
- **`EvidencePayload` → `CuradorAutomatico` (Fase 4):** `cure()` recebe payload como parâmetro.
- **`cmd_run` → `EvidenceCollector.build_llm_payload()` (Fase 5):** CLI chama coletor após falha do pytest.
</code_context>

<specifics>
## Specific Ideas

- Screenshot base64: incluir apenas se `include_screenshot=True` (default False). Screenshots grandes consomem tokens.
- `step_context` dict: incluir `action`, `selector`, `value`, `intention`, `url`, `framework`, `tag_name`, `family`, `taxonomy_id`.
- DOM snapshot: usar `page.content()` do Playwright (já disponível no coletor).
- Console errors: acessar via `page.on("console")` — registrar no coletor durante execução.
- Network state: acessar via `page.on("response")` — registrar no coletor durante execução.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 6-LLM EvidencePayload Estruturado*
*Context gathered: 2026-06-15*
