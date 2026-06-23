# Changelog

## [0.4.1] — 2026-06-23

### Added
- **ComponentHandler system** (`src/testforge/handlers/`):
  - `ComponentHandler` — abstract base class (detect, normalize, execute, heal)
  - `CDKOverlayHandler` — shared CDK overlay utilities
  - `AngularMaterialHandler` — mat-select, mat-autocomplete, mat-dialog, mat-tab-group, mat-slide-toggle
  - `PrimeFacesHandler` — skeleton (detect only)
  - `ReactMUIHandler` — skeleton (detect only)
  - `detect_handler()` — registry-based dispatch for component-specific handling
- **Sprint 1:** Handler foundation + mat-select (LAB-11)
- **Sprint 2:** mat-autocomplete + keypress→fill collapse (LAB-12)
- **Sprint 3:** mat-dialog + mat-tab-group + mat-slide-toggle (LAB-13, LAB-14)
- **Sprint 4:** Normalizer migration — `_dedup_datepicker_sequences` replaced by `AngularMaterialHandler.normalize()`
- **Sprint 5:** PrimeFaces handler skeleton (LAB-15)
- **Sprint 6:** React MUI handler skeleton (LAB-16)
- **Normalizer:** shadow DOM (GT-01), iframe (GT-02), contenteditable (GT-08), Select2 combobox (GT-07) blind spot detection
- **Normalizer:** keypress→fill compression for autocomplete inputs
- **LAB pages:** 7 new — Select2, Angular Material, React MUI, Vue Vuetify, mat-autocomplete, mat-dialog, mat-tabs, PrimeFaces select
- **Publisher:** auto-publish to Azure DevOps Git, local-mode, CLI `--system`/`--suite`, updater, PT-BR healing
- **Publisher:** zero-config via `.testforge/config.yml` + GCM

### Fixed
- **Normalizer (4 bugs):** contenteditable false positive, Angular datepicker dedup, healing_rejected on Calcular button, element_id usage
- **Executor:** accessible_name as fill label, dispatch blur after fill for Angular/React validation
- **Dedup:** CAIXA datepicker pattern detection, Portuguese error classification
- **Runner:** DD/MM/AAAA date mask detection, Tab after fill, UnboundLocalError in oracle branch
- **Assert:** Angular auto-generated ID degradation, element capture + semantic identity + hover highlight
- **Recorder:** assert menu visibility, simplified assert flow (no confirm dialog, Esc+timeout)
- **Viewport:** Windows flick fix — `new_context(viewport=)` instead of `set_viewport_size()`

### Changed
- Normalizer: keypress sequences compacted into single fill before dedup
- Normalizer: datepicker dedup migrated from inline method to handler.normalize()
- StepExecutor: handler detection injected before action routing
- StepPostcondition: improved assert oracle logic

### Tests
- LAB-11 to LAB-16 test suites (mat-select, mat-autocomplete, mat-dialog, mat-tabs, PrimeFaces, React MUI)
- test_intent_lab_pages: 21 pages total (7 new)
- Assert oracle regression tests
- Recorder stability tests

## [0.4.0] — 2026-06-20

### Added
- Consolidação completa da documentação — 7 fases
- Intent Lab: 14+ páginas de teste de intenção
- Readiness gate: 5 critérios objetivos (completude, steps, blocking, user-supplied, healing)
- Pilot metrics: MetricsRepository + PilotMetrics
- URL validator
- Validação incremental de intenção (Sprint 5)
- CLI `--validate-before-ready`
- CLI `--pilot-mode`
- 14 diagramas PlantUML sincronizados com código v0.4.0
- Guia de versionamento e sincronização de diagramas

### Changed
- Documentação reorganizada: USER-GUIDE, TUTORIAIS, REFERENCIA, ARQUITETURA, DIAGRAMAS
- ADR-006: Phase B evidence consumption
- Comentários e outputs traduzidos para português

### Fixed
- Overlay assert flow + browser close hang + step counter spam
- Windows viewport resize compat
- Step.value has priority over field_value_map
- Normalizer filters SVG inner_html + clicks without candidates
- Masked input detection by placeholder pattern

## [0.1.0] — 2026-06-13

### Added
- Estrutura inicial do repositorio
- Synthetic lab: fake-react-bank-app com fluxo CPF
- Mutation matrix com 5 mutacoes
- ADRs: shadow mode, alert_only, semantic source of truth
- Testes Playwright para fluxo base e mutacoes
