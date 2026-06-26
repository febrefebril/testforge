# Consolidation Sprint — break the hotfix-per-helper loop

**Status**: planned, 2026-06-26.
**Duration**: ~1 working day (8h).
**Trigger**: hotfixes 16 + 17 patched the same bug class twice in two helpers; the third helper still ships the bug. We pause new hotfixes and consolidate.

> Read this with [DECISIONS-LOG.md](DECISIONS-LOG.md). The diagnosis at the bottom of that file motivates this sprint.

---

## Problem statement (evidence)

Real run against `simuladorhabitacao.caixa.gov.br/home` (recording `test-pos-hotfix3`):

- `Step 12/14 click [OK] passed [field_map:Prestação desejada *]` — runner reports success but the field receives the wrong value, so:
- `pos-condicao: p:has-text("Valor do imóvel") nao encontrado` — Calcular button does nothing.
- After hotfix 16 the same run produced the same outcome.
- After hotfix 17 the third helper still has another divergence: user-supplied values via `--complete` produce `fill [FAIL] failed [input[aria-label="CPF"]]` because key normalization at fill time does not match the page's actual aria-label.
- File uploads record `C:\fakepath\filename` and the runner cannot resolve the real path.

Three different bugs, one structural cause: **logic duplicated across 4 functions in `step_executor.py` with no canonical implementation.**

| Function | Purpose | Has triple-click clear? | Has placeholder mask fallback? | Has date-mask branch? |
|---|---|---|---|---|
| `_execute_fill` (canonical) | action="fill" | Yes (hotfix 6) | Yes | Yes |
| `_fill_input` | click→missing_fill | After hotfix 16 + 17 | After hotfix 17 | After hotfix 16 |
| `_fill_by_aria_label` | aria-label fallback | After hotfix 16 | After hotfix 17 | After hotfix 16 |
| `_try_data_fill` | data_values fallback | After hotfix 16 | After hotfix 17 | After hotfix 16 |

The matrix was 4×4 of "this function may or may not have the same fix" until 17 closed the placeholder gap. There is no guarantee a future fix will be replicated to all 4. **The matrix itself is the bug.**

---

## Success criteria — what "done" means

This sprint succeeds only if, at the end:

1. **There is exactly one fill function for masked inputs** in `step_executor.py`. All 4 call sites converge on it. The matrix above is reduced to 1 row.
2. **A red-becomes-green test pins the SIOPI bug class**: a fixture page with a Material input that has `placeholder="R$0,00"` and **no** `currencymask` attribute, plus a date-mask input with `placeholder="DD/MM/AAAA"`, plus an aria-label with special characters (`*`, accents). The test fails on `main` before the consolidation; passes after.
3. **Every fill emits a structured log line** with: `fill_path={canonical|aria_label|data_fill|placeholder}`, `mask_detect={attr|placeholder|date|none}`, `cleared={true|false}`, `pressed_value=...`, `selector_used=...`. We can answer "which function ran on step N?" from `.testforge/spans.jsonl` without re-running.
4. **The bug class is documented** in `DECISIONS-LOG.md` with the resolution date and a link to the consolidating commit. Future contributors know to search the log before adding a sibling helper.
5. **Two added user findings are either fixed or formally on the backlog with reproduction steps**:
   - User-supplied `--complete` values not applied (`fill [FAIL]`) — root cause analysis + fix or backlog ticket.
   - File upload uses `C:\fakepath\` — backlog ticket with the prior-implementation note attached.

If even one criterion fails, the sprint did not converge and we re-plan, not ship.

---

## Why this approach works (theory)

Hotfixes 16 and 17 are evidence of a recurring failure mode. The sprint plan is a hypothesis test for the simplest causal claim that fits the evidence: **the bugs recur because the same logic exists in N places.** Reducing N to 1 forces every future fix to land in the right spot.

### Hypothesis

If the runner has exactly one canonical fill function for masked inputs, then:

- a bug discovered in one code path **must** be fixed in the only path that exists;
- the placeholder-mask fallback that hotfix 17 had to copy 3 times becomes a single line that all callers reach;
- a future contributor cannot accidentally add a fifth fill helper because the consolidating function is now the documented entry point.

### Why pinned fixtures matter

The Caixa SIOPI bug shape — Material input with currency mask but no `currencymask` attribute — never appeared in our tests. Real runs are the only reproducer. Real runs cost ~30 min each. We made the bug discoverable in real runs only, so we discovered it in real runs only.

Pinning a fixture with the production shape (no `currencymask` attribute, just placeholder; date mask; aria-label with `*`) flips the cost: bug-detection moves from 30 min to 30 s. We can fail-fast.

### Why structured logs matter

Hotfix 16 missed because we did not know which of the 4 functions ran. We guessed `_execute_fill` (wrong); the run still failed; we instrumented manually; we found `_fill_input` was the actual path; we patched it; the placeholder-mask gap surfaced; hotfix 17.

If the log had said `fill_path=_fill_input mask_detect=attribute_missing fallback=none cleared=false pressed_value=1.000,00` we would have shipped a single hotfix in 30 min. Telemetry pays for itself in the first incident.

### Why decisions go in DECISIONS-LOG.md

The honest critique is that we keep relearning the same lesson. v2 architecture was supposed to fix things; it did not, because nobody migrated consumers. Hotfix 7 was supposed to fix postbacks; it did not, because the metadata never reached disk. We had no living document that recorded "we tried this and it did not work for this reason."

Append-only `DECISIONS-LOG.md` is the cheapest fix for that. Next contributor reads top to bottom and knows what is already off the table.

---

## Plan — 4 work items, sequenced

### Item 1 — Consolidate fill helpers (~3-4h)

Touch: `src/testforge/runner/step_executor.py`, `tests/test_step_executor.py`.

**1.1 — Extract `_fill_masked(self, el, value)`**

Single function that:

- Detects mask via attribute *or* placeholder (`currencymask`, `R$`, `0,00`, `dd/mm`, `aaaa`).
- Returns `(mask_kind, type_value)` where `mask_kind ∈ {none, currency, date}`.
- For currency: strips to digits with `re.sub(r"[^0-9]", "", value)`.
- For date: keeps the formatted value (slashes position the cursor).
- For none: returns the original value.
- Triple-click clears the field before pressing.
- Calls `press_sequentially` for masks, `el.fill` for non-masks.
- Logs structured `fill_path/mask_detect/cleared/pressed_value/selector_used`.

**1.2 — Replace all 4 sites**

- `_execute_fill`: replace the in-line mask logic with a call to `_fill_masked`.
- `_fill_input`: same.
- `_fill_by_aria_label`: same.
- `_try_data_fill`: same.

**1.3 — Delete the dead matrix**

Remove the duplicated mask detection / digit-strip / press-sequence blocks. Net LOC: ~120 lines removed, ~30 added. Diff is a deletion, not an addition. That is the win.

**1.4 — Tests**

- Reuse the hotfix 16 + 17 tests, point them at `_fill_masked` directly.
- Add the cross-helper test: invoke each of the 4 helpers with the same SIOPI-shaped element mock; assert all 4 produce identical `press_sequentially` arguments.
- This is the regression guard: any future divergence between helpers will fail this test.

**Exit gate**: every `_fill_input` / `_fill_by_aria_label` / `_try_data_fill` call site reaches `_fill_masked`. `grep -c "press_sequentially" src/testforge/runner/step_executor.py` returns 1 (just the one inside `_fill_masked`).

---

### Item 2 — Pin production-shaped fixtures (~2-3h)

Touch: `tests/test_pages/runner_fills/`, `tests/test_runner_fill_paths.py`.

**2.1 — HTML fixture**

`tests/test_pages/runner_fills/index.html` with:

- `<input placeholder="R$0,00" aria-label="Prestação desejada *">` — currency-masked, no `currencymask` attr, aria-label with `*` (selector escape concern), accent in label.
- `<input placeholder="DD/MM/AAAA" aria-label="Data de nascimento">` — date mask.
- `<input aria-label="CPF" placeholder="000.000.000-00">` — masked but neither currency nor date.
- `<input aria-label="Nome completo">` — plain text.

Each input attaches a minimal JS mask listener that mimics what the Caixa input does (suppresses `input` event, reformats on keypress) so the helpers exercise the real failure shape.

**2.2 — Pytest module** `tests/test_runner_fill_paths.py`

For each of the 4 fill helpers and each of the 4 inputs, assert:

- The helper detects the mask correctly.
- The value pressed is the raw digits / formatted date / fill-as-is (per mask kind).
- The field shows the recorded display value after the helper runs.

Marked `@pytest.mark.slow` because it launches a browser. Acceptable: <5 s total.

**Exit gate**: `pytest tests/test_runner_fill_paths.py` passes. Revert `_fill_masked` to its pre-sprint state — the suite must go red. Then re-apply — green. This proves the suite actually exercises the bug class.

---

### Item 3 — Path telemetry (~1h)

Touch: `src/testforge/runner/step_executor.py`, `src/testforge/metrics/telemetry.py`.

Every `_fill_masked` call emits a JSONL span to `.testforge/spans.jsonl`:

```json
{
  "event": "fill.attempted",
  "step_index": 12,
  "fill_path": "_fill_input",
  "mask_detect": "placeholder",
  "mask_kind": "currency",
  "cleared": true,
  "pressed_value_redacted": "<currency:6 digits>",
  "selector_used": "input[aria-label=\"Prestação desejada *\"]",
  "result": "ok"
}
```

`pressed_value_redacted` follows the redaction guidance from `TELEMETRY-PLAN.md` (never log raw fill values; bucket by `value_kind` and length).

**Exit gate**: after running the smoke pipeline, `cat .testforge/spans.jsonl | jq '.event == "fill.attempted"'` shows one event per fill, with `fill_path` populated and the mask detection trail visible.

---

### Item 4 — Address the two new user findings (~1h)

**4.1 — `--complete` values not applied (`fill [FAIL]`)**

Root-cause analysis:

- Hypothesis 1: `field_value_map.json` keys are sanitized (`cpf`, `prestação_desejada_*`) but `_fill_input` builds patterns from the **raw** label, so CSS attribute equality fails.
- Hypothesis 2: the value-source priority in `_resolve_field_value` picks the wrong source.
- Hypothesis 3: aria-label at runtime differs from record-time aria-label (Caixa's mask plugin sometimes appends ` *` for required fields after first interaction).

Action:

- Add a log line in `_resolve_field_value` and `_fill_input` showing the resolved label + selector vs the actual element's aria-label.
- Re-run with the same recording.
- Confirm which hypothesis matches.
- Fix the single root cause; pin the failure in `tests/test_runner_fill_paths.py` as a new case.

This is in-scope for the sprint because it is **the same bug class** — divergence between record-time labels and runtime element labels.

**4.2 — File upload `C:\fakepath\filename`**

`<input type="file">` exposes `value` as `C:\fakepath\<filename>` for security; the real path is hidden from JS. Two options:

- **Capture-time fix**: `page.on('filechooser')` in RecorderController. When the chooser opens, copy the selected files to `recordings/<rid>/uploads/<basename>`. Record the basename in `raw_events.jsonl`. At runtime, `set_input_files(rec_dir/uploads/<basename>)`.
- **Replay-time fix**: ask the user via `--complete` for a path; runner uses that.

The prior implementation referenced by the user did the former. Action:

- Search git history for the prior implementation (`git log --oneline --all -S "filechooser"`).
- If found: revive it and add a fixture test.
- If not found: write a fresh `tests/test_recorder_file_upload.py` test that drives a file input, asserts a copy lands in `recordings/<rid>/uploads/`, and the resulting `raw_events.jsonl` has the basename.

Defer to backlog (`H5` in BACKLOG.md) if this overruns the sprint budget. **Do not** let it consume more than 1h. Time-box it.

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Consolidation introduces a new regression in `_execute_fill` (the canonical path used today) | medium | Re-run `tests/test_step_executor.py` after every step. Smoke pipeline (test 13) must still pass. Stop and bisect if either goes red. |
| Production-shaped fixture is *not* the production shape | low | Confirm by recording against the fixture and diffing raw_events vs the SIOPI recording. They should agree on `target.placeholder`, `target.attributes`, `target.aria_label`. |
| Telemetry adds latency or noise | low | Single JSONL append per fill, ~200 µs. Already proven in Phase 6. |
| File-upload work blows the timebox | medium | Strict 1h cap. Falls to backlog if not done. |
| The bugs do not actually share a root cause and consolidation does not fix them | low | Item 4.1's diagnostic step verifies the cause before claiming the fix works. |

---

## Out of scope (and why)

- **Replacing the recorder with Playwright codegen**: deferred — see `DECISIONS-LOG.md` 2026-06-26 entry. Not what unblocks pilot.
- **v2 phases (1-7) becoming load-bearing**: separate sprint. Pilot data tells us which phases to flip on first.
- **Closing all 7 G1-G7 gaps from the research doc**: separate sprint, post-pilot.

---

## After the sprint — what we should observe

1. Real run against Caixa SIOPI completes the fill step with the recorded value (R$ 1.000,00, not R$ 100.000,00, not concatenated junk).
2. `--complete` user-supplied values reach the field (no more `fill [FAIL]`).
3. `.testforge/spans.jsonl` answers "which fill path ran on step 12?" without re-running.
4. `DECISIONS-LOG.md` has a 2026-06-27 entry: "consolidation sprint shipped, bug class closed, fixture pinned."
5. Adding a new mask kind in the future (e.g. CNPJ) requires one change in `_fill_masked` + one fixture row, not 4 helpers + 4 sets of tests.

If we observe (1)-(4), the sprint worked. If we observe (5) the next time someone needs to add a mask, the sprint *kept* working.
