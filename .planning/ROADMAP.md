# Roadmap — TestForge v1

## Milestone 1: Fundacao + Synthetic Lab (Sprint 1) ✅

**Objetivo:** Estrutura do repositorio + fake app + mutation matrix

| Fase | Tarefas | Status |
|------|---------|--------|
| 1.1 | Estrutura repo, README, VERSION, CHANGELOG, ADRs | ✅ |
| 1.2 | fake-react-bank-app com fluxo CPF | ✅ |
| 1.3 | mutation_matrix.yaml (5 mutacoes) | ✅ |
| 1.4 | Implementar mutacoes + testes Playwright | ✅ |

## Milestone 2: Recorder Sensorial (Sprint 2) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 2.1 | RecordingSession + RecorderController | ✅ |
| 2.2 | Captura de eventos (pointerup, input, keydown) | ✅ |
| 2.3 | Snapshot do alvo + contexto (DOM, AX, screenshot) | ✅ |
| 2.4 | Network log + sensitive data alert | ✅ |
| 2.5 | Teste E2E da gravacao | ✅ |

## Milestone 3: Evidence (Sprint 3) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 3.1 | EvidenceCollector: screenshots, DOM, manifest | ✅ |
| 3.2 | EvidenceStore: list runs, query manifest | ✅ |
| 3.3 | Sensitive data alerts (alert_only) | ✅ |
| 3.4 | pending_reviews query | ✅ |

## Milestone 4: MIS + Compiler (Sprint 4) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 4.1 | SemanticTestCase + SemanticAction model | ✅ |
| 4.2 | RecordingNormalizer: raw → SemanticTestCase | ✅ |
| 4.3 | LocatorCandidateGenerator com scoring | ✅ |
| 4.4 | PlaywrightCompiler com fallback loop | ✅ |
| 4.5 | Compilacao de 4 tipos de assert | ✅ |

## Milestone 5: Oracle + Gate (Sprint 5) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 5.1 | OracleRunner: visual_dom | ✅ |
| 5.2 | OracleRunner: business_state | ✅ |
| 5.3 | run_all: multiplos oracles | ✅ |
| 5.4 | PromotionGate: 3 estados + 5 bloqueios | ✅ |

## Milestone 6: Taxonomia + Shadow (Sprint 6) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 6.1 | FailureClassifier: keyword + group + word-boundary | ✅ |
| 6.2 | 11 familias, 88 codigos taxonomicos | ✅ |
| 6.3 | ShadowValidator + FallbackRunner deterministico | ✅ |

## Milestone 7: Metricas (Sprint 7) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 7.1 | MetricsRepository: precision, false_heal_rate | ✅ |
| 7.2 | Review CLI: listar pendentes | ✅ |

## Milestone 8: CLI + Pipeline (Sprint 8) ✅

| Fase | Tarefas | Status |
|------|---------|--------|
| 8.1 | `testforge` CLI entry point (console_scripts) | ✅ |
| 8.2 | Comando `testforge record <url>` | ✅ |
| 8.3 | Comando `testforge compile <recording>` | ✅ |
| 8.4 | Comando `testforge run <script>` com healing | ✅ |
| 8.5 | Pipeline integrada: record → compile → run → heal | ✅ |
| 8.6 | Demo healing real com fake-bank + mutation | ✅ |

## Milestone 9: LLM Self-Healing L3 (Sprint 9) 🔧

**Objetivo:** Curador automatico com LLM off critical path

| Fase | Tarefas | Status |
|------|---------|--------|
| 9.1 | Expandir taxonomia (6→11 familias, 80+ codigos) | ✅ |
| 9.2 | EvidencePayload estruturado para LLM | ⏳ |
| 9.3 | LLMClient (Azure OpenAI / OpenAI) | ⏳ |
| 9.4 | LLMHealer + MockLLMHealer + 11 prompts | ⏳ |
| 9.5 | CuradorAutomatico (pipeline L0→L3) | ⏳ |
| 9.6 | Integrar cmd_run com CuradorAutomatico | ⏳ |
| 9.7 | Testes L3 + integracao fake-bank | ⏳ |
| 9.8 | L2 Agents especialistas (opcional) | ⏳ |

## Milestone 10: Prompt Pack + Docs (Sprint 10)

| Fase | Tarefas | Status |
|------|---------|--------|
| 10.1 | Prompt pack GSD v0.2.0 | ⏳ |
| 10.2 | Diagramas PlantUML arquitetura completa | ✅ (13) |
| 10.3 | GOVERNANCA.md atualizada | ✅ |
| 10.4 | TUTORIAL.md para LLM healing | ⏳ |

## Fora do MVP

- LLM Curator integrado (L3c)
- Dashboard web
- Multiplos frameworks alem de React/PrimeFaces
- Mascaramento automatico de dados sensiveis

### Phase 6: 6 LLM EvidencePayload estruturado

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 6 to break down)

### Phase 7: 7 LLM Healer + MockLLMHealer + prompts

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 6
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 7 to break down)
