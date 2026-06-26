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

## How to use this log

- Read top to bottom before proposing a refactor.
- When a decision turns out wrong, do **not** delete it. Append a new entry that supersedes the old one with explicit reference (`Supersedes 2026-06-15 — v2 …`).
- When a bug recurs, add an entry noting the recurrence and what changed in the analysis.
