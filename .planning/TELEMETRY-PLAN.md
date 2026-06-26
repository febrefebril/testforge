# TestForge — Telemetry Plan for Pilot

**Status**: proposal · **Branch**: `hotfix/sprint-0-recorder-fixes` · **Date**: 2026-06-25

The pilot ships TestForge to QA testers running real workflows in a multi-framework
banking SUT (Angular Material + PrimeFaces + React MUI + CDK Overlay coexisting on the
same page, e.g. SIOPI / simuladorhabitacao.caixa.gov.br). We need telemetry that, once
the pilots come back, can answer six questions:

1. Did we generate **resilient** tests? (Pass rate on the Nth playback as the SUT drifts.)
2. Did **self-healing** save the run, and **which tier** (L0/L1/L2/L3) — at what latency
   and LLM-token cost?
3. **Where** do tests still fail despite healing — which family (FAM-01…FAM-11) and which
   framework?
4. Did **recording-quality blind spots** correlate with run-time failures?
5. Are recordings **deterministic** — does re-recording the same workflow converge to the
   same locator set?
6. **Per framework** breakdown of all of the above — Angular Material vs PrimeFaces vs MUI.

Constraints: small team, no hosted backend, JSONL on disk + static HTML dashboard is the
ceiling. Pilot data contains real banking PII (CPF, account numbers, currency values) —
all schema fields are marked PII-sensitive (P) where applicable, with redaction rules in
§7.4.

---

## 1. Primary KPIs (5–7 numbers, comparable across pilots)

| # | KPI | Definition | Target | Why |
|---|---|---|---|---|
| K1 | `playback_pass_rate` | runs with all steps green / total runs (per recording, rolling over last 5 plays) | ≥ 0.90 by play #3 | Core thesis: tests stay green as SUT evolves |
| K2 | `heal_save_rate` | runs where ≥1 step required L0/L1/L2/L3 AND run finished green / total runs that needed healing | ≥ 0.80 | Did healing actually rescue the run, vs theatre |
| K3 | `heal_distribution` | share of healed steps resolved at L0 / L1 / L2 / L3 (sums to 1.0) | L0+L1 ≥ 0.80 of heals | LLM-on-every-step (ZeroStep) failure mode |
| K4 | `mean_llm_cost_per_run_usd` | sum(L3 prompt + completion tokens × price) / runs | ≤ $0.02 | Caps cost at enterprise scale (Ramadan 2025) |
| K5 | `recording_health_score` | weighted aggregate of capture quality at record time (1 − blind_spot_rate, value_captured rate, primary_selector rate, ax_snapshot rate) | ≥ 0.85 | Catches bad recordings *before* playback |
| K6 | `determinism_score` | locator-fingerprint Jaccard between paired re-recordings of the same workflow | ≥ 0.75 | Are recordings reproducible? |
| K7 | `unresolved_failure_rate_by_family` | failures that even L3 couldn't heal / total failed steps, broken out per FAM-XX | < 0.05 each family | Where to invest next |

K1+K2+K3 form the "did healing work" story. K5+K6 form the "did recording work" story.
K4 caps cost. K7 routes engineering attention.

---

## 2. Per-Layer Signals (L0 / L1 / L2 / L3)

For **each** of the four layers, capture per-invocation:

| Field | L0 catalog | L1 fallback | L2 agents | L3 LLM |
|---|---|---|---|---|
| `invocations` | hit attempts | candidate walks | agent runs | LLM calls |
| `successes` | catalog match passed | a candidate worked | agent proposal passed | proposal validated AND executed |
| `success_rate` | succ/inv | succ/inv | succ/inv | succ/inv |
| `latency_p50_ms` / `latency_p95_ms` | <50 target | <2000 | <100 | <3000 |
| `attempts_before_hit` | n/a | candidate_index distribution | n/a | retry_count |
| `cost.tokens_prompt` / `tokens_completion` | — | — | — | required |
| `cost.usd` | — | — | — | required |
| `miss_reason` | `no_recipe` / `low_confidence` / `selector_unsafe` | `score_too_low` / `all_failed` | `family_unsupported` / `low_confidence` / `taxonomy_invalid` | `parse_failed` / `strategy_disallowed` / `executed_but_failed` |
| `cache_state` (L0 only) | `mem_hit` / `sqlite_hit` / `mem_miss_sqlite_hit` / `cold_miss` | — | — | — |
| `eviction_event` (L0 only) | stale promotion, status flip | — | — | — |

**Practical capture points** (these all need wiring — see §9):

- L0: emit `heal.l0.attempted` / `heal.l0.succeeded` from `HealingCatalog.match_recipes()`
  and `LocatorResolver._resolve_impl()` (cache hit branch).
- L1: emit `heal.l1.attempted` per candidate, `heal.l1.succeeded` on first hit. The
  `candidate_index` is the cheap "how far down the list did we get" signal.
- L2: emit one `heal.l2.<agent_name>.attempted/succeeded` per `CuradorAutomatico._try_layer2_agents()`
  invocation. `agent_name` ∈ {selector, timing, context, state, dynamic_dom, input}.
- L3: emit `heal.l3.attempted/succeeded` with `model`, `tokens_prompt`, `tokens_completion`,
  `tokens_total`, `usd_estimated`, `retries`, `parse_status`.

A run's heal envelope is then: `runs_with_heal`, `mean_heal_depth` (deepest layer used per
run; 0 if green without healing).

---

## 3. Per-Framework Signals

Detected primary framework comes from `FrameworkDetector.detect()['primary']` ∈
`{angular-material, angular, primefaces, mui, react, vue, jsf, custom, unknown}`. Every
recording-level and step-level event carries `framework.primary`. Multi-framework pages
(common in the SIOPI app) also carry the boolean flags `framework.has_angular`,
`framework.has_primefaces`, `framework.has_mui` so we can detect mixed-stack pages.

KPIs to roll up per `framework.primary`:

- `K1_playback_pass_rate[fw]`
- `K2_heal_save_rate[fw]`
- `K3_heal_distribution[fw]` (does PrimeFaces dominate L3?)
- `K7_unresolved_failure_rate_by_family[fw][fam]` — 2D pivot

**Decision lens.** If `K3[primefaces].L3` >> `K3[angular].L3`, invest in PrimeFaces L2
specialist agents (we already have `selector_agent.py` — extend it). If
`K1[mui] << K1[angular-material]`, invest in MUI-specific candidate extraction. We
explicitly **do** want per-framework rollup, not single aggregate — the whole point of
TestForge is multi-framework resilience.

A single aggregate is still emitted for the dashboard's top tile, but every other chart
slices by `framework.primary`.

---

## 4. Recording-Quality Signals

Captured at record time (today: partially captured by `CaptureQualityTracker.assess()` and
`DiagnosticSession` — see §9 for gaps). Per recording:

| Signal | Source today | Aggregation |
|---|---|---|
| `typing_not_captured_rate` | `blind_spots` contains `typing_not_captured` | count / fill-actions |
| `no_primary_selector_rate` | `blind_spots` contains `no_primary_selector` | count / steps |
| `long_gap_count` | `blind_spots` contains `long_gap` (idle > 10s) | count |
| `overlay_click_noise_count` | `blind_spots` contains `overlay_click_noise` | count |
| `network_postback_detected_rate` | NEW — derive from raw_events network calls between user actions | postbacks / user-actions |
| `ax_snapshot_present_rate` | `recordings/<id>/ax_snapshots/<eid>.json` exists | files / steps |
| `candidate_count_p50` / `p95` | `selector_generated.candidates_count` distribution | percentiles |
| `value_captured_at_event_rate` | `capture_quality.value_captured_at_event` | true / total |
| `pii_value_kind_count` | `value_kind` ∈ {cpf_BR, cnpj_BR, email, phone_BR, cep_BR, currency_BR} | per kind |
| `framework_consistency` | distinct `framework.primary` values seen per recording (should be 1) | dummy count |

These feed `K5 recording_health_score` and the recording-quality dashboard tile. The
typing_not_captured rate is the leading indicator for downstream FAM-01 SEL / FAM-06 INP
failures — establish baseline now, regress on it.

---

## 5. Determinism Signals

The same QA tester records the same workflow twice → ask: did we produce comparable
locator sets?

Per recording, compute and store a **locator fingerprint set**:

```
fingerprint = {
  intent_text_normalized,
  (primary_strategy, primary_selector_normalized),
  set(secondary_strategies),
  framework.primary,
}
```

`intent_text_normalized` strips values and PII — only role + accessible name + action
type. `primary_selector_normalized` collapses numeric IDs (`j_idt412` → `j_idt*`) the same
way `sqlite_intent_catalog.normalize_url` does for paths.

Determinism metrics (computed per *pair* of recordings flagged as "same workflow" — pilot
testers tag with a `workflow_id` env var or CLI flag):

| Metric | Definition | Target |
|---|---|---|
| `intent_overlap_jaccard` | \|A.intents ∩ B.intents\| / \|A.intents ∪ B.intents\| | ≥ 0.95 |
| `locator_fingerprint_jaccard` | as above over the full fingerprint tuple | ≥ 0.75 |
| `framework_consistency_pair` | `A.framework == B.framework` | true |
| `step_count_delta` | abs(\|A\| − \|B\|) / max(\|A\|, \|B\|) | ≤ 0.10 |

Low determinism on the same workflow is a recorder bug, not a SUT problem — file under
FAM-09 REC. The metric also gates "are tests cross-tester portable" once we have multiple
QA pilots.

---

## 6. Failure Attribution

Per failed run, per failed step, log:

```
fail.attribution = {
  family: "FAM-01",                        # taxonomy from FailureClassifier
  taxonomy_id: "SEL-001",                  # specific code
  last_failed_locator_kind: "role",        # which strategy was last tried
  last_failed_selector: "<redacted>",      # P — redact via §7.4
  layers_attempted: ["L0_mem_miss", "L1_role", "L1_test_id", "L2_selector_agent", "L3"],
  layer_outcomes: {
    L0: "miss",
    L1: "all_failed",
    L2: "low_confidence",
    L3: "executed_but_failed"
  },
  framework: "angular-material",
  url_signature: "host=app path=/credito/*",
  classification_confidence: 0.85,
  classifier_matched_by: "keyword",        # "keyword" | "group" | "llm"
}
```

Aggregate views:

- **Per family count** — how many runs hit each FAM-XX.
- **Per family × framework heatmap** — where does each framework hurt?
- **Per family layer-of-last-attempt distribution** — does FAM-06 INP always escalate to
  L3? Then build the L2 input agent better.
- **Top 10 failing taxonomy_ids by absolute count** — the to-do list for next sprint.

---

## 7. Proposed JSONL Schema for `.testforge/spans.jsonl`

### 7.1 Design

Keep the current Phase 6 OTel-compatible shape (`name`, `trace_id`, `span_id`,
`parent_span_id`, `start_time`, `end_time`, `duration_ms`, `status`, `attributes`). Add
**typed event names** so consumers can filter without parsing the attribute soup. Use
dotted namespace: `recording.*`, `compile.*`, `run.*`, `step.*`, `resolve.*`, `heal.*`,
`assert.*`, `diagnostic.*`.

### 7.2 Required fields on every span (in addition to OTel envelope)

- `tester_hash` — opaque hash of the OS user, no real name. (P-derived but irreversible.)
- `recording_id` — directory name.
- `run_id` — UUID minted at run start (`run.start` span). Same value on every span in that
  run via trace.
- `framework.primary` — string (see §3).
- `url_signature` — `host=<host> path=<normalized>` from `sqlite_intent_catalog.normalize_url`.
- `schema_version` — int. Start at `1`. Bump on breaking changes.

### 7.3 Event catalog

| event `name` | parent | required attrs | optional attrs | unit notes |
|---|---|---|---|---|
| `recording.start` | (root) | `recording_id`, `tester_hash`, `app_url_signature`, `framework.primary`, `recorder.use_cdp`, `recorder.use_v2_locator` | `recorder.version` | `start_time` only |
| `recording.step` | recording.start | `step_id`, `action` (click/fill/select/assert/navigate), `intent_text` | `value_kind`, `value_len`, `value_source`, `candidates_count`, `primary_strategy`, `primary_score`, `blind_spots`, `idle_before_ms`, `ax_snapshot_present`, `framework.is_mat`, `framework.is_cdk_overlay` | values themselves NOT logged (PII) |
| `recording.replay_probe` | recording.step | `step_id`, `resolved` (bool), `selector_attempted` (P) | `fallback_strategy`, `fallback_index`, `elapsed_ms`, `error` | record-time fragility check |
| `recording.stop` | recording.start | `recording_id`, `steps_total`, `asserts_total`, `blind_spots_total`, `value_missing_count`, `value_captured_count`, `selectors_immediate_ok`, `selectors_immediate_fail` | `audit.quality_score` | one per recording |
| `compile.start` | (root) | `recording_id`, `compiler_version`, `use_v2_compiler` | `flags` | |
| `compile.end` | compile.start | `status` (ok/fail), `steps_compiled`, `candidates_per_step_p50`, `candidates_per_step_p95`, `assertions_compiled` | `error.message` | |
| `run.start` | (root) | `run_id`, `recording_id`, `framework.primary`, `play_number` (1=first, 2+=replay), `runner_version`, `headless` | `git_sha`, `sut.version_hint` | |
| `step.click` / `step.fill` / `step.select` / `step.assert_text` / `step.assert_visible` | run.start | `step_id`, `intent_text`, `action`, `framework.primary` | `value_kind`, `value_len`, `target_role` | values NOT logged — only kind+len |
| `resolve` | step.* | `intent_text`, `action`, `candidate_count`, `level` (`L0_cache`/`L1_candidate`/`FAILED`), `strategy`, `score`, `candidate_index`, `elapsed_ms`, `framework.primary` | `attempted` (list, max 10), `cache_source` (`mem`/`sqlite`/`none`) | currently emitted in Phase 6 — EXTEND with framework + cache_source |
| `heal.l0.attempted` | step.* | `intent_text`, `family`, `recipe_id_matched` (or null) | `match_score` | NEW |
| `heal.l0.succeeded` | heal.l0.attempted | `recipe_id`, `elapsed_ms` | | NEW |
| `heal.l1.attempted` | step.* | `intent_text`, `candidate_index`, `strategy`, `score` | `selector` (P), `tag` | NEW — extract from `FallbackRunner` / `_try_layer1_candidates` |
| `heal.l1.succeeded` | heal.l1.attempted | `winning_index`, `winning_strategy`, `elapsed_ms` | | NEW |
| `heal.l2.attempted` | step.* | `family`, `agent_name`, `taxonomy_id` | `error_message` (P-trim 200ch) | NEW |
| `heal.l2.succeeded` | heal.l2.attempted | `proposal.strategy`, `proposal.confidence`, `elapsed_ms` | `proposal.new_locator` (P) | NEW |
| `heal.l3.attempted` | step.* | `family`, `model`, `prompt_chars` | `evidence_size_bytes` | NEW |
| `heal.l3.succeeded` | heal.l3.attempted | `proposal.strategy`, `proposal.confidence`, `tokens_prompt`, `tokens_completion`, `tokens_total`, `usd_estimated`, `retries`, `elapsed_ms`, `parse_status` (ok/empty/json_error/strategy_disallowed/taxonomy_invalid) | `proposal.new_locator` (P) | NEW |
| `step.failed` | step.* | `family`, `taxonomy_id`, `classifier_matched_by`, `layers_attempted` (list), `layer_outcomes` (dict) | `error.message` (P-trim) | NEW — one per step that ends red even after heal |
| `run.end` | run.start | `status` (pass/fail/error), `steps_total`, `steps_passed`, `steps_failed`, `heals_l0`, `heals_l1`, `heals_l2`, `heals_l3`, `tokens_total`, `usd_estimated`, `duration_ms` | `trace_zip_path` | one per run |
| `assert.failed` | step.assert_* | `expected_kind` (text/visible/state/auto), `actual_excerpt_hash` (sha256 first 12 chars; do NOT log actual text) | `taxonomy_id` (AST-xxx) | hash-only to avoid leaking SUT data |
| `diagnostic.step` / `diagnostic.replay` | recording.* | already defined in `telemetry_store.py` | — | KEEP — rename `diagnostic.replay` → `recording.replay_probe` consolidation (§9) |

### 7.4 PII / redaction rules

Bank workflows contain CPF, CNPJ, currency values, account numbers, names. Apply at write
time in `Tracer._write()`:

- **Never log**: raw input values, raw assertion `actual` text, raw fill text. Replace with
  `value_kind` + `value_len` + (assertions only) `actual_excerpt_hash` (sha256 first 12).
- **Hash-with-salt**: `tester_hash` (already done in `session.json`).
- **Redact pattern**: any string attribute matching CPF/CNPJ/CC/CEP regex (reuse
  `capture_quality._VALUE_KINDS`) is rewritten to `<value_kind:cpf_BR>` etc.
- **Selector strings**: `selector_attempted`, `fallback_selector`, `proposal.new_locator`,
  `last_failed_selector` are stored but pass through a CSS-value scrubber that replaces
  string literals inside `:has-text("…")`, `text=…`, `[value="…"]`, `[aria-label="…"]`
  with `<redacted>`. Attribute names + structural shape stay.
- **DOM excerpts** in L3 evidence: NOT written to spans.jsonl. Only `evidence_size_bytes`
  and `prompt_chars` are emitted; the full prompt + response stay in the recording's
  `healing/<step_id>/` directory, gitignored, and are deleted on `testforge publish`
  unless `--include-healing-evidence` is set.

A single `pii_scrub_level` recording-metadata field (`strict` default, `relaxed` for
tester opt-in) gates whether selector strings get scrubbed.

### 7.5 Sample events (3 to 5 concrete)

```json
{"name":"recording.step","trace_id":"a72e480e512f4e1b8caf26ef4c9d38ca","span_id":"b7576e6786a26714","parent_span_id":"c14de2640270c04a","start_time":"2026-06-25T19:31:02.812Z","end_time":"2026-06-25T19:31:02.871Z","duration_ms":59.2,"status":"ok","attributes":{"schema_version":1,"recording_id":"test-pos-hotfix","tester_hash":"b7576e6786a26714","framework.primary":"angular-material","framework.is_mat":true,"framework.is_cdk_overlay":false,"url_signature":"host=simuladorhabitacao.caixa.gov.br path=/calculadora","step_id":"e-0042","action":"fill","intent_text":"fill textbox \"Valor do imovel\"","value_kind":"currency_BR","value_len":9,"value_source":"fill_event","candidates_count":4,"primary_strategy":"label","primary_score":0.92,"blind_spots":[],"idle_before_ms":1300,"ax_snapshot_present":true}}
{"name":"resolve","trace_id":"d94c1d0ba395727aed5987af10413c4a","span_id":"68f739360730e3dc","parent_span_id":"step.fill-9821","start_time":"2026-06-25T19:31:02.815Z","end_time":"2026-06-25T19:31:02.819Z","duration_ms":4.1,"status":"ok","attributes":{"schema_version":1,"run_id":"r-2026-06-25-9821","framework.primary":"angular-material","url_signature":"host=simuladorhabitacao.caixa.gov.br path=/calculadora","intent_text":"fill textbox \"Valor do imovel\"","action":"fill","candidate_count":4,"level":"L0_cache","cache_source":"sqlite","strategy":"label","score":0.92,"candidate_index":-1,"elapsed_ms":4.1}}
{"name":"heal.l3.succeeded","trace_id":"d94c1d0ba395727aed5987af10413c4a","span_id":"f01a86b7c2391bcd","parent_span_id":"step.click-9822","start_time":"2026-06-25T19:31:08.401Z","end_time":"2026-06-25T19:31:09.812Z","duration_ms":1411.0,"status":"ok","attributes":{"schema_version":1,"run_id":"r-2026-06-25-9821","framework.primary":"angular-material","family":"FAM-01","model":"gpt-4.1-mini","tokens_prompt":1820,"tokens_completion":92,"tokens_total":1912,"usd_estimated":0.00095,"retries":1,"elapsed_ms":1411.0,"proposal.strategy":"has_text_fallback","proposal.confidence":0.85,"proposal.new_locator":"<redacted>","parse_status":"ok"}}
{"name":"step.failed","trace_id":"d94c1d0ba395727aed5987af10413c4a","span_id":"aa12be77c2390000","parent_span_id":"step.click-9823","start_time":"2026-06-25T19:31:11.000Z","end_time":"2026-06-25T19:31:11.001Z","duration_ms":0.5,"status":"error","attributes":{"schema_version":1,"run_id":"r-2026-06-25-9821","framework.primary":"primefaces","family":"FAM-01","taxonomy_id":"SEL-003","classifier_matched_by":"keyword","layers_attempted":["L0_miss","L1_test_id","L1_text","L2_selector_agent","L3"],"layer_outcomes":{"L0":"miss","L1":"all_failed","L2":"low_confidence","L3":"executed_but_failed"},"error.message":"widgetVar instavel"}}
{"name":"run.end","trace_id":"d94c1d0ba395727aed5987af10413c4a","span_id":"ffff86b7c2390000","parent_span_id":null,"start_time":"2026-06-25T19:31:00.000Z","end_time":"2026-06-25T19:31:14.500Z","duration_ms":14500.0,"status":"ok","attributes":{"schema_version":1,"run_id":"r-2026-06-25-9821","recording_id":"test-pos-hotfix","framework.primary":"angular-material","status":"fail","steps_total":12,"steps_passed":11,"steps_failed":1,"heals_l0":3,"heals_l1":2,"heals_l2":0,"heals_l3":1,"tokens_total":1912,"usd_estimated":0.00095,"trace_zip_path":"recordings/test-pos-hotfix/trace.zip","play_number":4}}
```

---

## 8. Minimum Dashboards (3–5 charts on `dashboard.html`)

Today `metrics/dashboard.py` renders 4 tiles for resolve-only spans. Extend to the
following minimum set:

| # | Chart | Type | Aggregation | Decision it informs |
|---|---|---|---|---|
| D1 | **Playback pass rate over plays** | Line chart, x = `play_number`, y = `K1`, one line per `framework.primary` | `run.end` spans grouped by recording_id and play_number | Are tests still green at play #5? Per framework? |
| D2 | **Heal tier distribution** | Stacked bar, x = `framework.primary`, y = % of healed steps at L0/L1/L2/L3 | `heal.*.succeeded` spans grouped by framework | Where is each framework escalating? |
| D3 | **LLM cost & latency** | Dual-axis bar+line, x = day, y1 = `usd_estimated` sum, y2 = `tokens_total` p95 | `heal.l3.succeeded` aggregated daily | Cost trajectory, abort if blowing budget |
| D4 | **Failure heatmap** | Heatmap, rows = FAM-01…FAM-11, cols = framework.primary, cells = `step.failed` count | `step.failed` spans pivot | Routing: where to build the next L2 agent |
| D5 | **Recording health vs run health** | Scatter, x = K5 recording_health_score at record time, y = K1 pass rate of that recording's runs | join `recording.stop` + `run.end` | Does bad capture predict bad playback? Confirms or kills K5 weights |

Bonus tile (cheap): **Determinism pair table** — list of `(workflow_id, recordings_paired,
intent_overlap_jaccard, locator_fingerprint_jaccard)`, sortable. Shows recorder
non-determinism without a graph.

All charts are Chart.js loaded from a CDN (already done in `dashboard.py`); JSONL is read
on `testforge dashboard`. No backend, no DB beyond the existing SQLite intent catalog.

---

## 9. Gaps in Current Capture (verified by reading code)

What we have today, by reading `metrics/telemetry.py`, `runtime/resolver.py`,
`runtime/step.py`, and `diagnostic/telemetry_store.py`:

- **Present and OTel-shaped**: `resolve` (good — has `level`, `strategy`, `score`,
  `candidate_index`, `elapsed_ms`), `step.click`, `step.fill`, `step.select` (very thin —
  only `intent_text`), `diagnostic.step`, `diagnostic.replay`.
- **Missing entirely**: every `heal.*` event, `step.failed`, `run.start`/`run.end`,
  `recording.start`/`recording.stop`, `assert.failed`, `compile.*`.
- **Present but incomplete**: `resolve` lacks `framework.primary` and `cache_source`;
  `step.*` lack `value_kind`, `framework.primary`, `target_role`.

Concrete code paths to change:

| Gap | Code path | Change |
|---|---|---|
| No `run.start` / `run.end` envelope | `runtime/step.py` has no run-level wrapper | Add `runtime/run.py::with_run(recording_id)` context manager that opens a parent span, generates `run_id`, computes `play_number` by scanning prior `run.end` spans for the same recording_id |
| No `heal.l0/l1/l2/l3` spans | `healing/curator.py::_try_layer0_catalog/_try_layer1_candidates/_try_layer2_agents/_run_healing_cycle` | Wrap each method body in `tracer.start_span("heal.l<N>.attempted")`, emit `.succeeded` on return-with-pass, set `status=error` on miss |
| LLM token cost not captured | `healing/llm_healer.py::LLMHealer.heal()` and `llm_client.chat()` | `chat()` must return `(text, usage_dict)`; healer span records `tokens_prompt`/`tokens_completion`. Need a price-per-model dict (single config file, e.g. `metrics/llm_prices.yaml`) for `usd_estimated` |
| No `framework.primary` on runtime spans | `runtime/step.py`, `runtime/resolver.py` | Cache framework once per run from `recordings/<id>/diagnostic/session.json::framework_detection.primary` (or null if missing); attach to every span in that trace |
| No `step.failed` event | runtime exception path in `step.click/fill/select/assert_text` and `runner/fallback_runner.py` | Catch `StepExecutionError`, classify via `FailureClassifier`, emit `step.failed` before re-raising |
| L0 cache hits don't distinguish mem vs sqlite | `runtime/resolver.py::_resolve_impl` already logs to logger but doesn't tag the span | Add `span.set_attribute("cache_source", "mem"|"sqlite")` in both hit branches |
| Recording-level rollup not persisted | `recorder/recorder_controller.py` writes `session.json` for diagnostic mode only | Emit `recording.start`/`recording.stop` spans always (not just in diagnostic mode), so non-diagnostic recordings are also visible on the dashboard |
| Playback pass rate K1 has no source | nothing today | `run.end` carries `status` and `play_number`; dashboard computes K1 from the time-series |
| Determinism `workflow_id` missing | no field today | Add `--workflow-id` flag to `testforge record`; persist in `recording_metadata.json`; carry on every span via `recording.start` |
| Network postback detection at record time | `raw_events.jsonl` has network rows from CDP but no rollup | Add a small post-process in `recording_auditor.py` that counts API POSTs between successive user actions, emit as `recording.stop.network_postback_detected_rate` |
| `value_kind` for runtime fills | `runtime/step.py::fill` only has the raw value | Use `capture_quality.detect_value_kind(value)` before attaching to span; never log the value itself |
| Existing `diagnostic.replay` shape close to but not identical to `recording.replay_probe` | `diagnostic/telemetry_store.py` | Rename in span emission, keep JSONL filename for back-compat (`replay_check.jsonl`) |
| Schema versioning | none today | Add `schema_version` constant in `metrics/telemetry.py`, attach to every span via Tracer wrapper |
| PII scrubber | none today | New `metrics/redact.py` module called from `Tracer._write()`; reuses regexes from `capture_quality._VALUE_KINDS` |

All changes are **additive** — old JSONL still parses. The dashboard reads new fields if
present, falls back gracefully.

---

## 10. External Research — what to steal, what to skip

References: `.planning/research-modern-healing-tools.md`, OpenTelemetry browser-test
semconv (draft), Datadog Synthetics docs, Playwright Trace Viewer.

| Source | What to steal | What to skip |
|---|---|---|
| **OTel `semconv` browser/test** (draft) | The flat `attributes` namespace + dot-separated keys (`http.url`, `db.system`). We already match this. Stay close to it so a future OTel exporter is a single adapter. | Distributed-tracing-style propagation across browser ↔ test runner. We're single-process. |
| **Playwright Trace Viewer** | `trace.zip` per run pointer (`trace_zip_path` on `run.end`) so a human can scrub failed runs in `trace.playwright.dev`. Already on our v2 roadmap. | Storing traces for every run — too big at pilot scale. Keep on failures + sample 1/N pass. |
| **mabl auto-heal** | 30-attribute snapshot per element — copy into `LocatorCandidate` (research doc §H.4 already flags this gap). Capture the snapshot at *record* time, log only the diff at heal time. | Closed-source healing dashboard. Their UI is overkill for us. |
| **Testim** | Per-locator stability score 0–100% surfaced in the readiness report. We already have `score` per `LocatorCandidate`; promote to UI. | Cross-customer trained weights — we have no scale for that. |
| **Healenium** | Persistent heal history with confidence, reviewable by humans. Our `healing_catalog.jsonl` is already this. SQLite extension (`sqlite_intent_catalog`) maps directly to Healenium's Postgres schema, simpler. | Web dashboard at `healenium-web` requires a hosted backend. Use our static HTML. |
| **Stagehand** | `intent_text` as cache key — already adopted. Token-usage logging on every LLM call — copy verbatim into `heal.l3.succeeded`. | Hosted Browserbase backend. We stay on-disk. |
| **browser-use** | Super-selector tuple (research §F.2). Telemetry-wise: their per-step CDP call counts and DOM-snapshot sizes — useful KPI for understanding overhead, but not for healing decisions. | Reasoning every step (re-LLM-ing). |
| **Playwright MCP** | YAML AX-tree snapshot as the L3 prompt input — already on roadmap, telemetry-wise just log `ax_snapshot_size_bytes` and `prompt_chars` (already in §7.3). | MCP-specific `ref=eN` IDs — session-scoped, not durable. |
| **Datadog Synthetics** | Test-run grouping by `(test_id, deploy_id)`, percentile latency over time. Adopt the *naming convention* `run.end.status` and `step.assert.outcome` if it converges to anything in semconv. | Their hosted backend, RUM integration — overkill. |
| **arXiv 2603.20358 Zero-Cost Self-Healing** | "Re-extract only the broken selector" — log `heal.l3.attempted.evidence_size_bytes` so we can later measure how much we send vs what they need (their answer is "much less"). | The CV-only fallback path — not relevant to our scope. |

**Net steal list for telemetry**:
1. Token usage on every LLM call (Stagehand).
2. Per-locator stability score in readiness report (Testim).
3. Trace.zip pointer on failed runs (Playwright).
4. Intent-text cache key on every resolve (Stagehand, already done).
5. Heal history with confidence on disk (Healenium, already done).
6. `framework.primary` on every span (TestForge-original — none of these tools handle
   multi-framework pages well).

**Net skip list**:
- Hosted backends (Mabl, Testim, Datadog, Browserbase).
- CV / vision telemetry (Functionize, Skyvern) — no L4 yet.
- Per-session OTel trace context propagation — single-process, no network hop.

---

## Appendix A. Acting on the data

This plan is only useful if we can react. For each KPI we commit to:

- **K1 falls below 0.90 for any framework** → file a phase under MIGRATION-ARCHITECTURE.
- **K2 below 0.80** → healing is theatre; the layer with the highest invocation-to-success
  ratio gets a sprint.
- **K3 L3 share > 0.20** → invest in L0/L1/L2 for the dominant framework (per D4).
- **K4 above $0.05/run** → cap retries, reduce evidence size, or fall back to MockLLMHealer
  on low-confidence families.
- **K5 below 0.85** → recorder bug — fix in `recorder_controller.py` or
  `capture_quality.py` rules.
- **K6 below 0.75** → recorder non-deterministic — likely candidate scoring instability;
  pin the locator extractor's tie-break order.
- **K7 hot family > 0.05** → spec a specialist agent.

If a KPI moves and *nothing* changes, the KPI is wrong. Cut it.

## Appendix B. Implementation order (cheapest first)

1. **Day 1 — additive `framework.primary` + `schema_version` + `cache_source` on existing spans.**
   One-file edit in `telemetry.py` + 3 attribute pushes in `runtime/resolver.py` + `runtime/step.py`. Zero new spans.
2. **Day 1 — `step.failed` + `run.start`/`run.end`.** Six attribute writes. Enables K1.
3. **Day 2 — wrap `CuradorAutomatico` in `heal.l*.attempted/succeeded` spans.** Six method
   bodies, mechanical. Enables K2, K3, D2.
4. **Day 2 — token capture in `llm_client.chat()`.** Returns `(text, usage)`. Enables K4, D3.
5. **Day 3 — `metrics/redact.py` + apply in `Tracer._write()`.** Privacy gate before
   distributing build to pilot.
6. **Day 3 — `workflow_id` CLI flag + determinism computation in `pilot-report`.** Enables K6.
7. **Day 4 — extend `metrics/dashboard.py` with D1, D2, D4, D5.** D3 lands once K4 spans exist.

Total: ~4 days, no new dependencies, no new file formats.
