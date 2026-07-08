# Changelog

## [0.1.0] - Unreleased

### Added

- **Estrutura inicial do repositorio** — Synthetic lab: fake-react-bank-app com fluxo CPF, mutation matrix com 5 mutacoes, ADRs (shadow mode, alert_only, semantic source of truth), testes Playwright para fluxo base e mutacoes
- **Consolidacao completa da documentacao** — 7 fases, estrutura em 6 categorias (USER-GUIDE, TUTORIAIS, ARQUITETURA, REFERENCIA, DIAGRAMAS, PESQUISA)
- **Intent Lab** — 14+ paginas de teste de intencao
- **Readiness gate** — 5 criterios objetivos (completude, steps, blocking, user-supplied, healing)
- **Pilot metrics** — MetricsRepository + PilotMetrics
- **URL validator**
- **Validacao incremental de intencao** (Sprint 5)
- CLI `--validate-before-ready`
- CLI `--pilot-mode`
- **ComponentHandler system** (`src/testforge/handlers/`): ComponentHandler base class, CDKOverlayHandler, AngularMaterialHandler (mat-select, mat-autocomplete, mat-dialog, mat-tab-group, mat-slide-toggle), PrimeFacesHandler skeleton, ReactMUIHandler skeleton, detect_handler() registry dispatch
- Handler Sprints 1-6: mat-select, mat-autocomplete, mat-dialog, mat-tab-group, mat-slide-toggle, PrimeFaces, React MUI
- Normalizer: shadow DOM, iframe, contenteditable, Select2 combobox blind spot detection, keypress-to-fill compression
- LAB pages: 7 new (Select2, Angular Material, React MUI, Vue Vuetify, mat-autocomplete, mat-dialog, mat-tabs, PrimeFaces select)
- Publisher: auto-publish to Azure DevOps Git, local-mode, CLI --system/--suite, updater, PT-BR healing, zero-config via .testforge/config.yml + GCM
- **Diagnostic Mode (Sprint 0):** FrameworkDetector, CaptureQualityTracker, ReplayCheck, GherkinWriter (pt-BR), DiagnosticTelemetryStore, DiagnosticSession, RecorderController hook, CLI `testforge record --diagnostic-mode`, Publisher for Azure DevOps
- **Architecture v2 (Phases 1-7):** Playwright tracing + CDP AX-tree capture (parallel), v2 LocatorExtractor + Playwright codegen + intent, LocatorResolver + step API + v2 compiler, SQLite intent-keyed catalog + persistent L0, Pipes & Filters infra + 4 stages, zero-dep tracer + dashboard.html, YAML-driven ComponentResolver
- **Recorder — Sprint A:** fill capture for Material currencymask + datepicker
- **Recorder — Sprint J:** Material form-field anchor resolution
- **Recorder — Sprint M:** runtime resolver Material anchor
- **Recorder — Sprint O/P/Q/R/S:** ACCNAME v1.2, mask raw value capture, rrweb-lite DOM mutation timeline, finder CSS optimization, visibility fix
- **Recorder — Sprint A2/A3/B2/B3/D/F:** 6 root-cause fixes for SIMULADOR 15a-f
- **Compiler — Sprint B:** drop ambiguous selectors + soft pos-condition
- **Runner — Sprint 1:** screen-state tracker MVP
- **Runner — Sprint 2:** screen-state drift escalation to L3 healer
- **Metrics:** assert_hit_rate — real pilot success metric + inline UI
- **UX:** QA wizard (--wizard), React _valueTracker reset detection
- **CLI:** --headed, --verify-ssl, --save-output flags, deprecation WARN on legacy `run`
- Recorder: capture fingerprint v1 + recording timeline audit
- Normalizer: H22b per-call dedupe telemetry
- Recording: shadow DOM (B14/B17) + H20 scenario + H21 inline field value prompts
- Healing: L0.5 accessibility tree resolution, compound attribute selectors, multi-attribute fingerprint, runtime multi-attribute self-healing, HealCatalog auto-learning (<1ms reuse)
- Compiler: B29 emit one pytest function per scenario_segment
- CLI: --validate-before-ready, --pilot-mode enhancements
- Test: smoke test (hotfix 13), intent lab LAB-11 to LAB-16
- 14+ diagramas PlantUML sincronizados com codigo
- 9 PUML diagrams for v0.1.0 Diagnostic Mode + Architecture v2

### Fixed

- Recorder (Sprint 1): 9 bugs/capacities
- Recorder Sprint P: exclude volatile Angular state classes from finder
- Recorder: promote XHR/fetch POST after click to pseudo-submit (hotfix 7)
- Recorder: browser close = graceful stop (hotfix 10)
- Recorder: Shift+S closes browser + clear UX (hotfix 14)
- Recorder: UnicodeEncodeError guard during assert selection
- Recorder: 300ms polling flood fix — batch all JS queue reads into one CDP call
- Recorder: persist overlay position across page navigations via localStorage
- Recorder: prevent browser close on error during assert
- Normalizer hotfix 22: IntentReconstructor recovers masked-input values again
- Normalizer H22a: promote final_state above setter_hook + unify priority table
- Normalizer CS-4a: fix --complete writer/reader contract mismatch
- Normalizer B30 rebind synthetic step_N keys + B26/B31 dedup
- Normalizer+Completeness: H9 HTTPS default, H16 verdict semantics, P3 invariants
- Normalizer (4 bugs): contenteditable false positive, Angular datepicker dedup, healing_rejected on Calcular button, element_id usage
- Runner hotfix 6: wait for CDK overlay before clicking inside it
- Runner hotfix 9: restore StepExecutor select_option + fill methods
- Runner hotfix 16: clear field and use raw digits in fallback fill paths
- Runner hotfix 17: detect currency mask by placeholder
- Runner hotfix 19+20: dataclass unwrap and click-only datepicker
- Runner hotfix 15: CWD-independent paths + finalize after close
- Runner: incremental_runner extract recording_id correctly in multi-scenario scripts
- Runner: DD/MM/AAAA date mask detection, Tab after fill, UnboundLocalError in oracle branch
- Executor: accessible_name as fill label, dispatch blur after fill for Angular/React validation
- Dedup: CORPORATIVO datepicker pattern detection, Portuguese error classification
- Healing B23 L0 proposal + B24/B25 text guard + B27/B28 LLM keys
- Healing B33: L0 js-only recipes carry the step's original locator
- Healing H17 finish + B18/B19/B20/B21 false-heal cascade
- Healing+Runner: fix false-heal cascade in FAM-02/05/06
- Diagnostic hotfix 1: heuristic candidates + detection cache
- Diagnostic hotfix 3: Material icon scrub + skip empty-label steps
- CLI hotfix 8: run-incremental accepts directory path
- CLI hotfix 11: --complete prompt shows enriched per-field context
- CLI B32: loud suffix-bump warning + compile sibling fallback
- CLI: correct indentation in cmd_record URL validation
- CLI: editor fallback chain (hotfix 2)
- Publisher hotfix 5: git add -f + --system default to --app
- Publisher: warn when --system/--suite missing, fix None crash, apply send overrides
- Publisher: probe cwd/.testforge/config.yml before git root
- Browser: --window-size only in headless mode, avoid headed resize flicker
- Browser: no_viewport=True in headed mode for all new_context calls
- Bug1: wrap _persist_step in try/except, guard page.title() and page.url
- Bug2+6: use no_viewport=True in headed mode
- Bug3: restore step counter increment after click and submit events
- Bug4: move _auto_publish_recording after validation in cmd_record
- Bug5: add encoding=utf-8 to all write-mode open() calls
- Bug8: expose _OVERLAY_JS as class attribute on RecorderController
- Bug9: fill dedup — DOM-indexed fallback key and skip same-field focus clicks
- Bug11-16: SELECT recording and playback fixes
- GUI: window title 'testforge', combo readonly colors mapped
- Assert: Angular auto-generated ID degradation, element capture + semantic identity + hover highlight
- Recorder: assert menu visibility, simplified assert flow (no confirm dialog, Esc+timeout)
- Viewport: Windows flick fix — new_context(viewport=) instead of set_viewport_size()
- Overlay assert flow + browser close hang + step counter spam
- Windows viewport resize compat
- Step.value has priority over field_value_map
- Normalizer filters SVG inner_html + clicks without candidates
- Masked input detection by placeholder pattern
- fix 9 test failures in categories B/C/D (overlay JS, commands, gate)
- align test expectations with PT-BR linter pass
- align metrics + recording_readiness with PT-BR + H16
- fix linter-induced indent breaks + readiness test for H16
- Metrics: field_snapshots emission + asserts denominator fix

### Changed

- Refactor: extract overlay JS from Python string to overlay_inject.js
- Refactor: merge IntentReconstructor into RecordingNormalizer, delete intent_reconstructor.py
- Refactor: simplify recording_normalizer.py _build_target, remove obsolete helpers
- Refactor: add page.on('framenavigated') for Python-side nav tracking
- Refactor: Pipes & Filters infra — 4 extracted stages (Phase 5)
- Refactor: consolidate fill helpers, add path telemetry (CS-1 + CS-3)
- Normalizer: keypress sequences compacted into single fill before dedup
- Normalizer: datepicker dedup migrated from inline method to handler.normalize()
- StepExecutor: handler detection injected before action routing
- StepPostcondition: improved assert oracle logic
- Documentacao reorganizada: USER-GUIDE, TUTORIAIS, REFERENCIA, ARQUITETURA, DIAGRAMAS
- ADR-006: Phase B evidence consumption
- Comentarios e outputs traduzidos para portugues
- Chore: remove all emojis from source code (replace with ASCII markers)
- Chore: post-sweep cleanup — gitignore .claude, fix browser.py indent
- Chore: remove runs/ and recordings/uncategorized/ from remote
- Perf: batched replay-check + action-only probes + reused resolver (H17)
- Perf: batch all JS queue reads into one CDP call per cycle
- Performance: translate step output to Portuguese, remove blocking DOM capture in light mode

### Tests

- LAB-11 to LAB-16 test suites (mat-select, mat-autocomplete, mat-dialog, mat-tabs, PrimeFaces, React MUI)
- test_intent_lab_pages: 21 pages total (7 new)
- Assert oracle regression tests
- Recorder stability tests
- Smoke test (hotfix 13): end-to-end pipeline smoke on controlled fixture
- Intent lab LAB-11 to LAB-16 (mat-select, autocomplete, dialog, tabs, PrimeFaces, React MUI)

### Docs

- Architecture v2 reference: docs/ARCHITECTURE-V2.md + 3 new diagrams
- Sprint 0 diagnostic mode: flowchart + sequence diagrams
- 9 PUML files sync'd
- CLAUDE.md sync'd
- README.md updated with Sprint 0 features, Architecture v2
- STATE.md updated with M13
- 14+ diagramas PlantUML sincronizados
- Guia de versionamento e sincronizacao de diagramas
