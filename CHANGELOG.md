# Changelog

## [0.4.2] — 2026-06-30

### Added
- **Diagnostic Mode (Sprint 0):** Standalone data-collection mode for QA telemetry
  - `FrameworkDetector` — CDP bundle analysis + window/DOM/custom-elements (A3+A4)
  - `CaptureQualityTracker` — value_kind regex, framework_signal, blind_spots
  - `ReplayCheck` — immediate (B1) or batched (B4) Locator probe
  - `GherkinWriter` — live `scenario.feature` (pt-BR), C4b auto-derive + C4c confirm
  - `DiagnosticTelemetryStore` — JSONL primary + OTel spans (E4)
  - `DiagnosticSession` — orchestrator integrating all components
  - `RecorderController` hook + CLI (`testforge record --diagnostic-mode`)
  - Publisher: Azure DevOps (G4 + Z1+Z5)
  - 2 new PlantUML diagrams: `fluxograma-diagnostic-mode.puml`, `sequencia-diagnostic-gherkin.puml`
- **Architecture v2 (Phases 1-7):** Feature-flagged additive migration
  - Phase 1: Playwright tracing + CDP AX-tree capture (parallel)
  - Phase 2: v2 LocatorExtractor + Playwright codegen + intent normalization
  - Phase 3: LocatorResolver + step API + v2 compiler
  - Phase 4: SQLite intent-keyed catalog + persistent L0
  - Phase 5: Pipes & Filters infra + 4 extracted stages
  - Phase 6: zero-dep tracer + static dashboard.html (OTel-compatible spans)
  - Phase 7: YAML-driven ComponentResolver + component_patterns.yaml
- **Recorder — Sprint A:** fill capture for Material currencymask + datepicker
- **Recorder — Sprint J:** Material form-field anchor resolution
- **Recorder — Sprint M:** runtime resolver Material anchor
- **Recorder — Sprint O/P/Q/R/S:** ACCNAME v1.2, mask raw value capture, rrweb-lite DOM mutation timeline, finder CSS optimization, visibility fix
- **Recorder — Sprint A2/A3/B2/B3/D/F:** 6 root-cause fixes for SIOPI 15a-f
- **Compiler — Sprint B:** drop ambiguous selectors + soft pos-condition
- **Runner — Sprint 1:** screen-state tracker MVP (decommission plan for legacy `run`)
- **Runner — Sprint 2:** screen-state drift escalation to L3 healer
- **Metrics:** `assert_hit_rate` — real pilot success metric + inline UI in run-incremental summary
- **UX:** QA wizard (`--wizard`) for guided recording setup
- **UX:** React `_valueTracker` reset detection
- **CLI:** `--headed` flag for run-incremental, `--verify-ssl` flag, `--save-output` flag
- **CLI:** deprecation WARN em `testforge run` legacy command
- **Recorder:** capture fingerprint v1 + recording timeline audit
- **Normalizer:** H22b — per-call dedupe telemetry on RecordingNormalizer
- **Recording:** shadow DOM (B14/B17) + H20 scenario + H21 inline field value prompts
- **Healing:** L0.5 accessibility tree resolution with regex `get_by_role` fallback
- **Healing:** compound attribute selectors (placeholder+aria-label, placeholder+name, aria-label+name)
- **Healing:** multi-attribute fingerprint in SemanticTarget
- **Healing:** runtime multi-attribute self-healing (Phase 4d)
- **Healing:** catalog auto-aprendido — HealCatalog records successful heal resolutions for <1ms reuse
- **Compiler:** B29 — emit one pytest function per scenario_segment
- **CLI:** `--validate-before-ready`, `--pilot-mode` enhancements
- **Test:** smoke test (hotfix 13) — end-to-end pipeline smoke on controlled fixture
- **Test:** intent lab LAB-11 to LAB-16 (mat-select, autocomplete, dialog, tabs, PrimeFaces, React MUI)

### Fixed
- **Recorder (Sprint 1):** 9 bugs/capacities — immediate stabilization
- **Recorder — Sprint P:** exclude volatile Angular state classes from finder
- **Recorder:** promote XHR/fetch POST after click to pseudo-submit (hotfix 7)
- **Recorder:** browser close = graceful stop (hotfix 10)
- **Recorder:** Shift+S closes browser + clear UX (hotfix 14)
- **Recorder:** UnicodeEncodeError guard during assert selection
- **Recorder:** 300ms polling flood fix — batch all JS queue reads into one CDP call
- **Recorder:** persist overlay position across page navigations via localStorage
- **Recorder:** prevent browser close on error during assert
- **Normalizer:** hotfix 22 — IntentReconstructor recovers masked-input values again
- **Normalizer:** H22a — promote `final_state` above `setter_hook` + unify priority table
- **Normalizer:** CS-4a — fix `--complete` writer/reader contract mismatch
- **Normalizer:** B30 rebind synthetic step_N keys + B26/B31 dedup
- **Normalizer+Completeness:** H9 HTTPS default, H16 verdict semantics, P3 invariants
- **Runner:** hotfix 6 — wait for CDK overlay before clicking inside it
- **Runner:** hotfix 9 — restore StepExecutor select_option + fill methods
- **Runner:** hotfix 16 — clear field and use raw digits in fallback fill paths
- **Runner:** hotfix 17 — detect currency mask by placeholder, not just attribute
- **Runner:** hotfix 19+20 — dataclass unwrap and click-only datepicker
- **Runner:** hotfix 15 — CWD-independent paths + finalize after close
- **Runner:** incremental_runner — extract recording_id correctly in multi-scenario scripts
- **Healing:** B23 L0 proposal + B24/B25 text guard + B27/B28 LLM keys
- **Healing:** B33 — L0 js-only recipes carry the step's original locator
- **Healing:** H17 finish + B18/B19/B20/B21 false-heal cascade
- **Healing+Runner:** fix false-heal cascade in FAM-02/05/06
- **Diagnostic:** hotfix 1 — heuristic candidates + detection cache
- **Diagnostic:** hotfix 3 — Material icon scrub + skip empty-label steps
- **CLI:** hotfix 8 — run-incremental accepts directory path
- **CLI:** hotfix 11 — `--complete` prompt shows enriched per-field context
- **CLI:** B32 — loud suffix-bump warning + compile sibling fallback
- **CLI:** correct indentation in cmd_record URL validation
- **CLI:** editor fallback chain (hotfix 2)
- **Publisher:** hotfix 5 — `git add -f` + `--system` default to `--app`
- **Publisher:** warn when `--system`/`--suite` missing, fix None crash, apply send overrides
- **Publisher:** probe cwd/.testforge/config.yml before git root, warn when unconfigured
- **Browser:** `--window-size` only in headless mode, avoid headed resize flicker
- **Browser:** no_viewport=True in headed mode for all `new_context` calls
- **Bug1:** wrap `_persist_step` in try/except, guard `page.title()` and `page.url`
- **Bug2+6:** use no_viewport=True in headed mode
- **Bug3:** restore step counter increment after click and submit events
- **Bug4:** move `_auto_publish_recording` after validation in cmd_record
- **Bug5:** add encoding=utf-8 to all write-mode `open()` calls
- **Bug8:** expose `_OVERLAY_JS` as class attribute on RecorderController
- **Bug9:** fill dedup — DOM-indexed fallback key and skip same-field focus clicks
- **Bug11-16:** SELECT recording and playback fixes
- **GUI:** window title 'testforge', combo readonly colors mapped
- **Performance:** translate step output to Portuguese, remove blocking DOM capture in light mode
- **Tests:** fix 9 failures in categories B/C/D (overlay JS, commands, gate)
- **Tests:** align expectations with PT-BR linter pass
- **Tests:** align metrics + recording_readiness with PT-BR + H16
- **Linter:** fix linter-induced indent breaks + readiness test for H16
- **Metrics:** field_snapshots emission + asserts denominator fix

### Changed
- **Refactor:** extract overlay JS from Python string to `overlay_inject.js`
- **Refactor:** merge IntentReconstructor into RecordingNormalizer, delete `intent_reconstructor.py`
- **Refactor:** simplify recording_normalizer.py `_build_target`, remove obsolete helpers
- **Refactor:** add `page.on('framenavigated')` for Python-side nav tracking
- **Refactor:** Pipes & Filters infra — 4 extracted stages (Phase 5)
- **Refactor:** consolidate fill helpers, add path telemetry (CS-1 + CS-3)
- **Chore:** remove all emojis from source code (replace with ASCII markers)
- **Chore:** post-sweep cleanup — gitignore .claude, fix browser.py indent
- **Chore:** remove `runs/` and `recordings/uncategorized/` from remote
- **Perf:** batched replay-check + action-only probes + reused resolver (H17)
- **Perf:** batch all JS queue reads into one CDP call per cycle

### Docs
- **Architecture v2 reference:** `docs/ARCHITECTURE-V2.md` + 3 new diagrams
- **Sprint 0 diagnostic mode:** flowchart + sequence diagrams
- **Changelog:** add v0.4.2 — Sprint 0 hotfixes, diagnostic mode, Phases 1-7
- **Diagrams:** 9 PUML files sync'd to v0.4.2
- **CLAUDE.md:** sync'd to v0.4.2 state
- **README.md:** add Sprint 0 features, update metrics
- **STATE.md:** update to v0.4.2 with M13

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
