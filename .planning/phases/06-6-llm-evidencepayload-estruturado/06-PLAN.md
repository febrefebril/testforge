# Phase 6: LLM EvidencePayload — PLAN.md

**Created:** 2026-06-15
**Source:** 06-CONTEXT.md (4 decisions locked)
**Status:** Ready for execution

---

## Goal

Criar `EvidencePayload` dataclass + adaptar `EvidenceCollector.build_llm_payload()` para gerar payloads estruturados que alimentam o LLM Healer (L3).

---

## Tasks

### T-06.01: Criar EvidencePayload dataclass

**File:** `src/testforge/healing/evidence_payload.py` (novo)

**What:**
- Dataclass `EvidencePayload` com campos:
  - `step_context: dict` — action, selector, value, intention, url, framework, tag_name, family, taxonomy_id
  - `dom_snapshot: str` — HTML sanitizado, head+tail 3000 chars, strip scripts/styles
  - `console_errors: list[dict]` — últimos 5, cada um `{text, level, timestamp}`
  - `network_state: list[dict]` — últimas 3, cada um `{method, url, status, timing_ms}`
  - `screenshot_b64: str = ""` — opcional, base64 PNG
  - `is_sufficient: bool = False`
  - `insufficiency_reason: str = ""`
- Método `validate() -> None`: seta `is_sufficient` e `insufficiency_reason`
  - Suficiente se: `len(dom_snapshot) >= 100` AND (`len(console_errors) > 0` OR `len(network_state) > 0` OR `len(screenshot_b64) > 0`)
- Método estático `_sanitize_dom(html: str) -> str`: strip `<script>`, `<style>`, truncate head+tail 1500/1500 chars
- Método estático `_truncate_url(url: str) -> str`: max 120 chars
- Exportar no `__init__.py`

**Acceptance:**
- Dataclass instanciável com campos mínimos
- `validate()` seta `is_sufficient=True` com DOM 100+ chars + console errors
- `validate()` seta `is_sufficient=False` com DOM vazio
- `_sanitize_dom()` remove scripts e trunca corretamente
- `_truncate_url()` limita em 120 chars

**Depends on:** None

---

### T-06.02: Adaptar EvidenceCollector.build_llm_payload()

**File:** `src/testforge/evidence/evidence_collector.py` (atualizar)

**What:**
- Adicionar método `build_llm_payload(step_context: dict, include_screenshot: bool = False) -> EvidencePayload`
- Coletar DOM via `self._page.content()` → `EvidencePayload._sanitize_dom()`
- Coletar console errors dos últimos 5 registros (do buffer interno do coletor)
- Coletar network state das últimas 3 requisições (do buffer interno do coletor)
- Screenshot base64 se `include_screenshot=True` via `self._page.screenshot(type="png")`
- Chamar `payload.validate()` antes de retornar
- Adicionar buffer `_console_buffer: list` e `_network_buffer: list` ao `EvidenceCollector.__init__()`
- Registrar console errors via `page.on("console")` — chamado em `start()`
- Registrar network via `page.on("response")` — chamado em `start()`

**Acceptance:**
- `build_llm_payload(ctx)` retorna `EvidencePayload` com `is_sufficient=True`
- DOM sanitizado (sem scripts, ≤3000 chars)
- Console errors nos últimos 5 registros
- Network state nas últimas 3 requisições
- Screenshot base64 quando `include_screenshot=True`
- Sem crash quando page é None (modo sem browser)

**Depends on:** T-06.01

---

### T-06.03: Testes

**File:** `tests/test_evidence_payload.py` (novo ou expandir existente)

**What:**
- `test_payload_sufficient()` — DOM + console → is_sufficient=True
- `test_payload_insufficient_empty_dom()` — DOM vazio → is_sufficient=False
- `test_payload_insufficient_no_context()` — DOM sem console/network/screenshot → is_sufficient=False
- `test_sanitize_dom_strips_scripts()` — `<script>alert(1)</script>` removido
- `test_sanitize_dom_truncates()` — HTML 10000 chars → ≤3000 chars
- `test_truncate_url()` — URL longa → 120 chars
- `test_build_llm_payload_with_page()` — integração com page real (Playwright)

**Acceptance:**
- 99+ testes passando (não regredir)

**Depends on:** T-06.02

---

## Task Dependencies

```
T-06.01 (dataclass)
  └→ T-06.02 (EvidenceCollector)
       └→ T-06.03 (testes)
```

## Verification

- [ ] `EvidencePayload` importável de `testforge.healing`
- [ ] `build_llm_payload()` acessível no `EvidenceCollector`
- [ ] Dataclass serializável (campos simples, sem objetos complexos)
- [ ] DOM sanitizado não contém `<script>` nem `<style>`
- [ ] `is_sufficient` gate funcional
- [ ] 99+ testes passando
