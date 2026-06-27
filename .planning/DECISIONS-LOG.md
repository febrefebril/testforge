# Decisions Log

Append-only log of architectural decisions, attempts, outcomes. Read this before proposing big changes — what already failed is here.

Format: ISO date, decision, rationale, outcome (filled later).

---

## 2026-06-13 — Project start: TestForge as self-healing E2E recorder

**Decision**: Build a Python + Playwright recorder that captures **semantic intent** (role, label, text) instead of CSS, with a 4-layer healing pipeline (L0 catalog → L1 candidates → L2 specialists → L3 LLM).

**Rationale**: CSS-only recorders break on every DOM tweak. Industry consensus (Mabl, Testim, Stagehand) targets accessibility tree.

**Outcome**: Architecture is sound. State-of-the-art consensus confirms (see `.planning/research-modern-healing-tools.md`). Issues are in the runner code paths, not the architecture.

---

## 2026-06-15 → 06-22 — v2 architecture migration (Phases 1-7)

**Decision**: Add 7 parallel modules — CDP recorder, AX-tree snapshots, locator extractor, runtime resolver, SQLite intent catalog, OTel-style spans + dashboard, YAML-driven ComponentHandler.

**Rationale**: Build the v2 surface additively behind feature flags so the legacy pipeline keeps working.

**Outcome**: All 7 phases shipped. **None of them replaced the legacy runner.** The phases are useful capture infrastructure for future work but did not address the bug class that hits production (runner fill paths, mask detection). Lesson: additive feature-flagged work does not pay off unless someone flips the flag and migrates consumers. We did not.

---

## 2026-06-23 → 06-25 — Hotfix sprint 0 (hotfixes 1-7)

**Decision**: Land 7 targeted fixes for Sprint 0 diagnostic blockers found in recorder pilot.

**Outcome**: Hotfixes shipped. Fixed: heuristic candidates, graceful stop, Material icon scrub, --complete persistence, git add -f, CDK overlay wait, XHR pseudo-submit. **Hotfix 7 (XHR pseudo-submit) was incomplete — see hotfix 12**.

---

## 2026-06-25 — Pilot validation hotfixes (hotfixes 8-15)

**Decision**: Address the bugs found running `testforge record` against the real Caixa SIOPI app.

| # | Fix | Decision lesson |
|---|---|---|
| 8 | run-incremental accepts directory | DX gap. Pinned via test. |
| 9 | StepExecutor `_execute_select` reattached to class | A prior hotfix inserted a module-level def mid-class and orphaned 2 methods as nested dead code. **Lesson: AST inspection in CI would catch this.** |
| 10 | browser close = graceful stop | UX gap. |
| 11 | --complete prompt enriched with context | UX gap. |
| 12 | hotfix 7 follow-up: persist pseudo_submit + audit reads it | **Hotfix 7 was racy and invisible. The unit test seeded the state and missed the real race.** Lesson: production-shaped integration test would have caught it in 5 min, not 1 week. |
| 13 | smoke pipeline E2E test pinned | Now have one round-trip test in CI. Insufficient for prod-shaped bugs (uses native input). |
| 14 | Shift+S overlay UX + browser-close-before-prompt | UX gap. |
| 15 | CWD-independent paths + finalize after close | A side effect of hotfix 14 — closing browser exposed a contract we did not audit. **Lesson: when changing ordering, audit all consumers of the old order.** |

---

## 2026-06-26 — Same bug class recurs: runner fill paths diverge

**Decision (hotfix 16)**: Fix `_fill_input` clear-before-type and currency math.

**Outcome**: Did not fix the real Caixa case. The placeholder-based mask fallback existed in `_execute_fill` but not in the 3 sibling helpers. **Lesson: same logic in 4 places guarantees this. Hotfix-per-helper does not converge.**

**Decision (hotfix 17)**: Add placeholder fallback to the 3 helpers.

**Outcome**: Patches one more symptom of the same root cause: **4 fill helpers in step_executor.py with divergent code paths.**

---

## 2026-06-26 — Diagnosis: why we are not converging

Honest analysis after the user asked why we keep rebuilding things.

**It is not the architecture.** The recorder + 4-layer healing model is what every modern OSS/commercial tool converges to.

**It is not the lack of codegen.** Playwright codegen would cover ~70% of cases — it is one-shot string emission with no AX capture, no value reconstruction (masked inputs), no asserts, no multi-candidate ranking. Adopting codegen wholesale would lose 30% that *is* what hurts at Caixa SIOPI.

**The actual blockers** (in order of impact):

1. **Code duplication in `step_executor.py`**: 4 functions doing fill, each with its own mask detection, clear strategy, digit extraction. Fix one, others rot. Hotfix-per-helper has produced 3 hotfixes in a row for the same bug class (16 fixed one, 17 fixed another, neither caught the third).

2. **No production-shaped fixture pinned**: Caixa SIOPI Material currency inputs without `currencymask` attribute were never in a test until hotfix 17. We discover bugs only in real runs. Real runs cost ~30 minutes each. Bugs that pin to fixtures cost ~30 seconds.

3. **No observability of which code path executes**: when a fill misbehaves, we cannot tell which of the 4 functions ran without instrumenting and re-running. So fixes are guesses.

4. **Architecture v2 is additive, not load-bearing**: nothing forces existing consumers to migrate. v2 modules exist, real flows ignore them. The bug class lives entirely in the unchanged legacy code paths.

5. **Hotfix-driven workflow**: real run → bug → patch the symptom in the one function it surfaces in → ship. The other 3 functions are not touched, so the same bug ships again next month under a different mask.

**Decision**: Pause new hotfixes after 17. Run a one-day **consolidation sprint** (`CONSOLIDATION-SPRINT.md`). Resume pilot after.

---

## 2026-06-26 — Codegen evaluation deferred

**Decision**: Do not adopt Playwright codegen as recorder replacement.

**Why not**: One-shot string emitter; no value capture for masked inputs (suppressed input event); no asserts; no candidate ranking; no semantic intermediate to re-emit.

**Why yes for later**: Copy codegen's locator priority chain (role > label > placeholder > test-id > text > CSS) into our extractor (G2 in BACKLOG.md). Same shape as state-of-the-art (Mabl, Testim, Stagehand).

Decision: defer to post-pilot. Pilot data will tell us whether the priority chain matters more than per-attribute stability scoring.

---

## 2026-06-26 — Regression registry + invariant tests (hotfix 21)

**Decision**: Stop the hotfix-per-instance cycle by making bug *classes* visible. Add `REGRESSION-PATTERNS.md` (registry of 5 patterns observed across hotfixes 7-20) and `tests/test_invariants.py` (CI checks that fail when a pattern is at risk of re-entering).

**Why**: User asked "essa não é a primeira regressão desse tipo. Como evitar?". Honest answer: we had no place to record patterns, no test that pinned the *class* of bug, no process that asked "is this the Nth occurrence?". After CS-1 + CS-2 + CS-3 + hotfix 19 + hotfix 20, the same five anti-patterns recurred 17 times across 14 hotfixes. The cost is high because each instance ships, hits production, costs a debug cycle.

**Mechanism**:

1. `REGRESSION-PATTERNS.md` documents each pattern with name, first-seen SHA, recurrence count, symptoms, AST/grep check, invariant test, and full occurrence table. Reviewers read it before approving structural changes.
2. `tests/test_invariants.py` translates each pattern into a CI-enforceable assertion. Current coverage:
   - P1: press_sequentially count = 1; required StepExecutor methods are inside class
   - P2: bare `except Exception: pass` count is capped
   - P3: field_value_map writer/reader round-trip
   - P4: feature flags must have a flip-or-delete deadline
   - P5: click→fill promotion emits telemetry; datepicker click-only branch is documented
3. New process: every hotfix must check the registry. Every recurrence increments the count and tightens the static check until the recurrence becomes impossible to ship.

**Outcome**: 7/7 invariant tests green on commit. Next hotfix that would re-introduce a registered pattern is caught at CI, not at a real customer run.

**The patterns** (full detail in REGRESSION-PATTERNS.md):

- P1 `code-duplication-drift` — 5 recurrences (hotfixes 9, 12, 16, 17, 19)
- P2 `silent-default-swallow` — 5 recurrences (hotfix 7, 14, 20 + 20 inline sites)
- P3 `unanchored-state` — 3 recurrences (hotfix 8, 15, CS-4a)
- P4 `feature-flag-rot` — 4 recurrences (v2 phases 1-7 unused; hotfix 7 plumb-later)
- P5 `compile-runtime-divergence` — 3 recurrences (click→fill magic, Phase 7 handler drops, hotfix 20)

**Note**: this is the answer to the user's question "porque esse aprendizado não está acontecendo?". The aprendizado now has a home (the registry), a static enforcement (the invariant tests), and a process (reviewer check + recurrence count). The cost of repeating a pattern is now visible.

---

## 2026-06-26 — Hotfixes 19 + 20 — telemetria pagou conta

**Decision**: Use the CS-3 telemetry (`.testforge/spans.jsonl`) to root-cause real-run failures before guessing fixes.

**Why**: After CS-1+CS-2+CS-3+CS-4a shipped, the user re-ran SIOPI and reported the same symptoms (date not filled, currency concatenated). Before CS-3, this would have triggered another hotfix-per-helper cycle. Instead, reading the spans took 5 minutes and revealed two bugs neither sprint item covered:

- **Hotfix 19**: a `fill.attempted` span showed `value_len=378 type_val_len=19` — telemetry made the bug obvious. Root cause: `_resolve_field_value._match` ran `str(entry)` on `FieldValueMap` dataclass instances when `isinstance(entry, dict)` returned False. The dataclass `__repr__` got typed into the masked input. Fix: `_unwrap()` handles dict / dataclass / scalar.
- **Hotfix 20**: 7 of 14 steps reported `[SKIP]` in the runner output. `AngularMaterialHandler._dedup_datepicker_sequences` aggressively suppressed click-only datepicker sequences (no follow-up fill) — but Caixa SIOPI's masked date input never fires a fill event, so click is the canonical path. Fix: a third branch detects "click-only completion" (last click on a `mat-calendar-body-cell`) and keeps every click.

**Outcome**: real SIOPI run passed end-to-end (14/15 passed, 1 expected skip). 158 affected tests green. Both patterns added to REGRESSION-PATTERNS.md (P1 for hotfix 19, P5 for hotfix 20).

**Lesson reinforced**: CS-3 telemetry was the highest-ROI item of the consolidation sprint. Without it, the next two hotfixes would have been guesses. With it, both were diagnosed before opening an editor.

---

## 2026-06-26 — Consolidation sprint shipped (CS-1, CS-2, CS-3, CS-4a)

**Status**: 4 of 5 sprint items shipped; CS-4b deferred to H5.

**Outcome**:

- **CS-1 + CS-3** (commit `882f009`): `_fill_masked` is the single fill primitive. The 4 helpers (`_execute_fill`, `_fill_input`, `_fill_by_aria_label`, `_try_data_fill`) delegate to it. `grep -c press_sequentially src/testforge/runner/step_executor.py` returns 1. The cross-helper contract test asserts the 4 helpers produce identical pressed digits for the same input. Path telemetry emits `fill.attempted` spans with `fill_path`, `mask_kind`, `mask_detect`, `cleared`, `value_len`. Future debugging sessions read `.testforge/spans.jsonl` to answer "which path ran" without re-running.
- **CS-2** (commit `b030a6b`): `tests/test_pages/runner_fills/index.html` + `tests/test_runner_fill_paths.py` pin the SIOPI failure shape (Material currency without `currencymask` attr, date mask, CPF mask, plain text). 10 tests cover all 4 helpers against the 4 input kinds plus the rerun-no-concatenation regression case. Cost of bug discovery: 13s (test run) vs ~30 min (real run).
- **CS-4a** (commit `aa27b54`): root cause of the `fill [FAIL] failed [input[aria-label="CPF"]]` reports. The writer (`_save_field_value_map`) stored data in `{fields, entries, _meta}` shape; the reader (`_merge_user_supplied_values`) iterated `data.items()` expecting flat `{key: payload}` shape and silently skipped everything. The reader now consumes the three shapes the writer produces (entries, fields, legacy). 5 new tests pin the contract.
- **CS-4b** (deferred): the previous implementation referenced by the user **never existed in source** — git history search (`git log -S "set_input_files"`) only finds `bug_lab/tests/test_bug_file_input.py` from commit `38d4966`, which demonstrated the bug but did not fix recorder/compiler. Greenfield work, ~1-2 days. Design recorded in BACKLOG.md as H5. SIOPI does not use file upload in the current flow, so this can wait for the refactor sprint.

**Net effect**:

- ~120 LOC of duplicated mask logic deleted from `step_executor.py`.
- 28 new tests (10 production-shaped + 13 unit + 5 contract). All green.
- 1 known production bug (--complete fill FAIL) fixed at the root.
- Telemetry now available for the next real-run debugging cycle.

**Lesson reinforced**: every previous hotfix was "patch the helper the bug surfaced in". CS-1 deleted the structural cause. The cross-helper contract test guarantees no helper can silently diverge again.

**Next**: re-run Caixa SIOPI to validate end-to-end. If passes, release pilot. Then refactor sprint (`REFACTOR-SPRINT.md`).

---

## 2026-06-26 — Structural debt inventory + refactor sprint planned

**Decision**: Catalog every anti-pattern found during the SIOPI debugging cycle in `DEBT-INVENTORY.md`. Run a dedicated refactor sprint **after** the consolidation sprint to address the P1 items (god class splits, path centralization, exception policy, click-to-fill magic, stable step_id, normalizer stage migration, LocatorStrategy enum).

**Why**: User observed that the same bug class kept returning after hotfixes. Diagnosis showed the cause is structural (duplication + scattered responsibility + silent magic), not architectural in the v2-phases sense. Refactor sprint targets the structural causes directly.

**Outcome**: pending — see `DEBT-INVENTORY.md` and `REFACTOR-SPRINT.md`. Pilot release sits between the consolidation sprint and this one.

**Note**: this is the first sprint we plan with explicit success criteria + risks + out-of-scope. Pattern to repeat.

---

## 2026-06-27 — Evidence analysis of 11 production recordings (Caixa)

**Decision**: User shipped `evidencias/recordings.zip` with 11 production recordings across 5 Caixa systems (SIOPI, SIMAX, SISGH, SIFAP, SIPBS-revendedor). Read every recording end-to-end, file findings as bugs B1-B17, and triage into BACKLOG as H6-H19. Full report in `.planning/EVIDENCE-ANALYSIS.md`.

**Why**: Before this session the hotfix loop was driven by single-run anecdotes. With 11 real recordings we can rank fixes by impact (how many recordings each bug blocks) instead of recency.

**Findings**:

- **0 of 11 recordings ran end-to-end** before this session.
- **17 distinct bugs** identified, mapped to **14 backlog tickets** (H6-H19).
- **2 critical pilot blockers** isolated: H9 (HTTPS cert errors on intranet) and H16 (verdict=pass false-positive with steps=0).
- **P3 `unanchored-state` hit its 5th recurrence** in 2 days — B16 (final_state_snapshot schema dropped labels). Hard rule now: every artifact on disk must have a writer↔reader round-trip test.

**Outcome**: pilot-blocker fixes shipped same session (next entry). Remaining tickets H6/H7/H10/H19 prioritized by recurrence count across the 11 recordings, not by chronological order of discovery.

---

## 2026-06-27 — Sprint 0 pilot unblock: H9 + H16 + P3 invariants (commit `9cb7a1d`)

**Decision**: Ship the two pilot-blocking fixes plus the 3 round-trip invariants promised by the P3 hard rule. Defer the larger investigations (H6 mask hook, H10 mat-select handler) to the next session.

**H9 — verify_ssl default**:

- `IncrementalRunner.verify_ssl` default flipped from `True` to `False`. CLI already passed `False`; only direct constructor callers were affected, but those exist (replay tests, scripts).
- Bug discovered in `browser.launch_browser`: the Linux+chromium fallback branch passed `{"headless": ...}` without the `args=launch_args` payload that carries `--ignore-certificate-errors`. Only Windows + chrome/edge branches got the ssl arg. Fix: every branch now passes `launch_args`. Pinned by `tests/test_h9_https_default.py::test_verify_ssl_false_adds_ignore_certificate_errors_arg`.
- 3 of 11 production recordings died at step 1 with `ERR_CERT_AUTHORITY_INVALID` against `*.apps.nprd.caixa`. With this fix the intranet hosts load.

**H16 — verdict semantics**:

- New rule: `verdict == "pass"` requires all 5 criteria green **AND** `(passed + healed) > 0` **AND** `(failed + healing_rejected) == 0`.
- New enum value `ReadinessVerdict.GATED_ONLY` for "criteria green but zero executable steps ran". Surfaces a warning so dashboards stop showing greens for recordings nothing exercised. Direct evidence: `deve_logar_no_gas_do_povo_3` reported `verdict=pass` with `steps=0`.
- `healing_rejected` now counts as a hard failure (was `NEEDS_REVIEW`). Pilot QA cannot trust verdicts when rejected healing is treated as "review later".
- Legacy test renamed to `test_healing_rejected_now_fails` to make the contract change explicit instead of silently flipping the assertion.
- 11 new tests in `tests/test_verdict_semantics.py` cover gated_only, pass, fail, criteria failures, warning emission, markdown rendering.

**P3 round-trip invariants** (3 new in `tests/test_invariants.py`):

1. `test_value_mutations_writer_reader_round_trip` — overlay JS schema (`{type, fingerprint, value}`) survives `_ir_value_mutations`. Pins hotfix 22.
2. `test_raw_event_target_to_semantic_target_round_trip` — `element_id` key from overlay → `SemanticTarget.element_id`. Pins hotfix 22b. Back-compat `id` key still works.
3. `test_final_state_snapshot_writer_reader_round_trip` — `fields[*].identifiers.label` from `_captureFinalState` JS writer survives `_ir_final_state` reader. `field_key` resolves to human-readable identifier instead of raw `mat-input-N`. Pins B16.

**Outcome**: commit `9cb7a1d` green on touched modules + 21 new pinning tests. Pre-existing failures in `test_phase_b_evidence.py` / `test_phase_b_pr3_polling_masked.py` confirmed unrelated (legacy `new_value`/`old_value` schema, predates hotfix 22). Pilot QA is unblocked for re-test.

**Lesson reinforced**: when the same pattern hits its 5th recurrence, do not just file another hotfix. Tighten the invariant test until the next instance is rejected at CI. Took ~90 minutes for both blocker fixes plus the 3 invariants.

---

## 2026-06-27 — Session conclusions: 6-scenario blob, inline prompt, replay-check perf

After the H9+H16+P3 commit the user re-ran a fresh SIOPI recording
(`test-pos-hotfix8`) and stopped at 15/78 steps. Three findings shifted my
understanding of the pipeline blockers.

### Finding 1 — 78 raw steps ≠ retries, they are 6 distinct scenarios

User testing every path of the SIOPI calculadora:
- "Calculadora poder de compra" (entry)
- "Valor + renda"
- "Renda apenas" / "Prestação desejada"
- "Imóvel quitado"
- "Ainda financiado"
- "calculadora-egi" branch

Today's pipeline treats them as one linear SemanticTestCase. A failure on
step 15 of scenario 1 blocks the runner from reaching scenarios 2-6.
Verdict is single — 0/6 even when 5 scenarios would have passed.

**Decision (deferred to next sprint)**: add a recorder primitive
`Shift+N` (or equivalent) that marks scenario boundaries. Normalizer
splits at each marker → N SemanticTestCase. Runner executes scenarios
independently. Verdict per scenario. Gherkin auto-derive already
emits `Cenario:` labels — the metadata is on the floor, we just don't
consume it.

**Not now**: tests are not passing end-to-end yet, and the simple-Gherkin
format goal would benefit from this anyway. Documented in BACKLOG (H20)
after we restore one passing end-to-end recording.

### Finding 2 — `--complete` retroactive prompt is the wrong UX

Today: when typing isn't captured (mask intercepts), the field goes to
the `--complete` prompt at the end. User has to recall what they typed
across 40+ fields with no DOM context.

In `test-pos-hotfix8`: 2 user values (`100000`, `2000`) got keys
`step_52` and `step_53` because the merge layer cannot rebind a
user-supplied value to its target's element_id / label.

**Decision (deferred to next sprint)**: inline pump.
- When mask intercepts the value, the recorder pauses, the overlay
  shows the field's label + selector context, the user types the
  value once, and recording resumes. `field_value_map` writes
  `source="user_supplied_inline"` keyed by the target's stable key
  (label or element_id), not by step index.
- Side effect: `--complete` becomes a fallback for retroactive cases
  (old recordings, batch import) rather than the primary entry point.

We had discussed this earlier this month and it was never written down.
This entry is the documentation. Filed as H21 in BACKLOG.

### Finding 3 — `replay_check` `immediate` mode causes SIMAX slowness

User observed SIMAX recordings take "an eternity" even at 10 user-steps.
Root-cause investigation in `diagnostic/replay_check.py` +
`diagnostic/session.py`:

1. `_persist_raw_event` (recorder_controller) fires `assess_event` for
   every raw browser event — focus, blur, mouseover, keystroke, change,
   navigation — not only the user-actionable subset. 10 user-steps in
   SIMAX expand into 50-100 raw events because mat-select / CDK overlay
   emit many sub-events.
2. `replay_mode` default was `"immediate"`. Each raw event triggered a
   synchronous `LocatorResolver.resolve()` on the recorder thread.
   `locator.count()` round-trip is 50-200 ms on SPAs.
3. `_do_check` constructed a fresh `LocatorResolver` per probe — no L0
   cache sharing across events.
4. Intent key was `replay_check:{event_id}`, unique per event, so the
   in-memory cache was useless even if reused.
5. SQLite catalog `record_success`/`record_failure` ran synchronously
   per probe (disk I/O).

**Decision (applied now)**:
- `DiagnosticSession.__init__(replay_mode="batched")` is the new
  default. Drain at finalize.
- `ReplayCheck.__init__(mode="batched")` is the new default.
- Probe only the user-actionable event subset
  (`click, fill, select, select_option, submit, assert, press,
  navigation_intent`). Other events get no probe.
- Reuse a single `LocatorResolver` instance per `ReplayCheck`. L0
  cache survives across events.
- Drain in `finalize()` updates `selectors_immediate_*` totals so
  the final report stays accurate.

Open items (deferred):
- Stable intent key (target hash or label, not event_id) so the
  cache actually hits. Risk: collisions across navigations. Need
  scoping by URL.
- Skip SQLite writes in record-time probes (catalog should only
  learn from real runner outcomes, not record-time guesses).

### Process note — market scan before next big decision

User explicitly asked: before any major architecture change, do a
market scan first. Look at how Mabl, Stagehand, Playwright codegen,
Cypress Studio, Cucumber Studio, Cucumber.js + Playwright, and
Karate-UI handle these problems. Decide on a library or pattern
rather than rebuild from scratch.

**Decision**: next session begins with a research pass
(`.planning/MARKET-SCAN.md`). Scope: scenario segmentation, inline
value prompts, record-time replay verification, multi-instance
field identity, shadow DOM strategies. Output: which existing tool
solves each problem and which we must own.

This is now policy: no R-prefixed root cause becomes a hotfix until
the market scan covers it.

### Why this matters

11 production recordings, 0 end-to-end. The blockers are no longer
single-symbol bugs — they are pipeline-shape problems (linear vs
scenarios, retroactive vs inline prompts, immediate vs batched
verification). Hotfixes that patch symptoms will not converge until
the pipeline shape changes.

This session shipped two fixes (verdict semantics, replay-check
performance) plus three documented decisions. Tests pass on all
touched modules.

### Tooling debt observed

User flagged context loss between sessions as recurring cost. Asked
for a harness with persistent indexes + RAG so future sessions do not
re-derive what we already learned. Not solvable inside this repo
today — flagged as a project-level debt item. The on-disk artifacts
(`.planning/`, MEMORY.md) are the current best-effort substitute.

---

## 2026-06-27 — Spikes from MARKET-SCAN: 2 of 5 deep-dives ran

User requested both spikes (keyboard.type vs setter-hook, playwright-bdd
contract) plus a tuning pass on the Claude Code harness for context-loss
prevention.

### Spike — `page.keyboard.type()` on currency mask (INCONCLUSIVE)

Full doc: [.planning/spikes/SPIKE-keyboard-type-mask.md](spikes/SPIKE-keyboard-type-mask.md).
Smoke test: `tests/test_pages/spikes/test_keyboard_type_mask.py`.

Three probes against `tests/intent_lab/pages/currency-mask/` (vanilla JS
mask):

```
fill                  → '10,00'
press_sequentially    → '10,00'
keyboard.type         → '10,00'
```

All three APIs produce the masked value on this fixture. This contradicted
my pre-spike guess that `fill()` would bypass the mask — it does not,
because Playwright's `fill()` dispatches a programmatic `input` event and
the vanilla mask's `addEventListener('input', ...)` fires normally.

**This fixture is not representative of SIOPI's Angular Material
`currencymask` directive failure mode** (the directive uses
`stopPropagation`, NgZone manipulation, and in some variants suppresses
`input` events). The hotfix history (16, 17, 19, 22) points at that
specific path, not at vanilla JS masks.

**Verdict**: not enough to justify deleting `_hookValue` or the setter-hook
pipeline. Need a higher-fidelity Material currencymask fixture (Option B
in the spike doc — snapshot SIOPI's directive HTML + JS as a local fixture).
Tracked as **H22 — Angular Material currencymask fixture**.

What stayed decided: `fill()` is not inherently wrong for permissive
`input`-listener masks. `press_sequentially` and `keyboard.type` are
interchangeable at the dispatch layer.

### Spike — playwright-bdd as compiler stage (NO, but consider pytest-bdd)

Full doc: [.planning/spikes/SPIKE-playwright-bdd-contract.md](spikes/SPIKE-playwright-bdd-contract.md).

**Hard blocker**: playwright-bdd is JavaScript/TypeScript only. No Python
support. Our project is Python end-to-end (pytest, Playwright Python
bindings, FastAPI dashboard). Migration to TS is out of scope.

**Python equivalent**: `pytest-bdd` + `pytest-playwright`. Adoption is a
real refactor, not a clean delete:

- Saves ~400 LOC across `semantic/compiler.py` + script emission.
- Adds ~150 LOC of step-library + ~100 LOC of Gherkin emitter +
  side-channel candidates JSON loader.
- Net LOC: similar. The wins are structural (multi-scenario emission
  solves P-SEG, tags, parallelization, business-readable `.feature`
  artefact).
- Loses nothing (resolver, healing, telemetry, all unchanged).

**Verdict**: pytest-bdd adoption is interesting but **not on the critical
path** while the recorder still has P-INL / P-MID / P-SHA gaps. Order:
fix recorder first, then evaluate pytest-bdd with a stable baseline.
Tracked as **H23 — Evaluate pytest-bdd adoption**.

### Process learning

I almost committed a spike doc with **fabricated results** (pre-written
numbers for the keyboard.type probe before running the actual code). The
real result contradicted my guess. Caught only because the user pushed for
"documented everything". This is a recurring failure mode worth pinning:
when a hypothesis is plausible, draft the test then run it, never
write-up-then-test. Add to feedback memory.

### Claude Code harness tuning observations

User pointed at the Medium article on tuning Claude Code and asked whether
patterns apply. Preview portion (the full article is paywalled) shows:

- `.claude/{rules,agents,skills}/` directories alongside `CLAUDE.md` +
  `settings.json` + `.mcp.json`.
- `CLAUDE.md` kept under ~500 tokens (the rest scoped into `rules/`).
- Subagents ~30 lines each, path-scoped.
- Skills modular via `SKILL.md`.
- "one pre-tool gate and one post-tool formatter" hook.

Current state of this repo's `.claude/`:
- `settings.local.json` only. No `agents/`, no `skills/`, no `rules/`,
  no `.mcp.json`.
- `CLAUDE.md` is 198 lines (well above the article's ~30-line guideline).
- Memory system is healthy (`MEMORY.md` index + 8 per-topic files).
- `.planning/` is our analog of the article's `rules/`.

**Recommendations** (not applied this session; documenting intent):

1. **Slim CLAUDE.md**. Keep the orientation lines (architecture overview,
   key paths). Move pipeline detail to `.claude/rules/{healing,recorder,
   compiler,invariants}.md`. Smaller top-level = less per-session context
   burden.
2. **Create `.planning/INDEX.md`** — one-line-per-document directory of
   every artefact in `.planning/`. Cheap retrieval substitute until a
   real vector index is in place. Each new doc adds one line.
3. **Add `.claude/agents/`** entries for recurring tasks:
   - `evidence-analyser.md` (the work done in EVIDENCE-ANALYSIS.md)
   - `spike-runner.md` (today's pattern: hypothesis → smoke test →
     truthful doc)
   - `market-scanner.md` (today's MARKET-SCAN.md flow)
4. **Real RAG / harness** for context preservation across sessions and
   model handoffs: out of scope for this repo. Logged as a project-level
   debt item. Substitute today: aggressive use of `.planning/` and
   per-session DECISIONS-LOG appends. The `MEMORY.md` system inside the
   Claude harness already approximates this for cross-session continuity.

Next session should start with a 30-minute pass on (1) + (2) to lower
context burden before any new spike or hotfix.

---

## 2026-06-27 — H22 Material-shape fixture spike (CONCLUSIVE)

Closes the gap left by the earlier `keyboard.type` spike (vanilla fixture
did not reproduce SIOPI's failure mode).

Full doc: [.planning/spikes/SPIKE-keyboard-type-mask.md](spikes/SPIKE-keyboard-type-mask.md) (H22 follow-up section).
Test: `tests/test_pages/spikes/test_material_currencymask.py`.
Fixture: `tests/intent_lab/pages/material-currencymask/index.html`.

Built a fixture that reproduces ng2-currency-mask: per-instance
`Object.defineProperty(input, 'value', ...)` plus a `keydown` handler
that intercepts and emits formatted display.

**Q1 — Replay (which API surfaces the masked value):**

```
fill                  → ''            ❌ (matches hotfix 16)
press_sequentially    → '10.000,00'   ✓
keyboard.type         → '10.000,00'   ✓
```

`fill()` is structurally broken against the per-instance override
pattern. `press_sequentially` and `keyboard.type` are interchangeable.
This pins exactly the failure mode the runner's `_fill_masked` already
defended against.

**Q2 — Record (does the prototype hook see writes):**

```
masked typing (with proto delegate): 4 captures
plain typing on plain input:         0 captures
```

The decisive finding: **real keyboard typing on a plain input never
fires the `value` setter at all**. Browser-native typing updates the
input via internal state. `_hookValue` only captures **JS-driven writes**
(mask scripts re-formatting the value), never raw user keystrokes.

For SIOPI Material currencymask:
- If the mask delegates writes through the prototype setter → hook
  catches → `value_mutations.jsonl` populated. (Today's working path
  for some masks.)
- If the mask uses an instance-only setter without proto delegate →
  hook misses → empty `value_mutations.jsonl`. (Today's SIOPI bug.)
- For plain inputs → hook always misses real typing.

This invalidates the premise that `value_mutations.jsonl` is the
primary capture path for user input.

### Decisions emitted

1. **Stop treating `value_mutations.jsonl` as primary**. New source
   priority in IntentReconstructor:

   ```
   final_state_snapshot  (highest — already written, single source of truth)
   keystroke aggregation (raw_events.jsonl, count digit keys between focus/blur)
   value_mutations       (lowest — only useful for masks that delegate to proto)
   ```

   Tracked as **H22a — re-rank source priority in `IntentReconstructor`**.

2. **Do not delete `_hookValue` yet**. It is still the only source for
   delegate-to-proto masks. Reassess after H22a runs in production
   recordings.

3. **`fill()` is forbidden for masked inputs**. Already encoded in
   `_fill_masked` → `press_sequentially`. Pin explicitly in
   REGRESSION-PATTERNS.md P1 as the canonical reason.

4. **The half of the normalizer mask path that re-reads
   `final_state_snapshot.json`** can be promoted to primary. Tracked
   as **H22b — normalizer source-priority refactor**.

### Estimate

H22a + H22b combined: 2-3 days. Risk: medium — the keystroke
aggregation must handle paste, IME composition, autocomplete pre-fill
(three known gaps).

---

## 2026-06-27 — H22b: dedupe telemetry on RecordingNormalizer

After H22a re-ranked the source priority table, the open question
became "is `setter_hook` still load-bearing once `final_state` is
primary?" H22b adds per-call telemetry on the normalizer so the
answer can be measured instead of guessed.

### What landed

`RecordingNormalizer` now carries `ir_dedupe_stats: dict` per instance,
reset on every `normalize()` call. Five counters:

```
loser_counts                          {source: int}
winner_counts                         {source: int}
setter_hook_dominated_by_final_state  int
setter_hook_uncontested               int
final_state_uncontested               int
```

`_ir_dedupe_entries` increments them as it picks winners between
sources for the same `field_key`. Stats are instance-local, not class-
level — a deliberate departure from the earlier P2 mutable-default
trap.

### What this unblocks

When the next SIOPI / SIMAX recording runs through the normalizer, we
will know:

- how many times `final_state` beat `setter_hook` (= cases where the
  hook was redundant).
- how many times `setter_hook` was the *only* source that produced a
  value for a field (= the remaining justification for keeping the
  hook).
- the same for `final_state` (= cases where the hook was structurally
  missing).

If `setter_hook_uncontested` stays at 0 across several real recordings,
H22c (delete `_hookValue` + `value_mutations.jsonl` pipeline) becomes
an evidence-based call rather than a speculative one.

### What this does NOT do

- No persistence of stats to disk (yet). They sit on the instance. A
  follow-up can write to `<recording>/normalizer_stats.json` and the
  pilot dashboard can aggregate.
- No CLI surfacing of the stats in `testforge run-incremental` or
  `testforge compile`. Wire-up is trivial when we want it.
- No new IR source. Keystroke aggregation (the original H22b spec from
  the spike doc) needs `keydown` capture in `overlay_inject.js` first,
  which is invasive enough to deserve its own ticket. Filed as **H22d**.

### H22c readiness criteria

`_hookValue` and `value_mutations.jsonl` can be deleted once:

1. `setter_hook_uncontested == 0` in 3 consecutive real recordings.
2. No regression in the existing P3 invariant for value_mutations
   round-trip (or that invariant is explicitly retired).
3. `_resolve_field_value` confirmed to work end-to-end using only
   `final_state`-sourced field_value_map entries on the SIOPI
   calculadora flow.

Estimate (post-readiness): ~1 day of mechanical deletion plus invariant
cleanup.

### Tests

`tests/test_h22b_dedupe_telemetry.py` — 7 new tests covering the
stats shape, the per-instance isolation, the dominated/uncontested
counters, and the reset-per-`normalize()` contract.

---

## 2026-06-27 — Capture fingerprint v1 + recording timeline audit

User asked why we needed to re-record after this session's changes and
flagged that the fear of "old recording → false bug" was real. Result:
zero re-recording required for what landed this session, plus a small
identity block embedded in every new recording so future-us can answer
the same question without redoing the analysis.

### Why no re-recording is needed for this session

Audit of every commit since `cf8cdb9` (start of this session):

| Commit | Touches recorder write format? |
|---|---|
| `9cb7a1d` H9+H16+P3 invariants | no — runner/gate/tests only |
| `880cfad` DECISIONS-LOG | no — docs |
| `dfd9db4` H17 batched replay-check | no — diagnostic timing only; artefacts written are identical |
| `5377f7e` MARKET-SCAN | no — docs |
| `8d6e948` keyboard.type spike | no — fixtures + smoke tests |
| `b6e7a73` H22 Material fixture | no — new fixture; no recorder change |
| `96bbd87` H22a IR priority | no — normalizer only |
| `7ec46ad` H22b dedupe telemetry | no — normalizer only |

Existing recordings are still readable by the current normalizer. H22a
re-ranks how the *existing* artefacts are interpreted; it does not
require new artefacts.

### Fingerprint block (new in this commit)

`src/testforge/recorder/capture_fingerprint.py` defines
`CAPTURE_SCHEMA_VERSION = 1` plus a block written into every new
`recording_metadata.json["fingerprint"]`:

```json
{
    "capture_schema_version": 1,
    "testforge_version": "0.x.y",
    "overlay_inject_sha256": "<64 hex>",
    "git_head_sha": "<40 hex>",
    "recorded_at": "..."
}
```

`RecordingNormalizer.normalize()` reads it via `verify_fingerprint()` and
logs a single warning per recording when:

- the block is missing → treated as legacy v0
- `capture_schema_version` differs from current
- `overlay_inject.js` hash differs from current

The verification result is cached on `normalizer.fingerprint_check` so
CLI callers can surface it in their summary output.

### Bump policy for CAPTURE_SCHEMA_VERSION

Bump **only** when the write format of a recording artefact changes:
- new fields in `raw_events.jsonl` / `value_mutations.jsonl` /
  `field_snapshots.jsonl` / `final_state_snapshot.json` / `steps.jsonl`
- renames or shape changes of existing fields
- changes to overlay JS that alter what fires `_persist_raw_event`

Do NOT bump for: timing / retry / fallback / UI / overlay shortcuts /
normalizer-only fixes. Last session that did change a write format was
hotfix 12 (`552e05c`, 2026-06-26 02:57); everything since has been
normalizer-side or perf-side.

### Recording audit table

Full per-recording bucket assignment in
[.planning/RECORDING-FINGERPRINTS-AUDIT.md](RECORDING-FINGERPRINTS-AUDIT.md).
Three buckets for existing artefacts:

- 🟥 incompatible (pre-Bug3/Bug9 step counter + fill dedup)
- 🟧 partial (post-SELECT, pre-pseudo-submit)
- 🟨 stable (post-hotfix-12, pre-fingerprint)

The 11 evidence recordings analysed earlier in EVIDENCE-ANALYSIS.md sit
in 🟥/🟧 mostly. Some of the "missing capture" findings there may
reflect known recorder gaps, not present-day bugs. H22c readiness
measurement (setter_hook_uncontested counter) should be evaluated only
on 🟨 or 🟩 recordings.

### No mutation of existing recordings

We do not backfill `recording_metadata.json` files in place. The
verifier already treats missing fingerprint as legacy v0 and warns.
The audit doc is the human-readable companion.

### Tests

`tests/test_capture_fingerprint.py` — 12 new tests covering: the block
shape, schema version invariant, sha256 hex format, determinism between
calls, embedding in new RecordingSession, finalize preservation,
verify_fingerprint compatibility / legacy / schema-mismatch /
overlay-sha-mismatch paths, normalizer caching of the check.

---

## How to use this log

- Read top to bottom before proposing a refactor.
- When a decision turns out wrong, do **not** delete it. Append a new entry that supersedes the old one with explicit reference (`Supersedes 2026-06-15 — v2 …`).
- When a bug recurs, add an entry noting the recurrence and what changed in the analysis.
