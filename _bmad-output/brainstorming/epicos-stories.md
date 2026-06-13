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

## EP-07: CLI + Pipeline Integrada (v0.2.0)

**Objetivo:** Ferramenta installavel e funcional

| Story | Descricao | Status |
|-------|-----------|--------|
| US-07.01 | `testforge` CLI entry point (console_scripts) | Pendente |
| US-07.02 | Comando `testforge record <url>` funcional | Pendente |
| US-07.03 | Comando `testforge compile <recording>` | Pendente |
| US-07.04 | Comando `testforge run <script>` com healing | Pendente |
| US-07.05 | Pipeline integrada: record → compile → run → heal | Pendente |
| US-07.06 | Demo healing real com fake-bank + mutation | Pendente |

---

## EP-08: Governanca + Documentacao

**Objetivo:** Manter qualidade e rastreabilidade

| Story | Descricao | Status |
|-------|-----------|--------|
| US-08.01 | GOVERNANCA.md com regras e gates | ✓ |
| US-08.02 | Diagramas PlantUML espelhados no codigo | ✓ |
| US-08.03 | TUTORIAL.md para teste manual | ✓ |
| US-08.04 | test_all.py para validacao automatica | ✓ |
| US-08.05 | Prompt pack para GSD (futuro) | Pendente |
