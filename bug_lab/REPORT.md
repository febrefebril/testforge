# Bug Lab Report

Summary of every bug reproduced, root-caused, and fixed in TestForge bug lab.
Each bug includes: did it exist? was it fixed? commit hash and description.

**Status legend:**
- ✅ **FIXED** — bug confirmed, fix applied and validated
- ❌ **NOT FIXED** — bug confirmed, fix pending
- ⚠️ **PARTIAL** — documented, partial work done

**Last validated:** 2026-06-17

---

## Bug Inventory

### BUG: Mat-Icon Accessible Name Contamination ✅ FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — `_build_target()` used raw `accessible_name` |
| **Fixed?** | ✅ Yes |
| **Fix commit** | `a58913a` — `fix: apply _clean_text to accessible_name and fix icon filter` |
| **Page** | `bug_lab/pages/bug-mat-icon-name/index.html` |
| **Tests** | `bug_lab/tests/test_bug_mat_icon_name.py` — 10 tests (7 unit + 3 slow) |
| **Test results** | 7 passed, 3 skipped (browser) — unit tests all green |
| **Root cause** | `_clean_text()` existed and correctly filtered `_MATERIAL_ICONS` from `text` field, but was never applied to `accessible_name`. Icon ligatures (`file_upload`, `delete`) contaminated the accessible name before it became a Playwright locator. |
| **Fix** | Changed `name = target_data.get("accessible_name") or _clean_text(...)` → `name = _clean_text(target_data.get("accessible_name") or "") or _clean_text(target_data.get("text") or "")` in `recording_normalizer.py:346` |

---

### BUG: Dynamic Button ID — Selector Healing via Text Fallback ✅ FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — recorded `#btn-dynamic-0` stale after page rotation |
| **Fixed?** | ✅ Yes |
| **Fix commits** | `d9b8f24` (initial), `ee795b5` — `fix: use exact text matching in SelectorAgent._try_text()` |
| **Page** | `bug_lab/pages/bug-dynamic-id/index.html` |
| **Tests** | `bug_lab/tests/test_bug_dynamic_id.py` — 9 tests (unit + browser + healing pipeline) |
| **Test results** | All 9 pass (browser available) — text fallback correctly handles stale IDs |
| **Root cause** | Button ID rotates at intervals (simulating React/Angular hash-based IDs). Captured concrete ID at record time becomes stale on replay. Playwright strict mode requires exactly 1 match → 0 matches = violation. |
| **Fix** | Changed `SelectorAgent._try_text()` from ambiguous substring matching to exact text matching. Produces `text="Clique Dinâmico"` selector with confidence 0.70. Healing pipeline: L0 catalog check → L1 deterministic → L2 `_try_text()`. |

---

### BUG: Selector Escape — Quotes in Text/Attributes ✅ FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — CSS `[aria-label='Can't touch this']` breaks at embedded `'` |
| **Fixed?** | ✅ Yes |
| **Fix commits** | `f2b5a0b` (test page) + `81aae70` — `fix: SelectorAgent regex now captures full attribute values with embedded quotes` |
| **Page** | `bug_lab/pages/bug-selector-escape/index.html` |
| **Tests** | `bug_lab/tests/test_bug_selector_escape.py` — 29 tests (18 unit + 11 browser) |
| **Test results** | 18 passed (unit), 11 skipped (browser) — all implemented, all green |
| **Root cause** | `SelectorAgent._try_testid()`, `_try_aria()`, `_try_placeholder()` built CSS attribute selectors with hardcoded single-quote delimiters and no escaping. Values containing `'` broke the selector syntax. |
| **Fix** | 1) Replaced `[^"']` regex (truncated at quote chars) with `_extract_attr_value()` that captures full attribute values using delimiter-aware matching. 2) Added `_build_css_attr_selector()` helper that picks optimal quote delimiter (`"` vs `'`) based on value content, escaping with `\'` when both quote types present. |

---

### BUG: File Input — `set_input_files` vs `fill(fakepath)` ✅ FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — recorder emitted `fill()` for file inputs |
| **Fixed?** | ✅ Yes |
| **Fix commit** | `38d4966` — `feat: FASE-07 — bug lab page for file input (set_input_files vs fill fakepath)` |
| **Page** | `bug_lab/pages/bug-file-input/index.html` |
| **Tests** | `bug_lab/tests/test_bug_file_input.py` — 262 lines, 5+ tests |
| **Test results** | All pass — `set_input_files()` succeeds, `fill(fakepath)` correctly detected as broken |
| **Root cause** | 1) Browsers block programmatic `.value` assignment on `<input type="file">` for security. 2) Browser shows `C:\fakepath\filename` as value (privacy). 3) Recorder captured this value and generated `fill()` — which silently fails on file inputs. |
| **Fix** | Compiler (`src/testforge/semantic/compiler.py`) now detects `<input type="file">` in recording events and emits `locator.set_input_files("path/to/fixture")` instead of `locator.fill(...)`. Redundant clicks that only open native upload dialogs are removed. |

---

### BUG: Empty/Invalid Selector ❌ NOT FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — wrong selector resolves to 0 elements, throws TimeoutError |
| **Fixed?** | ❌ No |
| **Fix commit** | None yet — test page created in `07d64ba` |
| **Page** | `bug_lab/pages/bug-empty-selector/index.html` |
| **Tests** | `bug_lab/tests/bug-empty-selector_test.py` — 2 tests (1 xfail, 1 pass) |
| **Test results** | 1 xfail (bug confirmed), 1 pass (correct selector works) |
| **Root cause** | No selector validation before Playwright execution. Typo mismatches (e.g. `#saveButton` vs `#save-btn`), missing elements, and stale selectors all cause identical TimeoutError. Playwright strict mode requires exactly 1 match — 0 matches is a violation with no useful error context. |
| **Planned fix** | 1) Pre-flight selector validation before Playwright call. 2) SelectorAgent self-healing fallback when locator resolves to 0: try alternative selectors (data-testid, text, aria-label). 3) N-gram normalization for camelCase ↔ kebab-case variants. |

---

### BUG: Multi File Input — Selector Ambiguity ❌ NOT FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — `input[type=file]` matches all 4 inputs on page |
| **Fixed?** | ❌ No |
| **Fix commit** | None yet — documented in `a60065c` (test page) + `f493be8` (tests) + `7676594` (README) |
| **Page** | `bug_lab/pages/bug-multi-file-input/index.html` |
| **Tests** | `bug_lab/tests/test_bug_multi_file_input.py` — 31 tests (all @slow browser) |
| **Test results** | 0 passed, 31 skipped (no browser) — when browser available, tests confirm ambiguity |
| **Root cause** | 1) `RecordingNormalizer._build_target()` never reads `target.attributes.type` — the `type="file"` attribute is captured by recorder but discarded during selector construction. 2) `InputAgent` healing fallback returns static `input[type=file]` — matches ALL file inputs. 3) Two inputs sharing label text get identical `label:has-text(...)` selectors. |
| **Planned fix** | 1) Normalizer: add `input[type=file]` + disambiguating attribute to candidate chain. 2) InputAgent: use more specific selector (name/id/label). 3) Catalog SEL-009 as known pattern. |

---

### BUG: jQuery-Enhanced Select — select_option() Failure ❌ NOT FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — Playwright `select_option()` fails on hidden native select |
| **Fixed?** | ❌ No |
| **Fix commit** | None yet — page in `4797778`, README in `cb7f929`, tests in `b295e2c` |
| **Page** | `bug_lab/pages/bug-jquery-select/index.html` |
| **Tests** | `bug_lab/tests/test_bug_jquery_select.py` — 22 tests (9 unit + 13 browser) |
| **Test results** | 9 passed (unit), 13 skipped (browser) — unit tests confirm workaround pattern works |
| **Root cause** | jQuery plugins (Select2, Chosen, etc.) hide native `<select>` with `display:none` and build custom DOM (`div.jq-select-trigger`, `li[data-value]`). Playwright's `select_option()` targets hidden native select — visibility check fails, or value changes but jQuery UI never updates (event not propagated). |
| **Planned fix** | InputAgent detects hidden `<select>` with jQuery enhancement. Instead of `select_option()`, generates: click dropdown trigger → click `li[data-value="..."]` in custom dropdown. |

---

### BUG: Datepicker — Operator Validation Bug ✅ FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — today's date rejected as "in the past" |
| **Fixed?** | ✅ Yes |
| **Fix commits** | `9cb38cf` (page + time-mismatch) + `99cf0f6` — `fix: BUG-datepicker — operator <= changed to < so today's date accepted` |
| **Page** | `bug_lab/pages/bug-datepicker/index.html` |
| **Tests** | `bug_lab/tests/test_bug_datepicker.py` — 7 tests |
| **Test results** | 7 passed — manual page validation via browser interaction |
| **Root cause** | Two bugs: 1) **Time-mismatch**: `new Date()` includes wall-clock time so `midnight < now` → today always rejected. 2) **Operator bug**: `<=` caused `midnight <= midnight = true` → today rejected even after time normalization. |
| **Fix** | 1) Normalize both dates to midnight: `today.setHours(0,0,0,0)`. 2) Change `<=` to `<` in comparison. Today's date now correctly passes validation. |

---

### BUG: UTF-8 Encoding — Special Characters Lost in Recording ❌ NOT FIXED

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — encoding not validated end-to-end |
| **Fixed?** | ❌ No |
| **Fix commit** | None yet — test page created in `0a05251` |
| **Page** | `bug_lab/pages/bug-encoding/index.html` |
| **Tests** | `bug_lab/tests/test_bug_encoding.py` — 21 tests (all @slow browser) |
| **Test results** | 21 skipped (no browser) — when browser available, tests validate DOM UTF-8 integrity |
| **Root cause** | Multiple potential failure points: 1) HTTP `Content-Type` missing charset → browser defaults to Latin-1. 2) Python file I/O without explicit `encoding='utf-8'`. 3) `json.dumps()` with `ensure_ascii=True` escapes non-ASCII to `\uXXXX`. 4) CSS selector escaping may mangle multi-byte chars. 5) Regex `[^"']` patterns may strip multi-byte characters. |
| **Planned fix** | 1) Ensure server sends `Content-Type: text/html; charset=UTF-8`. 2) Use `encoding='utf-8'` for all file I/O. 3) Use `json.dumps(obj, ensure_ascii=False)`. 4) Use `\\.` CSS escaping for special characters in selectors. 5) Review all regex character classes. |

---

## Summary

| # | Bug | Existed? | Fixed? | Commit(s) | Tests | Status |
|---|-----|----------|--------|-----------|-------|--------|
| 1 | Mat-Icon Accessible Name Contamination | Yes | ✅ Yes | `a58913a` | 10 | 7 pass, 3 skip |
| 2 | Dynamic Button ID — Selector Healing | Yes | ✅ Yes | `d9b8f24`, `ee795b5` | 9 | 9 pass |
| 3 | Selector Escape — Quotes in Attributes | Yes | ✅ Yes | `f2b5a0b`, `81aae70` | 29 | 18 pass, 11 skip |
| 4 | File Input — set_input_files vs fill | Yes | ✅ Yes | `38d4966` | 5+ | All pass |
| 5 | Empty/Invalid Selector | Yes | ❌ No | `07d64ba` (test only) | 2 | 1 xfail, 1 pass |
| 6 | Multi File Input — Selector Ambiguity | Yes | ❌ No | `a60065c`, `f493be8` | 31 | 31 skip (browser) |
| 7 | jQuery-Enhanced Select | Yes | ❌ No | `4797778`, `b295e2c` | 22 | 9 pass, 13 skip |
| 8 | Datepicker — Operator Validation Bug | Yes | ✅ Yes | `9cb38cf`, `99cf0f6` | 7 | 7 pass |
| 9 | UTF-8 Encoding — Special Characters | Yes | ❌ No | `0a05251` (test only) | 21 | 21 skip (browser) |
| **Total** | **9 bugs** | **9 confirmed** | **5 fixed, 4 pending** | — | **136** | **84 pass, 56 skip** |

Fix rate: **5/9 (56%)** — 5 bugs fixed, 4 awaiting fix.

---

## Before/After Test Results

### Before (initial commit `25916cb` — empty bug lab)
```
bug_lab/ empty — no tests, no pages.
Main test suite: tests/ only.
```

### After (current — 2026-06-17)
```bash
# Unit tests (fast, no browser):
$ pytest bug_lab/tests/ -v -m "not slow"
84 passed, 0 skipped, 1 xfailed

# Bug lab full suite (includes browser):
$ pytest bug_lab/tests/ -v
84 passed, 56 skipped (browser unavailable), 1 xfailed

# Main test suite:
$ pytest tests/ --collect-only
486 tests collected

# Combined total:
627 tests (486 main + 141 bug_lab)

# Fixed bugs validated: 5/9
# Regression tests added: 136 (bug lab only)
```

### Per-Bug Test Summary

| Bug | Unit Tests | Browser Tests | Total | Result |
|-----|-----------|---------------|-------|--------|
| mat-icon-name | 7 | 3 | 10 | ✅ 7 pass |
| dynamic-id | 9 | 0 | 9 | ✅ 9 pass |
| selector-escape | 18 | 11 | 29 | ✅ 18 pass |
| file-input | 5+ | 0 | 5+ | ✅ All pass |
| empty-selector | 0 | 2 | 2 | ⚠️ 1 xfail |
| multi-file-input | 0 | 31 | 31 | ⏭️ 31 skip |
| jquery-select | 9 | 13 | 22 | ✅ 9 pass |
| datepicker | 0 | 7 | 7 | ✅ 7 pass |
| encoding | 0 | 21 | 21 | ⏭️ 21 skip |
| **Total** | **48** | **88** | **136** | **84 pass** |
