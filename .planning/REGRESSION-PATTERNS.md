# Regression Patterns Registry

Append-only catalog of anti-patterns we have shipped and re-shipped in TestForge. The point is to recognize the **class** of bug before fixing the **instance** of it — and to gate future commits against the class so the next occurrence is caught at CI, not at a real customer run.

> Read **before** writing a hotfix. If your bug fits a pattern below, the right fix is broader than the symptom you are looking at.

---

## How to use this file

1. **Before opening a hotfix**: search this file. If your symptom matches a registered pattern, your fix must address the pattern (not only the symptom) and bump the pattern's recurrence count.
2. **After landing a fix**: if the bug is novel, add a new pattern entry. If it is a recurrence, append to the existing one with the new commit SHA + lesson.
3. **Reviewer checklist**: for every PR that touches `step_executor`, `recording_normalizer`, `recorder_controller`, or any handler, scan this file. Reject changes that re-introduce a pattern unless the registry entry is updated with a justification.

Each entry has:

- **Name** — short label used in commit messages: `[class:<name>]`
- **First seen** — ISO date + commit SHA of the first occurrence we know about
- **Recurrence count** — how many times this class has appeared
- **Symptoms** — concrete observable failures the class produces
- **AST/grep check** — the cheapest static check that catches an instance
- **Invariant test** — a pytest that pins the property the pattern violates
- **Past occurrences** — table of every recorded instance

---

## P1 — Duplication produces divergent paths

- **Name**: `code-duplication-drift`
- **First seen**: 2026-06-17, commit `6bf85cb` (heuristic candidates duplicated)
- **Recurrence count**: 5 (hotfixes 9, 12, 16, 17, 19)
- **Symptoms**:
  - The same algorithm exists in 2+ functions with divergent details (e.g. one has triple-click clear, another does not; one detects mask by attribute, another by placeholder).
  - A hotfix patches one location; the bug returns next month in another location.
  - Tests for one location pass; integration breaks because the *other* location runs.
- **AST/grep check**:
  ```bash
  grep -c "press_sequentially" src/testforge/runner/step_executor.py  # must be 1
  ```
  More generally: any "primitive" operation (`press_sequentially`, `select_option`, `el.fill`, `el.click(click_count=3)`) should appear in exactly one production location per file.
- **Invariant test**:
  ```python
  def test_press_sequentially_lives_in_one_place():
      assert open(step_executor_path).read().count("press_sequentially") == 1
  ```
  See `TestCS1ConvergenceContract::test_press_sequentially_lives_in_one_place`.
- **Past occurrences**:

  | Date | SHA | Where | What | Why this didn't stop the next one |
  |---|---|---|---|---|
  | 2026-06-25 | `ee40d16` | step_executor.py | hotfix 9 — `_execute_select` orphaned mid-class | No AST check that class methods stay inside class body |
  | 2026-06-25 | `552e05c` | recorder_controller.py + auditor | hotfix 12 — pseudo_submit persistence + audit count | Hotfix 7 marked "follow-up" but no ticket; second logical path stayed unimplemented |
  | 2026-06-26 | `e66035b` | step_executor.py | hotfix 16 — `_fill_input` clear + digits | Fix landed in 1 of 4 helpers; same logic in 3 others not touched |
  | 2026-06-26 | `aac8209` | step_executor.py | hotfix 17 — placeholder fallback in 3 helpers | Fix repeated the same lines in 3 helpers instead of consolidating |
  | 2026-06-26 | `4373c40` | step_executor.py `_resolve_field_value` | hotfix 19 — FieldValueMap dataclass unwrapped, not str()'d | The fallback `return (str(entry), "")` silently shipped wrong shape; no test exercised the FieldValueMap entry path |

- **Lesson reinforced**: a hotfix that touches only the call site where a bug surfaced is **not done**. Either consolidate to one location, or add a contract test that asserts identical behavior across every site. CS-1 + CS-2's cross-helper contract test is the template.

---

## P2 — Silent defaults eat real signal

- **Name**: `silent-default-swallow`
- **First seen**: 2026-06-25, commit `ce1966e` (hotfix BUG 2 `try/except: pass` tolerance pattern)
- **Recurrence count**: 5 (hotfix 7, 14, 20, plus 20+ inline `try/except: pass` sites)
- **Symptoms**:
  - A real error fires (page closed, target gone, framework hung) but the code's `except Exception: pass` swallows it.
  - UI/visible state never updates ("Gravando..." stays after Shift+S).
  - A normalizer/handler decides to drop steps without emitting a span or a warning.
  - Telemetry only reports happy path; failure path is invisible.
- **AST/grep check**:
  ```bash
  # Should converge toward 0; allowlist is enforced separately.
  grep -rn "except Exception:" src/ | grep -A1 "pass" | wc -l
  ```
- **Invariant test**: every `try/except` block must either log at `debug` level or re-raise. Lint rule + CI grep. Documented per-site reason required.
- **Past occurrences**:

  | Date | SHA | Where | What |
  |---|---|---|---|
  | 2026-06-25 | `15bbde2` | recorder_controller.py | hotfix 7 — pseudo_submit only in memory; downstream consumers blind |
  | 2026-06-25 | `2d057a9` | overlay_inject.js + app.py | hotfix 14 — overlay banner did not signal stop in progress |
  | 2026-06-26 | `4373c40` | angular_material.py | hotfix 20 — datepicker handler silently suppressed click-only sequences |

- **Lesson reinforced**: silence is the worst telemetry. Add a span/log at the decision point even if the path succeeds. If a handler drops steps, it must emit a `handler.suppressed` event with reason and step_id so the runner's blind-spot count goes up — not stay at 0.

---

## P3 — State assumed but not anchored

- **Name**: `unanchored-state`
- **First seen**: 2026-06-25, commit `9eec732` (CWD vs `_PROJECT_ROOT`)
- **Recurrence count**: **4** (hotfix 8, 15, CS-4a, **hotfix 22**)
- **Symptoms**:
  - Producer and consumer of the same data structure disagree on its shape.
  - Recording artifacts saved relative to CWD but looked up via `_PROJECT_ROOT`.
  - A file's writer (e.g. `_save_field_value_map`) uses one JSON layout; the reader (e.g. `_merge_user_supplied_values`) expects another, and silently no-ops on every entry.
  - A JS overlay emits `{value, fingerprint}` and the Python reader looks for `{new_value, tag, id, name, old_value}` and gets nothing.
  - Two sides of a contract (`element_id` vs `id`) silently lose information at the boundary.
  - Tests of the writer pass. Tests of the reader pass. The integration silently loses data.
- **AST/grep check**:
  - For paths: `grep -rn "Path.cwd()" src/testforge/ | grep -v "testforge.paths.py"` — should be 0 once `testforge.paths` lands (debt R-A3).
  - For data shapes: every writer and reader of a JSONL/JSON file must reference the same dataclass / TypedDict.
- **Invariant test**: each on-disk artifact has one read/write round-trip test that uses the exact dataclass on both sides, never a hand-rolled dict. See:
  - `test_invariants.py::TestP3UnanchoredState::test_field_value_map_writer_reader_round_trip`
  - `test_invariants.py::TestP3UnanchoredState::test_value_mutations_writer_reader_round_trip`
  - `test_invariants.py::TestP3UnanchoredState::test_raw_event_target_to_semantic_target_round_trip`
- **Past occurrences**:

  | Date | SHA | Where | What | Why this didn't stop the next one |
  |---|---|---|---|---|
  | 2026-06-25 | `3140297` | cli/_run_incremental_patch.py | hotfix 8 — `run-incremental` rejected a dir path because consumer assumed a file | Path resolution had no invariant test |
  | 2026-06-25 | `9eec732` | cli/app.py + runner | hotfix 15 — recording_root anchored at CWD by recorder but at PROJECT_ROOT by CLI lookup | Centralization deferred to refactor sprint; instead we added more candidates |
  | 2026-06-26 | `aa27b54` | recording_normalizer.py | CS-4a — `field_value_map.json` writer/reader shape mismatch | The round-trip test covered ONLY field_value_map, not the other JSONL artifacts |
  | 2026-06-26 | `38d1ab4` | recording_normalizer.py | hotfix 22 — `value_mutations.jsonl` writer/reader mismatch AND `target.element_id` vs `target.id` key mismatch | The CS-4a invariant test only covered field_value_map.json; value_mutations and raw_event target were still unchecked |

- **Lesson reinforced**: every JSON/JSONL artifact, every dict-passed-between-modules, needs a writer/reader round-trip test. CS-4a's invariant covered one file. Hotfix 22 found two more under the same pattern. After hotfix 22 the invariant now covers all three artifacts the recorder/normalizer share. The next P3 recurrence must show that a NEW artifact slipped past the invariant, not the same one returning.

- **Hard rule (added 2026-06-26)**: any new on-disk artifact or any new dict shape passed between modules MUST land with a round-trip test in `test_invariants.py::TestP3UnanchoredState` in the same PR. No exceptions. Reviewers reject the PR otherwise.

---

## P4 — Phase shipped without consumer

- **Name**: `feature-flag-rot`
- **First seen**: 2026-06-15, commits `7a24ec4` → `b941950` (v2 phases 1-7)
- **Recurrence count**: 4 (Phase 1 AX snapshots; Phase 3 v2 compiler; Phase 4 SQLite catalog; hotfix 7 IntentReconstructor plumb-later)
- **Symptoms**:
  - "Additive, feature-flagged" code lands. Nobody flips the flag. The flag becomes a maintenance burden with no upside.
  - Real production bugs live in the unchanged legacy path. The v2 path is dead code.
  - Architecture review says "we already solved this in v2" — but nobody is using v2.
- **AST/grep check**: every feature flag has a default value. Open issue tracker for every feature flag with `default=False`.
- **Invariant test**: per-flag, a CI job runs both branches. If both pass, the legacy branch should be deleted.
- **Past occurrences**:

  | Date | SHA | What |
  |---|---|---|
  | 2026-06-15 | `7a24ec4` | Phase 1 — CDP AX snapshots captured to disk; 0 consumers |
  | 2026-06-17 | `f54abbd` | Phase 3 — v2 compiler behind `--use-v2-compiler`; pilot uses legacy |
  | 2026-06-17 | `750e2ac` | Phase 4 — SQLite intent catalog; legacy JSONL still default |
  | 2026-06-25 | `15bbde2` | hotfix 7 — "follow-up will plumb pseudo_submit into _ir_form_values" — never plumbed until hotfix 12 |

- **Lesson reinforced**: a feature flag is debt with interest. Either flip the default within 2 weeks (forcing migration) or delete the flag (and the parallel code path).

---

## P5 — Runtime magic substitution

- **Name**: `compile-runtime-divergence`
- **First seen**: 2026-06-23, original `_execute_click` priority chain
- **Recurrence count**: 3 (click→fill switch; datepicker silent suppression; healing strategies)
- **Symptoms**:
  - Compile output says action=X. Runner secretly does Y.
  - Reading the compiled `test_*.py` does not predict behavior.
  - Reviewers cannot trust the test_*.py contents.
  - A bug surfaces only in production runs; unit tests of compile pass; unit tests of execute pass.
- **AST/grep check**: no `execute()` branch may take a step with `action="click"` and call `_fill_input` / `set_input_files` / any non-click primitive without first emitting a `action_promoted` span.
- **Invariant test**: any branch in `execute()` that promotes an action must (a) be reachable from a compiled step and (b) emit a span. Cross-path tests assert the action recorded in spans matches the action the user expected.
- **Past occurrences**:

  | Date | SHA | What |
  |---|---|---|
  | 2026-06-23 | (older) | `_execute_click` priority 2: click step with missing_fill is silently filled |
  | 2026-06-22 | `b941950` | Phase 7 ComponentHandler — handlers silently drop steps |
  | 2026-06-26 | `4373c40` | hotfix 20 — datepicker handler suppressed click-only sequences |

- **Lesson reinforced**: every implicit promotion must become explicit. The normalizer (compile time) commits to the action. The runner does not invent new actions. If the runner discovers a mismatch, it logs and refuses the magic — let healing decide explicitly.

---

## Process — how patterns get added and enforced

### Adding a pattern

A pattern enters this registry when a fix touches the same conceptual area for the second time **or** when a reviewer sees a class boundary being crossed silently. The PR that adds the pattern must include:

- A regression test that fails on the pre-fix code.
- The AST/grep check committed to `tests/test_invariants.py` (to be added).
- A line in DECISIONS-LOG.md cross-referencing this file.

### Enforcing a pattern

Three layers:

1. **Static** — AST/grep checks run as `pytest tests/test_invariants.py`. Cheap, fast, no browser.
2. **Contract tests** — like `TestCS1ConvergenceContract::test_press_sequentially_lives_in_one_place`. They encode the invariant in test form and run on every commit.
3. **Review checklist** — reviewers scan this file for any PR touching the affected modules. The PR description must reference which patterns it could re-introduce and why it does not.

### Reviewing recurrences

When a pattern recurs:

- Increment the recurrence count.
- Add a row to "Past occurrences" with the date, SHA, what, and why the previous fix didn't prevent this.
- Tighten the AST/grep check or invariant test so this exact recurrence couldn't have shipped.
- Update DECISIONS-LOG.md with the lesson.

### Why this works

The fundamental problem is that learning from one bug should make the next bug of the same class **impossible to ship**, not just "less likely". The registry forces three things:

1. Every fix is paired with a check that catches the class.
2. Every recurrence costs an explicit count + tighter check — the cost of repetition goes up.
3. Reviewers have one file to read before approving structural changes. The discipline is cheap because the file is short.

If after 3-4 entries a pattern keeps recurring despite a static check, the static check is the wrong shape. The fix is then to escalate to a stronger structural change (collapse the duplicated module, delete the legacy branch, etc.).

---

## Open questions

- Should `test_invariants.py` block CI or just warn? (proposal: block after first month of usage)
- Where do we surface this file to new contributors? (CLAUDE.md should reference it)
- How often should we audit it for stale entries? (quarterly review)
