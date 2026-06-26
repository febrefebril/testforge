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

## How to use this log

- Read top to bottom before proposing a refactor.
- When a decision turns out wrong, do **not** delete it. Append a new entry that supersedes the old one with explicit reference (`Supersedes 2026-06-15 — v2 …`).
- When a bug recurs, add an entry noting the recurrence and what changed in the analysis.
