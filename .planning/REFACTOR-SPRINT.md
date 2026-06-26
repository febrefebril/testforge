# Refactor Sprint — design pattern cleanup

**Status**: planned, starts after `CONSOLIDATION-SPRINT.md` ships.
**Duration estimate**: 10-14 working days. Likely split in two sub-sprints.
**Trigger**: user decision 2026-06-26 — fix the anti-patterns surfaced by the SIOPI debugging cycle.

> Read order: [DECISIONS-LOG.md](DECISIONS-LOG.md) → [DEBT-INVENTORY.md](DEBT-INVENTORY.md) → this file. Pilot release is between consolidation sprint and this one.

---

## Why this sprint, why now

Consolidation sprint removes the immediate pilot blocker (fill helper divergence) and adds telemetry. **It does not fix the structural causes**. Those causes are inventoried in `DEBT-INVENTORY.md` and reproduced briefly here:

- 4 fill helpers were a symptom of a broader pattern — three god classes (`RecorderController`, `RecordingNormalizer`, `overlay_inject.js`) accumulate responsibility.
- Path resolution is scattered across 4 sites; hotfix 15 added a candidate rather than centralizing.
- `try/except: pass` proliferated as "tolerance"; loses signal.
- Click-can-secretly-become-fill is the recurring bug type — silent action promotion in the runner.
- v2 phases (1-7) shipped but are dead in production — additive feature flags nobody flipped.

If consolidation sprint closes a hole and we resume hotfix-driven work, the holes return. The refactor sprint closes the **structural** causes.

---

## Scope — what is in (P1 from DEBT-INVENTORY)

| ID | Item | Estimate | Order |
|---|---|---|---|
| R-A2 | Collapse `stop()` and `finalize()` into one `shutdown()` | 1d | 1 |
| R-A3 | `testforge.paths` module — single source for project paths | 0.5d | 2 |
| R-C1 | `@tolerate` decorator policy + sweep | 0.5d | 3 |
| R-E2 | Compile-time `action="fill"` decision (kill click→fill magic) | 1d | 4 |
| R-E3 | Stable `step_id` UUID at record time, key everything off it | 0.5d | 5 |
| R-B1 | Split `RecorderController` into 4 collaborators | 2-3d | 6 |
| R-B2 | Split `overlay_inject.js` into 4 concatenated modules | 1-2d | 7 |
| R-B3 | Finish migration of `RecordingNormalizer` to v2 Phase 5 stage pipeline | 2-3d | 8 |
| R-E1 | `LocatorStrategy` enum + deterministic runner walk | 1-2d | 9 |

Total: 10-14d. Recommended split:

- **Sub-sprint 1 (5d)**: R-A2, R-A3, R-C1, R-E2, R-E3. Small, contained, sets foundation.
- **Sub-sprint 2 (5-9d)**: R-B1, R-B2, R-B3, R-E1. Heavier — god class splits + runner reshape.

---

## Out of scope (deferred to P2 / P3)

- v2 vs legacy duplicate code (catalog, compiler) — needs pilot data to choose.
- Step model unification (`SemanticAction` / `RawRecordedEvent` / internal Step) — needs pilot data to know which fields matter.
- AX-tree consumer (gap G1 from research) — needs pilot data to justify cost.
- ComponentHandler full implementations per framework — needs pilot data to prioritize.
- Tests-as-contracts directory — process change, separate effort.

---

## Why this works — design pattern theory per item

### R-A2 — Single `shutdown()` method

**Pattern**: replace **multi-step teardown protocol** with **single teardown method**. Eliminates ordering bugs by making the order an implementation detail of one function rather than a contract between five callers.

**Before**: `cmd_record → stop() → finalize() → diagnostic.finalize() → browser.close()` — 5 boundaries, each can fail.

**After**: `recorder.shutdown(close_browser=True, gherkin_overrides={...}) → returns CompletedSession`. The function owns ordering internally; consumers do not encode it.

**Why it works**: hotfix 14 and 15 were ordering bugs. If only one function decides order, ordering bugs cannot propagate.

### R-A3 — `testforge.paths` module

**Pattern**: **service locator** for paths.

**Before**: `_PROJECT_ROOT` recomputed in `cli/app.py`; `Path.cwd()` in healing catalog; `Path(__file__).resolve().parents[N]` in runner; `recordings_root` param in `RecorderController`.

**After**: import `testforge.paths` — `paths.project_root`, `paths.recordings_root`, `paths.semantic_tests_root`, `paths.healing_catalog`. Single computation, every consumer agrees.

**Why it works**: hotfix 15 fixed a path bug by adding a candidate. Same shape would happen again whenever a new consumer ships. Centralizing kills the class.

### R-C1 — `@tolerate` decorator policy

**Pattern**: **explicit exception policy** instead of bare `try/except: pass`.

**Before**:
```python
try:
    self._capture_final_state_snapshot("recording_stopped")
except Exception:
    pass
```
Twenty-plus sites. Eats real errors silently.

**After**:
```python
@tolerate(closed_page=True, log_level="debug", reason="hotfix 2: page may be closed at finalize")
def _capture_final_state_snapshot(self, label: str) -> None:
    ...
```
- `closed_page=True` declares the only acceptable exception class (Playwright closed-target errors).
- `log_level` decides whether to log or stay silent.
- `reason` is required (linter enforces) and explains *why*.

**Why it works**: the bug shape was "a real error is mistaken for tolerated". Forcing each tolerate site to declare *which class* it swallows means a `PermissionError` is no longer mistaken for a `TargetClosedError`. Lint rule: bare `except: pass` is forbidden.

### R-E2 — Compile-time fill decision

**Pattern**: **explicit polymorphism** instead of runtime magic.

**Before**: step has `action="click"`. Runner inspects `context.missing_fill` and decides to fill instead. The compile-time view says "click"; the runtime view says "fill". Tests covering compile do not exercise the fill path.

**After**: normalizer commits to `action` at compile time. If a click on an input has a known fill value, emit `action="fill"`. Otherwise emit `action="click"`. Runner has one path per action, no magic.

**Why it works**: silent promotion is the root of the most pernicious bugs (current `fill [FAIL]` on `--complete`). Making the action explicit at compile time means the compiled test_*.py shows the truth; reviewers can see "this is a fill"; tests of the compiler exercise the path.

### R-E3 — Stable `step_id`

**Pattern**: **identity** before **ordering**.

**Before**: steps are referenced by `step_index` (position in the array). Re-normalization (e.g. after `--complete`) can shift indices; field-value maps keyed by the old index point to the wrong step.

**After**: every recorded step gets a UUID4 `step_id` at record time. Field-value map keys by `step_id`. Re-normalization preserves IDs. Indices are display-only.

**Why it works**: this is the same pattern as primary keys in databases. Position is not identity. Decoupling them removes a whole class of "step N got the wrong value" bugs.

### R-B1 — RecorderController split

**Pattern**: **collaborator extraction** (Refactoring: Improving the Design of Existing Code, Fowler).

**Before**: 540 LOC class, 18+ methods, 7+ orthogonal responsibilities. Every new feature lands here. Every test mocks half of it.

**After**: four collaborators behind narrow interfaces, one thin facade:

```
class RecorderController:
    def __init__(self, page, recordings_root):
        self._event_capture = EventCapture(page, on_request=..., on_close=...)
        self._snapshots = SnapshotStore(...)
        self._diagnostic = DiagnosticBridge(...)
        self._lifecycle = LifecycleController(...)

    def start(self, ...): self._lifecycle.start(...)
    def shutdown(self, ...): self._lifecycle.shutdown(...)
    # all other methods delegate
```

**Why it works**: each collaborator is testable in isolation (no need to mock a Playwright page just to test the command queue). Adding a feature lands in one collaborator, not the god class. The matrix of responsibilities is explicit.

### R-B2 — overlay_inject.js split

**Pattern**: same as B1, applied to JS. Concatenation at load time (Python reads 4 files, joins with `\n//---\n`) keeps the deployment story simple — no bundler needed.

**Why it works**: hotfix 14 added the stopping UI inline because there was no obvious module for it. Module boundaries make the answer to "where does this go?" automatic.

### R-B3 — Finish normalizer migration

**Pattern**: **pipes and filters** (already designed in v2 Phase 5, partially shipped).

**Before**: `RecordingNormalizer.normalize()` is a 1750-LOC monolith with `_ir_*` helpers embedded.

**After**: `Pipeline([CompactStage, ContextStage, PollingIRStage, ValueMutationIRStage, SnapshotIRStage, FormValuesIRStage, NetworkIRStage, FieldValueResolverStage, CompletenessStage])`. Each stage has a typed input/output and a test.

**Why it works**: v2 Phase 5 already shipped the infrastructure (`semantic/stages/`). The remaining work is migration of 5 `_ir_*` methods. Same code, organized differently. Tests for each stage in isolation.

### R-E1 — LocatorStrategy enum

**Pattern**: **explicit strategy** instead of **implicit fallthrough**.

**Before**: compiler emits a list of selector strings. Runner has 10 SmartStepRunner strategies that can substitute (`visibility_wait`, `press_sequentially`, `overlay_dismiss`, …). Order of try-and-fall-through is implicit. Compiler does not know which strategy will win.

**After**:
```python
class LocatorStrategy(Enum):
    GET_BY_ROLE_EXACT = 1     # role + accessible name
    GET_BY_ROLE_FUZZY = 2     # role + regex name
    GET_BY_LABEL = 3
    GET_BY_PLACEHOLDER = 4
    GET_BY_TEST_ID = 5
    GET_BY_TEXT = 6
    CSS_FULL_PATH = 7
    CSS_FRAGMENT = 8
    XPATH = 9
```
Compiler emits a list of `(LocatorStrategy, selector_args)` tuples ordered by priority. Runner walks in order, no implicit promotion. Healing escalates to the next level explicitly.

**Why it works**: this is what Playwright codegen does internally (decision 2026-06-26 — copy the priority chain, not the recorder). Reorder by `DEBT-INVENTORY` G2 from research doc.

---

## Success criteria

The sprint succeeds only if:

1. **No bare `try/except: pass`** in the production source (excluding generated code). `grep -r "except Exception:\s*pass" src/ | wc -l` returns 0.
2. **One teardown method**. `grep -c "browser.close" src/testforge/cli/app.py` returns 1 (or zero — moved to `recorder.shutdown`).
3. **`step_id` exists** in `SemanticAction` and is non-empty for every recorded step.
4. **`testforge.paths` is the only place project root is computed**. Linter rule rejects `Path(__file__).resolve().parents[N]` outside that module.
5. **`RecorderController` is <200 LOC**. Collaborators sum to roughly the same total — the goal is split, not addition.
6. **`overlay_inject.js` is split** into named modules concatenated at load time.
7. **`compile_v2` is the default**, or legacy `compile` is deleted. No middle.
8. **Real Caixa SIOPI run still passes** end to end (regression guard for the consolidation sprint's pin).
9. **DECISIONS-LOG.md** has a closing entry for the sprint with commit SHA range.

If any criterion fails, the sprint did not converge. Do not declare done.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Splitting a god class introduces a regression | Each collaborator extraction is its own commit with passing tests before/after. Smoke pipeline (test 13) runs after each commit. Bisect if any goes red. |
| `compile_v2` is not actually feature-equivalent | Run both compilers on every recording in the corpus; diff outputs; close gaps before switching default. |
| Step-id migration breaks existing recordings | Backward compatibility: missing `step_id` falls back to deterministic hash of `(step_index, action, target.fingerprint)`. Existing recordings load. |
| Refactor takes longer than 14 days | Split is already 2 sub-sprints. Pause after sub-sprint 1 and decide whether sub-sprint 2 still makes sense given pilot data. |
| Pilot data invalidates the sprint plan | Read pilot telemetry first. If a P2 item from `DEBT-INVENTORY` is hotter than something in this sprint, swap. |

---

## After this sprint

The codebase should reach a steady state where:

- Adding a new framework handler is a one-file change in `handlers/`.
- Adding a new fill strategy is a one-function change in the consolidated fill module.
- Adding a new locator strategy is one enum entry + one runner case.
- Reading the recorder's stop sequence takes one method, not five files.

That is what "stable foundation" means. The next pilot can ride on it without hotfixes per mask kind.
