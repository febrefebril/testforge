# Epicos & Historias — TestForge v1

**Versao:** 1.0
**Data:** 2026-06-13

---

## EP-00: Fundacao (v0.1.0 ✓)

**Objetivo:** Estrutura base do projeto

| Story | Descricao | Status |
|-------|-----------|--------|
| US-00.01 | Criar estrutura de diretorios e pyproject.toml | ✓ |
| US-00.02 | Criar README, CHANGELOG, VERSION | ✓ |
| US-00.03 | Criar ADRs (shadow mode, alert_only, source of truth) | ✓ |
| US-00.04 | Configurar git hooks (conventional commits) | ✓ |
| US-00.05 | Synthetic lab: fake-react-bank-app + mutation matrix | ✓ |

---

## EP-01: Recorder Sensorial (v0.1.0 ✓)

**Objetivo:** Capturar eventos do usuario no navegador

| Story | Descricao | Status |
|-------|-----------|--------|
| US-01.01 | RecordingSession: start/stop/finalize | ✓ |
| US-01.02 | RecorderController com JS injection | ✓ |
| US-01.03 | Captura de eventos: click, fill, navigation | ✓ |
| US-01.04 | Snapshot do alvo: DOM, screenshot, AX | ✓ |
| US-01.05 | Network log + sensitive data alert_only | ✓ |
| US-01.06 | Assert mode: 4 tipos (textual, estado, visivel, auto) | ✓ |
| US-01.07 | Comandos de teclado: Shift+P/S/A | ✓ |
| US-01.08 | Overlay UI com botoes e contador | ✓ |

---

## EP-02: Evidence (v0.1.0 ✓)

**Objetivo:** Coletar e armazenar evidencias de execucao

| Story | Descricao | Status |
|-------|-----------|--------|
| US-02.01 | EvidenceCollector: screenshots, DOM, manifest | ✓ |
| US-02.02 | EvidenceStore: list runs, query manifest, steps | ✓ |
| US-02.03 | Sensitive data alerts | ✓ |
| US-02.04 | pending_reviews query | ✓ |

---

## EP-03: Semantic Intermediate Model (v0.1.0 ✓)

**Objetivo:** Converter gravacao bruta em contrato semantico

| Story | Descricao | Status |
|-------|-----------|--------|
| US-03.01 | SemanticTestCase + SemanticAction model | ✓ |
| US-03.02 | RecordingNormalizer: raw events → SemanticTestCase | ✓ |
| US-03.03 | LocatorCandidateGenerator com scoring deterministico | ✓ |
| US-03.04 | PlaywrightCompiler com fallback loop | ✓ |
| US-03.05 | Compilacao de 4 tipos de assert | ✓ |

---

## EP-04: Oracle + Gate (v0.1.0 ✓)

**Objetivo:** Validar resultados e controlar promocao de healing

| Story | Descricao | Status |
|-------|-----------|--------|
| US-04.01 | OracleRunner: visual_dom | ✓ |
| US-04.02 | OracleRunner: business_state | ✓ |
| US-04.03 | run_all: executa multiplos oracles | ✓ |
| US-04.04 | PromotionGate: 3 estados + 5 bloqueios | ✓ |

---

## EP-05: Taxonomia + Healing (v0.1.0 ✓)

**Objetivo:** Classificar falhas e sugerir correcoes

| Story | Descricao | Status |
|-------|-----------|--------|
| US-05.01 | FailureClassifier: 11 codigos em 6 familias | ✓ |
| US-05.02 | ShadowValidator: sugestao em shadow mode | ✓ |
| US-05.03 | FallbackRunner: deterministico, timeout 2s | ✓ |

---

## EP-06: Metricas (v0.1.0 ✓)

**Objetivo:** Medir qualidade do healing

| Story | Descricao | Status |
|-------|-----------|--------|
| US-06.01 | MetricsRepository: precision, false_heal_rate | ✓ |
| US-06.02 | Review CLI: listar pendentes | ✓ |

---

## EP-07: CLI + Pipeline Integrada (v0.2.0) ✓

**Objetivo:** Ferramenta installavel e funcional

| Story | Descricao | Status |
|-------|-----------|--------|
| US-07.01 | `testforge` CLI entry point (console_scripts) | ✓ |
| US-07.02 | Comando `testforge record <url>` funcional | ✓ |
| US-07.03 | Comando `testforge compile <recording>` | ✓ |
| US-07.04 | Comando `testforge run <script>` com healing | ✓ |
| US-07.05 | Pipeline integrada: record → compile → run → heal | ✓ |
| US-07.06 | Demo healing real com fake-bank + mutation | ✓ |

---

## EP-08: Governanca + Documentacao

**Objetivo:** Manter qualidade e rastreabilidade

| Story | Descricao | Status |
|-------|-----------|--------|
| US-08.01 | GOVERNANCA.md com regras e gates | ✓ |
| US-08.02 | Diagramas PlantUML espelhados no codigo | ✓ (13 diagramas) |
| US-08.03 | TUTORIAL.md para teste manual | ✓ |
| US-08.04 | test_all.py para validacao automatica | ✓ |
| US-08.05 | Prompt pack para GSD (futuro) | Pendente |

---

## EP-09: LLM Self-Healing L3 (v0.3.0) ✅

**Objetivo:** Curador automatico com LLM off critical path (4-layer healing)
**Validado:** Azure GPT-4.1-mini real → `button:has-text('Pesquisar')` curou mutation change_id (conf 0.90)

| Story | Descricao | Status |
|-------|-----------|--------|
| US-09.01 | Expandir taxonomia (6→11 families, 88 codigos) | ✓ |
| US-09.02 | Keyword + group + word-boundary classifier | ✓ |
| US-09.03 | EvidencePayload estruturado (DOM, console, network) + EvidenceCollector.build_llm_payload() | ✓ |
| US-09.04 | LLMClient (Azure OpenAI / OpenAI) + imagens base64 + retry backoff | ✓ |
| US-09.05 | LLMHealer + MockLLMHealer (11 family prompts EN) | ✓ |
| US-09.06 | CuradorAutomatico (pipeline L0→L1→L3) + CurationOutcome | ✓ |
| US-09.07 | Integrar cmd_run com CuradorAutomatico | ✓ |
| US-09.08 | Testes: 25 evidence_payload + 11 taxonomy + Mock + Azure real | ✓ |
| US-09.09 | L2 Agents especialistas (Selector, Timing, Input...) | Pendente (opcional) |
| US-09.10 | Failure tracker + review threshold + _register_learned | ✓ |

**Principios:**
- LLM nunca no critical path ✅
- MockLLMHealer deterministico sem API key ✅
- Confidence gate ≥ 0.5 ✅
- Max retry depth = 1 ✅
- Auto-learn: curas bem-sucedidas viram receitas no HealingCatalog ✅

---

## EP-10: Data-Driven Testing + Docs (v0.3.0) ✅

**Objetivo:** Massa de dados externa em JSON, prompt pack, tutorial

| Story | Descricao | Status |
|-------|-----------|--------|
| US-10.01 | DataExtractor: extrai valores fill da gravação → test_data.json | ✓ |
| US-10.02 | Compiler data-driven: script lê _data.get() em vez de hardcoded | ✓ |
| US-10.03 | Suporte --scenarios para múltiplos cenários no mesmo JSON | ✓ |
| US-10.04 | Detecção de campos sensíveis (CPF, senha) — alert_only | ✓ |
| US-10.05 | Prompt Pack GSD v0.3.0 (7 prompts: base, record, compile, run, review, verify, new feature) | ✓ |
| US-10.06 | TUTORIAL-LLM-HEALING.md (8 seções: visão geral, debug, métricas, troubleshooting) | ✓ |
| US-10.07 | Sanitização de nomes de teste (regex, collapse underscore) | ✓ |
| US-10.08 | 15 diagramas PlantUML atualizados (componentes, sequência, C4, data-driven) | ✓ |

**Principios:**
- Dados de teste versionáveis separados do código
- Script não precisa ser recompilado para mudar massa
- Sensitive data: alert_only no MVP
