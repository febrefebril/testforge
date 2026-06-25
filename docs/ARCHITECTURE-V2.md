# TestForge v2 — Architecture Reference (Phases 1-7)

**Updated:** 2026-06-25 (post-migration)
**Branch:** `refactor/recorder-playwright`
**Diagrams:**
- [fluxograma-pipeline-v2.puml](diagramas/fluxograma-pipeline-v2.puml) — end-to-end pipeline
- [sequencia-fluxo-completo-v2.puml](diagramas/sequencia-fluxo-completo-v2.puml) — record → compile → run sequence
- [sequencia-assert-flow.puml](diagramas/sequencia-assert-flow.puml) — assert capture and execution

---

## What changed in the migration

| Concern | Before (v0.4.1) | After (v2 / Phase 1-7) |
|---|---|---|
| Capture transport | JS overlay + sessionStorage polling | Playwright `tracing.start()` + CDP `Accessibility.getFullAXTree` (parallel, opt-in) |
| Snapshot per event | DOM HTML text | AX tree JSON via CDP + `trace.zip` (3 DOM snapshots per action) |
| Locator candidate | `(strategy, selector, score, reason)` | Super-selector with `playwright_call`, `intent_text`, `attribute_stability`, `ax_path`, `ancestor_roles`, `backend_node_id` |
| Selector scoring | Hand-tuned magic numbers (0.95, 0.92, ...) | `attribute_stability(target) × STRATEGY_WEIGHTS[strategy]` |
| Compiled `.py` | 600+ lines, try/except per step | ~10 lines: `from testforge.runtime import step` + 1 call per step |
| Fallback chain | Frozen in compiled `.py` | Runtime `LocatorResolver` — change chain without recompiling tests |
| L0 cache | Substring-keyed JSONL | SQLite `intent_catalog.sqlite` keyed by `(intent_text, url_signature, action)` |
| Healing transparency | `readiness_report.md` per recording | JSONL spans + `dashboard.html` + Playwright `trace.zip` |
| Component detection | 5 hand-rolled handler classes | `component_patterns.yaml` declarative + lazy backend |

---

## Phase-by-phase summary

| Phase | Commit | Module | Public surface |
|---|---|---|---|
| 1 | `7a24ec4` | `recorder/{tracing_manager,cdp_snapshot}.py` | `testforge record --use-cdp-recorder` |
| 2 | `3550781` | `semantic/locator/*` | `RecordingNormalizer(use_v2_locator=True)` |
| 3 | `f54abbd` | `runtime/{resolver,step,_pw_dispatch,errors}.py`, `compile_v2` | `testforge compile --use-v2-compiler` |
| 4 | `750e2ac` | `healing/sqlite_intent_catalog.py` | `testforge catalog-migrate / catalog-export` |
| 5 | `c800311` | `semantic/stages/*` | `RecordingNormalizer(use_pipeline=True)` |
| 6 | `8f25b9f` | `metrics/{telemetry,dashboard}.py` | `testforge dashboard`, env `TESTFORGE_TRACING` |
| 7 | `b941950` | `handlers/component_resolver.py`, `config/component_patterns.yaml` | `ComponentResolver().find_handler(step)` |
| 8 | — | — | **Deferred to backlog** (paper arXiv 2603.20358 shows 100% without vision) |

All phases are **additive with feature flags** — legacy paths still work unchanged.

---

## How asserts work

### Capture
1. QA presses **Shift+A** (or clicks the "Assert" button on the overlay) → `_tf_enterAssertMode()` (`overlay_inject.js:532`).
2. Cursor enters selection mode (orange outline). Next click captures the element.
3. Menu shows 4 assert types:

   | Type | Captured value |
   |---|---|
   | **Text** (textual) | `textContent`, cleaned, ≤200 chars |
   | **State** (estado) | `checked` / `unchecked` / `enabled` / `disabled` |
   | **Visible** (visivel) | `visible` / `hidden` (bounding-box test) |
   | **Auto** (automatico) | textual + state |

4. `_addStep('assert', el, type)` (`overlay_inject.js:263`) writes a record to `__tfStepQueue` with `assert_type`, `assert_state`, `expected_value`.
5. `RecorderController._persist_step()` (`recorder_controller.py:226`) appends to `recordings/<name>/steps.jsonl`.

### Normalize
`RecordingNormalizer._convert_step()` (`recording_normalizer.py:1191`) reads the step and builds a `SemanticAction(action="assert", target=..., value=expected, context={"assert_type": ..., "assert_state": ...})`.

### Compile
- **v2** (`compiler._emit_v2_call`, line 157): emits one line — `step.assert_text(page, intent='assert text "Welcome"', expected="Welcome", candidates_file="step_NNN.json")`.
- **Legacy** (`compiler._gen_assert`, line 834): emits an inline `try/except` block per assert type.

### Run
`runtime.step.assert_text(page, intent, expected, candidates_file)`:
1. Resolve intent → `Locator` via `LocatorResolver`.
2. `locator.first.wait_for(state="visible", timeout=10s)`.
3. Read `text_content()`.
4. Substring check (case-insensitive). Raise `AssertionError` with intent + actual on mismatch.

`step.assert_visible(...)` exists for visibility-only checks.

---

## How users control recording

### Keyboard shortcuts (overlay_inject.js:551-574)

| Key | Action |
|---|---|
| **Shift+P** | Pause / resume |
| **Shift+S** | Stop (confirmation if zero asserts) |
| **Shift+A** | Enter assert mode |
| **Shift+M** | Toggle drag for the overlay panel |
| **Esc** | Cancel assert mode |

### Overlay UI (top-right corner)

- Buttons: Pause `||`, Stop `[]`, Assert
- Counters: passos / asserts (synchronized through `sessionStorage` across navigations)
- Status text: gravando / pausado / assert mode
- Context label: `system / suite / test_case` if provided via CLI

### CLI flags (`testforge record`)

```bash
--name <id>                  # recording ID
--system / --suite / --test-case   # path in Git: recordings/{system}/{suite}/{tc}/
--headless                   # no window
--evidence-level light|full  # full = screenshot + DOM per event
--complete                   # check completeness + prompt missing values
--no-interactive             # write a template instead of asking
--validate-before-ready      # run IncrementalRecordingValidator before READY
--pilot-mode                 # automatic validation + reporting
--use-cdp-recorder           # (Phase 1) parallel CDP AX-tree + trace.zip capture
```

---

## Compiled test maintainability

The v2 compiled script is intentionally tiny:

```python
"""Compiled by TestForge v2 compiler — fallback chain runs in runtime LocatorResolver."""
from playwright.sync_api import Page
from testforge.runtime import step

BASE_URL = "http://localhost:8765"

def test_simulador_credito(page: Page):
    step.go(page, BASE_URL)
    step.fill(page, intent='fill textbox "CPF"', value="12345678900",
              candidates_file="step_001.json")
    step.click(page, intent='click button "Simular"',
               candidates_file="step_002.json")
    step.assert_text(page, intent='assert text "Aprovado"',
                     expected="Aprovado", candidates_file="step_003.json")
```

Each step's candidates live alongside it:

```
semantic_tests/ST-simulador-credito/
├── test_st_simulador_credito.py
├── test_data.json                    # fields + sensitive_alerts
└── candidates/
    ├── step_001.json
    ├── step_002.json
    └── step_003.json
```

**Implications**
- A reviewer reads the `.py` once and sees the user intent of every step in plain language.
- Changing the fallback strategy (Phase 3 runtime resolver) does not require recompiling tests.
- A failed step shows the intent text in the error, not a CSS selector.
- The candidates JSON is an audit trail of what the recorder believed at compile time; the SQLite catalog tracks what actually worked at run time.

---

## Test data separation

`testforge compile <rec> --data` runs `data_extractor.py`:

1. Walks raw fill events.
2. Builds a field name with priority `label > placeholder > element_id > field_N`.
3. Detects sensitive fields (CPF, senha, cartão, email, RG, telefone, CEP, conta, agência, token) by regex.
4. Writes `semantic_tests/ST-X/test_data.json`.

**Flat layout (default):**

```json
{
  "fields": {
    "cpf": "12345678900",
    "renda_mensal": "5000"
  },
  "sensitive_alerts": [
    { "field": "cpf", "pattern": "(?i)cpf" }
  ]
}
```

**Multi-scenario layout (`--scenarios`):**

```json
{
  "scenarios": {
    "default":      { "cpf": "12345678900", "renda_mensal": "5000" },
    "renda_baixa":  { "cpf": "98765432100", "renda_mensal": "1500" }
  }
}
```

The generated script reads `_DATA_FILE` at the top, falls back to a hard-coded default only if the file is missing. Changing values means editing the JSON — no recompilation.

---

## New CLI commands shipped in this migration

| Command | Phase | Purpose |
|---|---|---|
| `testforge record --use-cdp-recorder` | 1 | Parallel Playwright tracing + CDP AX-tree capture (writes `trace.zip` + `ax_snapshots/`) |
| `testforge compile --use-v2-compiler` | 3 | Minimal script + per-step JSON candidates |
| `testforge catalog-migrate --source <jsonl> --db <sqlite>` | 4 | Import legacy JSONL recipes into SQLite |
| `testforge catalog-export --db <sqlite> --output <jsonl>` | 4 | Export active intent resolutions as JSONL for Git review |
| `testforge dashboard --output reports/dashboard.html` | 6 | Static observability dashboard (Chart.js, zero infra) |

Environment variable `TESTFORGE_TRACING=0` disables span emission globally.

---

## Storage layout (post-migration)

```
recordings/<name>/                  # raw capture
  raw_events.jsonl
  steps.jsonl
  recording_metadata.json
  ax_snapshots/<event_id>.json      # Phase 1, when --use-cdp-recorder
  trace.zip                         # Phase 1, when --use-cdp-recorder

semantic_tests/ST-<name>/           # compiled artifacts
  test_st_<name>.py                 # legacy OR v2
  test_data.json                    # --data
  semantic_steps.jsonl              # audit
  readiness_report.md
  candidates/                       # Phase 3 v2 only
    step_NNN.json

.testforge/                         # runtime state
  spans.jsonl                       # Phase 6
  intent_catalog.sqlite             # Phase 4

reports/                            # dashboards
  pilot_readiness_report.{json,md}
  dashboard.html                    # Phase 6
```

---

## Open work / deferred

1. **Cutover handlers `detect()`** — Phase 7 ships parity; delete legacy methods after one release.
2. **Cutover `_build_target`** — Phase 2 ships v2 candidates as append-only; delete legacy heuristics after `compile_v2` becomes default.
3. **Convert + intent reconstruction stages** — Phase 5 extracted Load/Dedup/Compact/Audit; Convert and `_ir_*` remain in normalizer and are due in a follow-up sprint.
4. **L2/L3 plumbing into LocatorResolver** — today, L2 specialist agents and L3 LLM still run via the legacy `fallback_runner`. Wiring them into `LocatorResolver` is the next observable-quality win.
5. **Phase 8 vision L4** — backlog; not justified by current evidence.
