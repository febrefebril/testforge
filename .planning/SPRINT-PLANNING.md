# Sprint Planning — TestForge v0.2.0 → v0.3.0

**Data:** 2026-06-15
**Status:** Sprint 8 ✅ | Sprint 9 ✅ | Sprint 10 ⏳

---

## Sprint 8: CLI + Pipeline Integrada ✅

### US-07.01: CLI Entry Point ✅
### US-07.02: Comando Record ✅
### US-07.03: Comando Compile ✅
### US-07.04: Comando Run ✅
### US-07.05: Pipeline Completa ✅
### US-07.06: Demo Healing Real ✅

**Criterios de Aceite:**
- [x] `testforge record http://localhost:8765` grava fluxo
- [x] `testforge compile REC-001` gera script valido
- [x] `testforge run semantic_tests/test_*.py` executa com healing
- [x] Demo: gravar → quebrar seletor → healing corrige

---

## Sprint 9: LLM Self-Healing L3 ✅

**Objetivo:** Curador automatico com LLM off critical path
**Validado:** Azure GPT-4.1-mini real curou seletor quebrado no fake-bank

### US-09.01: Expandir Taxonomia ✅

| Tarefa | Status |
|--------|--------|
| T-09.01.01 — 11 familias (FAM-01 a FAM-11) | ✅ |
| T-09.01.02 — 88 codigos taxonomicos (SEL-001, TIM-005...) | ✅ |
| T-09.01.03 — Keyword matching com word-boundary | ✅ |
| T-09.01.04 — Group fallback via regex | ✅ |
| T-09.01.05 — KNOWN_FAILURES: mapeamento completo com recoverable | ✅ |
| T-09.01.06 — Atualizar FallbackRunner (FailureFamily.ACTIONABILITY → STATE/DOM/INPUT) | ✅ |
| T-09.01.07 — 11 novos testes de classificacao | ✅ |

### US-09.02: EvidencePayload Estruturado ✅

| Tarefa | Status |
|--------|--------|
| T-09.02.01 — `EvidencePayload` dataclass (step_context, dom, console, network) | ✅ |
| T-09.02.02 — Sanitizacao: DOM trunc 3000 chars, strip scripts/styles | ✅ |
| T-09.02.03 — Adaptar `EvidenceCollector.build_llm_payload()` | ✅ |
| T-09.02.04 — `is_sufficient` (DOM ≥100 chars) | ✅ |

### US-09.03: LLM Client ✅

| Tarefa | Status |
|--------|--------|
| T-09.03.01 — `LLMClient.chat()` — Azure OpenAI / OpenAI | ✅ |
| T-09.03.02 — Auto-detectar provider via env vars | ✅ |
| T-09.03.03 — Suporte a imagens base64 (screenshots) | ✅ |
| T-09.03.04 — Retry com exponential backoff (429) | ✅ |
| T-09.03.05 — `extract_code_block()` | ✅ |

### US-09.04: LLMHealer + MockLLMHealer ✅

| Tarefa | Status |
|--------|--------|
| T-09.04.01 — `LLMHealingProposal` dataclass | ✅ |
| T-09.04.02 — 11 prompts familia-especificos (FAM01 a FAM11 — EN) | ✅ |
| T-09.04.03 — `CURATION_PROMPT_TEMPLATE` generico | ✅ |
| T-09.04.04 — `LLMHealer.heal()` — chama LLM → parse JSON → valida | ✅ |
| T-09.04.05 — `MockLLMHealer` — deterministico, CSS selectors, confidence 0.85 | ✅ |
| T-09.04.06 — Ativacao automatica: Azure key → real, sem key → mock | ✅ |

### US-09.05: CuradorAutomatico ✅

| Tarefa | Status |
|--------|--------|
| T-09.05.01 — `CurationOutcome` + `ProgressResult` dataclasses | ✅ |
| T-09.05.02 — `CuradorAutomatico.cure()` — orquestrador L0→L3 | ✅ |
| T-09.05.03 — `_try_layer0_catalog()` — HealingCatalog.match() | ✅ |
| T-09.05.04 — `_try_layer1_fallback()` — placeholder para agentes | ✅ |
| T-09.05.05 — `_run_healing_cycle()` — LLMHealer → validar → executar | ✅ |
| T-09.05.06 — `_register_learned()` / `_register_unresolved()` | ✅ |
| T-09.05.07 — Failure count + review threshold (5) + notificacao | ✅ |
| T-09.05.08 — Stale detection (90 dias) | ✅ |
| T-09.05.09 — Rollback automatico (REGRESSED/STAGNATED) | ✅ |

### US-09.06: Integrar cmd_run ✅

| Tarefa | Status |
|--------|--------|
| T-09.06.01 — Coletar EvidencePayload durante execucao | ✅ |
| T-09.06.02 — Chamar `CuradorAutomatico.cure()` na falha | ✅ |
| T-09.06.03 — Registrar metricas (layer_used, llm_used) | ✅ |
| T-09.06.04 — Report final com layer+confidence | ✅ |

### US-09.07: Testes ✅

| Tarefa | Status |
|--------|--------|
| T-09.07.01 — `test_evidence_payload.py` — 25 testes: validacao, sanitizacao, integracao | ✅ |
| T-09.07.02 — `test_taxonomy_runner.py` — 11 testes de classificacao expandidos | ✅ |
| T-09.07.03 — Teste real: MockLLMHealer cura change_id | ✅ |
| T-09.07.04 — Teste real: Azure GPT-4.1-mini cura change_id (conf 0.90) | ✅ |

**Criterios de Aceite da Sprint 9:**
- [x] `EvidencePayload` gerado com DOM truncado, console, network
- [x] `MockLLMHealer` cura `change_id` sem API key
- [x] `CuradorAutomatico.cure()` pipeline L0→L1→L3 funcional
- [x] Curas bem-sucedidas registradas no HealingCatalog (`_register_learned`)
- [x] Failure tracker + review threshold (5 falhas → notificacao)
- [x] `testforge run` integrado com curador
- [x] 124/124 testes passando
- [x] LLM real validado: Azure GPT-4.1-mini → `button:has-text('Pesquisar')` (conf 0.90) → PASSED_STEP

---

## Sprint 10: Prompt Pack + Docs Finais ✅

| Tarefa | Status |
|--------|--------|
| T-10.01 — Criar `.planning/prompt-pack-v0.3.0.md` | ✅ |
| T-10.02 — Prompts para cada fase (record, compile, run, heal) | ✅ |
| T-10.03 — Prompt de code review + verificacao | ✅ |
| T-10.04 — TUTORIAL.md para LLM healing | ✅ |
| T-10.05 — Data-driven testing (massa de dados externa) | ✅ |

---

## Backlog (futuro)

| # | O quê | Prioridade |
|---|-------|-----------|
| P2 | cmd_run: re-execução do step curado inline (hoje pytest subprocess limita) | Média |
| P3 | L2 Specialist Agents (Selector, Timing, Input, Context, State, DynamicDOM) | Baixa |
| P4 | Flag `--llm` / `--no-llm` no CLI | Baixa |
| P5 | Pipeline CI (GitHub Actions / Azure DevOps) | Baixa |
| P6 | Dashboard web de métricas | Fora do MVP |
