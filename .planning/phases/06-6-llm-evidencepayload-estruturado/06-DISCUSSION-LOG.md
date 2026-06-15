# Phase 6: LLM EvidencePayload — Discussion Log

**Date:** 2026-06-15
**Facilitator:** BMAD brainstorming (compressed)
**Mode:** Structured analysis with reference implementation

---

## Session Overview

**Topic:** 4 technical decisions for EvidencePayload implementation
**Goals:** Lock down DOM sanitization, minimum evidence criteria, console/network fields, and integration approach

**Reference:** `projeto-anterior` codebase (validated implementation)

---

## Decisions

### Area 1: DOM Sanitization
- **Presented:** 3 options (head+tail, head-only, full body)
- **Selected:** Head+tail 1500/1500 chars, strip `<script>` and `<style>`, no PII in `data-*`
- **Rationale:** Same as validated reference implementation. Preserves page structure context.
- **Reference:** `llm/healer.py:_truncate_dom()`

### Area 2: Minimum Evidence (is_sufficient)
- **Presented:** 3 options (DOM+1 source, DOM-only, all-or-nothing)
- **Selected:** DOM snapshot (≥100 chars) + at least 1 of {console errors, network state, screenshot}
- **Rationale:** DOM is essential for LLM analysis. At least 1 additional context source required.
- **Reference:** `curator.py:cure()` evidence gate

### Area 3: Console + Network Fields
- **Presented:** 3 options (varying field richness)
- **Selected:** Console: `{text, level, timestamp}` last 5. Network: `{method, url, status, timing_ms}` last 3.
- **Rationale:** `level` filters warnings vs errors. `timestamp` gives event order. `timing_ms` helps diagnose slowness.
- **Reference:** `llm/healer.py:_build_prompt()`

### Area 4: Integration with EvidenceCollector
- **Presented:** 3 options (method on collector, separate builder, factory on dataclass)
- **Selected:** New method `build_llm_payload(step_context)` on existing `EvidenceCollector`
- **Rationale:** Collector already has page, screenshots, DOM, network. No extra indirection needed.
- **Reference:** Phase plan diagram `sequencia-integracao-cmd-run.puml`

---

## Outcome

All 4 decisions locked. User selected recommended options (A in all cases).
CONTEXT.md created with decisions, canonical refs, code context, and integration points.

**Next:** `/gsd-plan-phase 6` or direct implementation.
