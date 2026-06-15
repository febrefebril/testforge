# Sprint Planning — TestForge v0.2.0 → v0.3.0

**Data:** 2026-06-15
**Status:** Sprint 8 concluida ✅ | Sprint 9 em andamento 🔧

---

## Sprint 8: CLI + Pipeline Integrada ✅

### US-07.01: CLI Entry Point ✅

| Tarefa | Status |
|--------|--------|
| T-07.01.01 — Atualizar `pyproject.toml` com `[project.scripts]` | ✅ |
| T-07.01.02 — `testforge = "testforge.cli.app:main"` | ✅ |
| T-07.01.03 — `pip install -e .` → comando `testforge` disponivel | ✅ |
| T-07.01.04 — `testforge --help` mostra comandos | ✅ |

### US-07.02: Comando Record ✅
### US-07.03: Comando Compile ✅
### US-07.04: Comando Run ✅
### US-07.05: Pipeline Completa ✅
### US-07.06: Demo Healing Real ✅

**Criterios de Aceite da Sprint 8:**
- [x] `testforge record http://localhost:8765` grava fluxo
- [x] `testforge compile REC-001` gera script valido
- [x] `testforge run semantic_tests/test_*.py` executa com healing
- [x] Demo: gravar → quebrar seletor → healing corrige
- [x] 99/99 testes passando

---

## Sprint 9: LLM Self-Healing L3 🔧

**Objetivo:** Curador automatico com LLM off critical path

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

### US-09.02: EvidencePayload Estruturado ⏳

| Tarefa | Status |
|--------|--------|
| T-09.02.01 — `EvidencePayload` dataclass (step_context, dom, console, network) | Pendente |
| T-09.02.02 — Sanitizacao: DOM trunc 3000 chars | Pendente |
| T-09.02.03 — Adaptar `EvidenceCollector.build_llm_payload()` | Pendente |
| T-09.02.04 — `is_sufficient` + `insufficiency_reason` | Pendente |

### US-09.03: LLM Client ⏳

| Tarefa | Status |
|--------|--------|
| T-09.03.01 — `LLMClient.chat()` — Azure OpenAI / OpenAI | Pendente |
| T-09.03.02 — Auto-detectar provider via env vars | Pendente |
| T-09.03.03 — Suporte a imagens base64 (screenshots) | Pendente |
| T-09.03.04 — Retry com exponential backoff (429) | Pendente |
| T-09.03.05 — `extract_code_block()` e `_parse_response()` | Pendente |

### US-09.04: LLMHealer + MockLLMHealer ⏳

| Tarefa | Status |
|--------|--------|
| T-09.04.01 — `LLMHealingProposal` dataclass | Pendente |
| T-09.04.02 — 11 prompts familia-especificos (FAM01 a FAM11) | Pendente |
| T-09.04.03 — `CURATION_PROMPT_TEMPLATE` generico | Pendente |
| T-09.04.04 — `LLMHealer.heal()` — chama LLM → parse JSON → valida | Pendente |
| T-09.04.05 — `MockLLMHealer` — deterministico, confidence 0.85 | Pendente |
| T-09.04.06 — Ativacao automatica: Azure key → real, sem key → mock | Pendente |

### US-09.05: CuradorAutomatico ⏳

| Tarefa | Status |
|--------|--------|
| T-09.05.01 — `CurationOutcome` + `ProgressResult` dataclasses | Pendente |
| T-09.05.02 — `CuradorAutomatico.cure()` — orquestrador L0→L3 | Pendente |
| T-09.05.03 — `_try_layer1_catalog()` — HealingCatalog.match() | Pendente |
| T-09.05.04 — `_try_layer2_agents()` — placeholder para agentes | Pendente |
| T-09.05.05 — `_run_healing_cycle()` — LLMHealer → validar → executar | Pendente |
| T-09.05.06 — `_register_learned()` / `_register_unresolved()` | Pendente |
| T-09.05.07 — Failure count + review threshold (5) + notificacao | Pendente |
| T-09.05.08 — Stale detection (90 dias) | Pendente |
| T-09.05.09 — Rollback automatico (REGRESSED/STAGNATED) | Pendente |

### US-09.06: Integrar cmd_run ⏳

| Tarefa | Status |
|--------|--------|
| T-09.06.01 — Coletar EvidencePayload durante execucao | Pendente |
| T-09.06.02 — Chamar `CuradorAutomatico.cure()` na falha | Pendente |
| T-09.06.03 — Registrar metricas (layer_used, llm_used) | Pendente |
| T-09.06.04 — Report final com layer+confidence | Pendente |

### US-09.07: Testes L3 ⏳

| Tarefa | Status |
|--------|--------|
| T-09.07.01 — `test_llm_healer.py` — MockLLMHealer, parse, prompts | Pendente |
| T-09.07.02 — `test_curator.py` — fluxo L0→L3, retry, threshold | Pendente |
| T-09.07.03 — `test_evidence_payload.py` — trunc, sanitizacao | Pendente |
| T-09.07.04 — `test_healing_l3_e2e.py` — fake-bank + change_id mutation | Pendente |

---

## Criterios de Aceite da Sprint 9

- [ ] `EvidencePayload` gerado com DOM truncado, console, network
- [ ] `MockLLMHealer` cura `change_id` sem API key
- [ ] `CuradorAutomatico.cure()` pipeline L0→L1→L3 funcional
- [ ] Curas bem-sucedidas registradas no HealingCatalog
- [ ] 5 falhas consecutivas → notificacao
- [ ] `testforge run` integrado com curador
- [ ] 100% testes passando

---

## Sprint 10: Prompt Pack + Docs Finais

| Tarefa | Status |
|--------|--------|
| T-10.01 — Criar `.planning/prompt-pack-v0.2.0.md` | Pendente |
| T-10.02 — Prompts para cada fase (record, compile, run, heal) | Pendente |
| T-10.03 — Prompt de code review | Pendente |
| T-10.04 — Prompt de verificacao | Pendente |
| T-10.05 — TUTORIAL.md para LLM healing | Pendente |
