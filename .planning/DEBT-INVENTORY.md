# Structural Debt Inventory

Anti-patterns found in the TestForge codebase as of 2026-06-26. Each entry has evidence, impact, proposed fix, and priority. Read this **before** a refactor sprint to know what is on the table.

> Read order: [DECISIONS-LOG.md](DECISIONS-LOG.md) (history) → this file (current debt) → [CONSOLIDATION-SPRINT.md](CONSOLIDATION-SPRINT.md) (next sprint) → [REFACTOR-SPRINT.md](REFACTOR-SPRINT.md) (after consolidation).
>
> Updated 2026-06-26. Append-only — when an item ships, mark `status: shipped <SHA>` instead of deleting.

---

## Legend

- **Impact**: `pilot-blocker` / `prod-quality` / `dx` / `latent`.
- **Cost**: small (<1d), medium (1-3d), large (>3d).
- **Priority**: P0 (this sprint), P1 (next sprint), P2 (post-pilot), P3 (eventual).
- **Status**: open / in-progress / shipped (with commit SHA).

---

## A. Duplication / divergent paths

### A1 — Fill helpers (4 functions, divergent mask logic)

- **Where**: `src/testforge/runner/step_executor.py`
- **Functions**: `_execute_fill` (canonical), `_fill_input`, `_fill_by_aria_label`, `_try_data_fill`.
- **Evidence**: Hotfix 16 fixed the clear-before-type in `_fill_input` only. Hotfix 17 had to copy the placeholder-based mask fallback to 3 helpers because each had its own copy of the detection logic. Same bug class, two hotfixes, three helpers patched independently.
- **Impact**: pilot-blocker.
- **Cost**: small.
- **Priority**: P0.
- **Status**: planned in `CONSOLIDATION-SPRINT.md` (CS-1).
- **Proposed fix**: extract `_fill_masked(el, value)` as the single mask-aware fill primitive; replace the 4 in-line blocks with calls to it; pin a Material-shaped fixture in CI.

### A2 — RecorderController.stop() and finalize() overlap

- **Where**: `src/testforge/recorder/recorder_controller.py:244-294`
- **Evidence**: Both methods call `_capture_final_state_snapshot` and `flush_events`. The end-of-recording lifecycle is spread across 5 boundaries: `cmd_record` (CLI) → `recorder.stop()` → `recorder.finalize()` → `diagnostic.finalize()` → `browser.close()`. Hotfix 14 reordered close-before-prompt; hotfix 15 added `precapture_for_close` to compensate. Each new ordering change risks racing with the consumers of the old order.
- **Impact**: prod-quality.
- **Cost**: medium.
- **Priority**: P1.
- **Proposed fix**: collapse to a single `recorder.shutdown(close_browser=True|False, gherkin_overrides=None)` method that owns the entire teardown sequence. Browser close becomes a hook the CLI passes in.

### A3 — Path resolution scattered across 4 sites

- **Where**: `_PROJECT_ROOT` in `cli/app.py`, `recordings_root` param in `RecorderController.__init__`, candidate list in `IncrementalRunner._find_recording_dir`, ad-hoc cwd usage in healing catalog and intel-updater.
- **Evidence**: Hotfix 15 had to anchor the CLI at `_PROJECT_ROOT` because user ran from a different CWD; same hotfix extended `_find_recording_dir` with 2 more candidates instead of centralizing.
- **Impact**: prod-quality.
- **Cost**: small.
- **Priority**: P1.
- **Proposed fix**: introduce `testforge.paths` module — single source of project root, recordings root, semantic tests root, healing catalog path. All consumers import from there. Remove ad-hoc `Path.cwd()` and `_PROJECT_ROOT` re-derivations.

### A4 — Three step models for the same concept

- **Where**: `SemanticAction` (semantic/model.py), `RawRecordedEvent` (recorder/raw_event.py), internal Step in IncrementalRunner.
- **Evidence**: Each carries a different subset of the same fields (selector, action, value, context). Conversion between them is implicit and lossy in places. Field-value flow crosses all three.
- **Impact**: latent — most bugs around field_value_map originate here.
- **Cost**: medium.
- **Priority**: P2.
- **Proposed fix**: define `SemanticAction` as the canonical model; `RawRecordedEvent` becomes an explicit ingestion DTO that emits `SemanticAction` deterministically; IncrementalRunner stops re-shaping and consumes `SemanticAction` directly.

### A5 — L0 catalog: JSONL + SQLite coexist

- **Where**: `healing_catalog.jsonl` (root) + `.testforge/intent_catalog.sqlite` (Phase 4 v2).
- **Evidence**: Both shipped; choice is by feature flag passed to `LocatorResolver`. JSONL is the production default, SQLite is opt-in. Two write paths, two read paths, two truth tables.
- **Impact**: latent.
- **Cost**: medium.
- **Priority**: P2 (decide post-pilot which one stays).
- **Proposed fix**: pilot data tells us whether SQLite scaling matters. Pick one, delete the other.

### A6 — Compiler legacy vs v2

- **Where**: `semantic/compiler.py::compile` (legacy) + `compile_v2` (opt-in, `--use-v2-compiler`).
- **Evidence**: Same input, two outputs. Tests cover both but they will drift.
- **Impact**: latent.
- **Cost**: medium.
- **Priority**: P2.
- **Proposed fix**: same as A5 — decide which one stays post-pilot, delete the other.

---

## B. God classes / scattered responsibility

### B1 — RecorderController (540 LOC, 18+ methods)

- **Where**: `src/testforge/recorder/recorder_controller.py`
- **Responsibilities mixed**: session lifecycle (start/stop/finalize), Playwright event handlers (request/response/framenavigated/close), CDP attach, tracing manager, diagnostic session, JS overlay injection, command queue, evidence capture (screenshots/DOM/AX), step persistence, pseudo-submit promotion, field snapshot save, value mutation save.
- **Impact**: prod-quality — every new feature touches this class; tests mock-heavy.
- **Cost**: large.
- **Priority**: P1.
- **Proposed fix**: extract 4 collaborators behind narrow interfaces:
  - `EventCapture` (request/response/framenavigated/close listeners + flush)
  - `SnapshotStore` (DOM, AX, screenshot, final state)
  - `DiagnosticBridge` (talks to DiagnosticSession)
  - `LifecycleController` (start/stop/finalize/shutdown)
  - `RecorderController` becomes a thin facade that wires them.

### B2 — overlay_inject.js (823 LOC, single file)

- **Where**: `src/testforge/recorder/overlay_inject.js`
- **Responsibilities mixed**: UI rendering (banner, buttons, status, assert menu, stop confirm dialog), event listeners (click/input/change/keydown), command queue, sessionStorage persistence, Gherkin auto-derive, value mutation tracker, drag mode, heatmap.
- **Evidence**: hotfix 14 added `_showStoppingUI` inline. Tests do `assert "_showStoppingUI" in RecorderController._OVERLAY_JS` because the JS has no module boundaries to test.
- **Impact**: prod-quality — JS bugs are debugged by reading 800+ lines of one file.
- **Cost**: medium.
- **Priority**: P1.
- **Proposed fix**: split into 4 modules concatenated at load time (or ES modules if we ship a bundler step): `tf-overlay-ui.js`, `tf-event-capture.js`, `tf-command-queue.js`, `tf-gherkin.js`. Test each in isolation via Playwright `page.evaluate`.

### B3 — RecordingNormalizer (1750+ LOC)

- **Where**: `src/testforge/semantic/recording_normalizer.py`
- **Responsibilities mixed**: event compaction (`_compact_events`), intent reconstruction (5 `_ir_*` methods: polling, value_mutations, snapshots, form_values, network), 7-source field-value resolver, completeness check, missing_fill detection, --complete merge.
- **Impact**: prod-quality — the 7-source resolver is the root of CS-4a (user-supplied values ignored).
- **Cost**: large.
- **Priority**: P1.
- **Proposed fix**: extract pipeline stages already started in v2 Phase 5 (`semantic/stages/`); fully migrate normalizer to that. Each `_ir_*` becomes a stage; resolver becomes its own class with a tested priority matrix.

---

## C. Implicit / silent boundaries

### C1 — `try / except / pass` proliferation

- **Where**: 20+ sites across recorder_controller, app.py, runner.
- **Evidence**: Hotfix BUG 2 introduced "tolerate closed page" pattern with `try/except: pass`. The shape was copied for every subsequent "may fail" call. No policy on which exception classes to swallow vs log vs raise. Silently loses real errors (e.g. permission denied on file write masked as "tolerated").
- **Impact**: prod-quality — debugging is harder because errors are eaten.
- **Cost**: medium.
- **Priority**: P1.
- **Proposed fix**: introduce a `@tolerate(closed=True, log_level="debug")` decorator or context manager that documents *why* the call is tolerated and *what* class it expects. Replace bare `try/except: pass`. Sweep with a linter rule.

### C2 — field_value_map: 7-source resolver, no central authority

- **Where**: `recording_normalizer.py` priority chain references: `form_values`, `fill_event`, `setter_hook`, `checked_transition`, `snapshot_diff`, `final_state`, `missing_fill`, `user_supplied_cli`.
- **Evidence**: Bug from `test-pos-hotfix3` real run — user supplied "CPF" via `--complete`, value never reached the field, `fill [FAIL]`. Cause: source keys sanitized differently (`cpf` lowercase + underscore) than runtime aria-label (`"CPF *"`). No fuzzy resolver between them.
- **Impact**: pilot-blocker.
- **Cost**: small.
- **Priority**: P0 — folded into the consolidation sprint as CS-4a.
- **Proposed fix**: `FieldValueResolver` class with explicit `(canonical_key, candidate_keys, source_priority, runtime_label_norm)` matrix. Tested as a unit. Same fuzzy match between record-time and runtime aria-label.

### C3 — value_kind detected in 3 layers

- **Where**: `diagnostic/capture_quality.py::detect_value_kind`, `validation/intent_completeness.py` (implicit via reason strings), healer prompts.
- **Evidence**: Each layer has its own regex set. Drift will mask completion-quality reports against actual healer behavior.
- **Impact**: latent.
- **Cost**: small.
- **Priority**: P2.
- **Proposed fix**: single `value_kinds.py` module exporting one detector + the regex table.

---

## D. Half-finished patterns ("we'll plumb it later")

### D1 — Hotfix 7 pseudo-submit in-memory only

- **Status**: shipped fix in hotfix 12 (commit 552e05c). **Pattern remains a risk.**
- **Lesson**: any "we'll wire it up later" is technical debt. Either wire it now or open an explicit backlog ticket with deadline.

### D2 — v2 Phases 1-7 feature-flagged, never load-bearing

- **Where**: `--use-cdp-recorder`, `use_pipeline=True`, `--use-v2-compiler`, `LocatorResolver(sqlite_catalog=...)`, `ComponentResolver()`.
- **Evidence**: All 7 phases shipped (2026-06-15 to 06-22). Pilot ran on legacy. Bugs found are all in legacy paths. v2 code exists but is dead in production.
- **Impact**: latent + maintenance — duplicates code surface.
- **Cost**: medium per phase.
- **Priority**: P2 (decide post-pilot).
- **Proposed fix**: for each phase, decide (a) flip on by default and migrate consumers, or (b) delete. No middle.

### D3 — AX snapshots captured, never consumed

- **Where**: `recordings/<id>/ax_snapshots/<eid>.json` — Phase 1 writes these when `--use-cdp-recorder`.
- **Evidence**: Zero consumers. Normalizer ignores. Compiler ignores. L3 healer ignores. Storage waste.
- **Impact**: latent (gap G1 from research doc).
- **Cost**: medium to consume.
- **Priority**: P2.
- **Proposed fix**: post-pilot, plumb AX-tree-as-YAML into L3 prompt (matches Playwright MCP). Otherwise stop writing them.

### D4 — ComponentHandler: 5 handlers, 2 are skeleton-only

- **Where**: `handlers/{angular_material,cdk_overlay,primeFaces,react_mui,abc}.py`
- **Evidence**: Angular Material + CDK Overlay execute and normalize. PrimeFaces and MUI detect-only. ABC is a stub.
- **Impact**: latent — `detect()` returns "primeFaces" but downstream handler is a noop. False positives in framework metrics.
- **Cost**: medium per framework.
- **Priority**: P2.
- **Proposed fix**: post-pilot data tells us which frameworks QA actually hits. Promote skeletons to full implementations only for the frameworks that appear. Mark detect-only ones explicitly in session.json so dashboards can show "framework detected but handler skeleton".

---

## E. Recorder ↔ runner mismatch

### E1 — Compiler emits selectors, runner re-derives chain

- **Where**: `semantic/compiler.py` (compile-time) + `runner/fallback_runner.py` + `runner/step_executor.py` (runtime).
- **Evidence**: Compiler picks the candidate chain at compile time; SmartStepRunner has 10 runtime strategies (`visibility_wait`, `press_sequentially`, `overlay_dismiss`, …) that can substitute. The two never agree on which strategy wins. Tests cover each in isolation; integration is informal.
- **Impact**: prod-quality — explains why hotfix-per-strategy keeps happening.
- **Cost**: medium.
- **Priority**: P1.
- **Proposed fix**: define a `LocatorStrategy` enum; compiler emits a list ordered by strategy; runner walks that list deterministically. Healing strategies become explicit "level-up" annotations rather than implicit fallthroughs.

### E2 — Click-but-actually-fill (silent action promotion)

- **Where**: `runner/step_executor.py:155-205`
- **Evidence**: A step compiled as `action="click"` can be silently promoted to a fill at runtime if `context.missing_fill=True`. Compiler does not know. Tests of compile do not exercise it. Last run's `Step 12/14 click [OK] passed [field_map:Prestação desejada *]` — the user reads "click" and gets a fill.
- **Impact**: pilot-blocker — root of multiple "field not filled" reports including the current `fill [FAIL]` on `--complete`.
- **Cost**: small (logging) + medium (proper compile-time decision).
- **Priority**: P0 logging; P1 design change.
- **Proposed fix**:
  - **Now (sprint CS-3)**: emit a `span.fill.attempted` with `action_promoted: click→fill` so the magic is auditable.
  - **Next sprint**: normalizer emits `action="fill"` explicitly when a click is on an input element with a known value; runner does **not** promote silently.

### E3 — step_index meaning differs between compile and runtime

- **Where**: `SemanticTestCase.steps[step_index]` (compile) vs runtime's normalized index.
- **Evidence**: When `--complete` adds values, normalizer re-runs and the step list may shift; the runtime resolver looks up `step_index` from raw_events which used the original index. Field-value mapping drifts.
- **Impact**: prod-quality.
- **Cost**: small.
- **Priority**: P1.
- **Proposed fix**: introduce a stable `step_id` (UUID at recording time) and key everything off that, not numeric index.

---

## F. Documentation / traceability

### F1 — "hotfix N" commits without design intent link

- **Where**: 14+ commits named `fix(...): hotfix N — short message`.
- **Evidence**: When a regression appears, locating the commit that introduced a behavior requires reading every hotfix commit message in sequence. No issue tracker references, no design-doc links.
- **Impact**: dx.
- **Cost**: small.
- **Priority**: P3 (process change, not code).
- **Proposed fix**: every fix commit references `DECISIONS-LOG.md` or `BACKLOG.md` item ID in the body.

### F2 — No decisions log until 2026-06-26

- **Status**: shipped (commit 0c4b34a) — DECISIONS-LOG.md exists. **Backfill of 2026-06-13 → 06-25 is the lossy part; recovered from commit log and CLAUDE.md.**

### F3 — Tests cover bugs, not contracts

- **Where**: 80+ test files; most are reproductions of specific bugs.
- **Evidence**: No file documents the contract of `RecorderController.start()` separately from the implementation. Mock-heavy tests pass while integration breaks.
- **Impact**: latent.
- **Cost**: medium.
- **Priority**: P2.
- **Proposed fix**: a `tests/contracts/` directory with one file per public class documenting "what start() promises". Used in code review.

---

## Summary by priority

### P0 — current sprint (CONSOLIDATION-SPRINT.md)

- A1 Fill helpers consolidation
- C2 FieldValueResolver (folded into CS-4a)
- E2 Click-but-actually-fill — logging only

### P1 — next sprint (REFACTOR-SPRINT.md, to be written)

- A2 stop/finalize collapse
- A3 testforge.paths module
- B1 RecorderController split
- B2 overlay JS split
- B3 RecordingNormalizer stages migration
- C1 `@tolerate` decorator policy
- E1 LocatorStrategy enum + deterministic runner
- E2 Click-but-actually-fill — design change
- E3 stable `step_id`

### P2 — post-pilot

- A4 unified step model
- A5/A6 decide v2 vs legacy (catalog + compiler)
- C3 value_kinds module
- D2 v2 phases: flip or delete
- D3 AX-tree consumer
- D4 ComponentHandler full impl per framework
- F3 contracts directory

### P3 — process

- F1 commit message references

---

## Estimation guide

If the next refactor sprint takes P1 in full:

- A2 stop/finalize: 1d
- A3 paths module: 0.5d
- B1 RecorderController split: 2-3d
- B2 overlay split: 1-2d
- B3 Normalizer stage migration: 2-3d (already partially done in v2 Phase 5)
- C1 `@tolerate`: 0.5d
- E1 LocatorStrategy: 1-2d
- E2 design change: 1d
- E3 step_id: 0.5d

Total: ~10-14 working days. Plan accordingly — likely split into 2 sprints if the team is small.
