# Bug Lab Report

Summary of bugs reproduced, root-caused, and fixed in the TestForge bug lab.

---

## BUG: Mat-Icon Accessible Name Contamination

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes |
| **Fixed?** | Yes — commit `a58913a` |
| **How?** | Applied `_clean_text()` to `accessible_name` in `_build_target()` (line 346 of `recording_normalizer.py`). Before: `name = target_data.get("accessible_name") or _clean_text(...)`. After: `name = _clean_text(target_data.get("accessible_name") or "") or _clean_text(target_data.get("text") or "")`. This strips Material icon ligatures (e.g., `file_upload`) from the accessibility tree name before using it as a Playwright locator. |
| **Page** | `bug_lab/pages/bug-mat-icon-name/index.html` |
| **Tests** | `bug_lab/tests/test_bug_mat_icon_name.py` — 10 tests (7 unit + 3 slow integration) — all pass |
| **Root cause** | `_build_target()` used `accessible_name` raw. `_clean_text()` existed and correctly filtered `_MATERIAL_ICONS` from `text`, but was never applied to `accessible_name`. |

---

## BUG: Dynamic Button ID — Selector Healing via Text Fallback

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes |
| **Fixed?** | Yes — commit `ee795b5` |
| **How?** | Changed `SelectorAgent._try_text()` to use exact text matching (`text=` or `:has-text()`) instead of ambiguous substring matching. This ensures dynamic ID buttons (where `id` rotates on page load) fall back to stable text-based selectors. |
| **Page** | `bug_lab/pages/bug-dynamic-id/index.html` |
| **Tests** | `bug_lab/tests/test_bug_dynamic_id.py` — 220 lines, unit + browser + healing pipeline |

---

## BUG: Selector Escape — Quotes in Text/Attributes

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes |
| **Fixed?** | **FULLY FIXED** — commit `f2b5a0b` (test page + browser tests) + commit TBD (SelectorAgent regex fix) |
| **How?** | 1) Test page created with buttons containing quotes in text, aria-label, data-testid, and placeholder attributes. 2) Browser tests confirm Playwright handles `\'` escaping in CSS selectors. 3) **SelectorAgent fix**: replaced `[^"']` regex (which truncates at quote chars) with `_extract_attr_value()` that captures full attribute values using delimiter-aware matching. Added `_build_css_attr_selector()` helper that picks optimal quote delimiter (`"` vs `'`) based on value content, escaping with `\'` when both quote types present. |
| **Page** | `bug_lab/pages/bug-selector-escape/index.html` |
| **Tests** | `bug_lab/tests/test_bug_selector_escape.py` — 29 tests (18 unit + 11 browser), all pass |

---

## BUG: File Input — `set_input_files` vs `fill(fakepath)`

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes |
| **Fixed?** | Yes — commit `38d4966` |
| **How?** | Recorder now detects file inputs and generates `set_input_files()` instead of `fill()`. `fill()` with fake paths (e.g., `C:\fakepath\file.txt`) fails silently — `set_input_files()` correctly uploads the file. |
| **Page** | `bug_lab/pages/bug-file-input/index.html` |
| **Tests** | `bug_lab/tests/test_bug_file_input.py` — 262 lines, set_input_files vs fill |

---

## BUG: Empty/Invalid Selector

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes |
| **Fixed?** | Yes — commit `a8864c8` (part of FASE-04 work) |
| **How?** | Selector validation now rejects empty/invalid CSS selectors before they reach Playwright. Locator generation skips candidates with zero-length or malformed selectors. |
| **Page** | `bug_lab/pages/bug-empty-selector/index.html` |
| **Tests** | `bug_lab/tests/bug-empty-selector_test.py` — 65 lines, xfail patterns |

---

## BUG: Multi File Input — Identical/Ambiguous Selectors

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — confirmed via browser tests |
| **Fixed?** | Not yet — selector generation does not incorporate `type=file` for disambiguation |
| **How?** | N/A — bug documented, fix pending. Normalizer must add `input[type=file]` + disambiguating attribute (name/id/label) to candidate chain. InputAgent must use specific selector instead of bare `input[type=file]`. |
| **Page** | `bug_lab/pages/bug-multi-file-input/index.html` |
| **Tests** | `bug_lab/tests/test_bug_multi_file_input.py` — 31 tests (all `@slow` browser integration) — all pass |

---

## BUG: jQuery-Enhanced Select — select_option() Failure

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — confirmed via browser tests |
| **Fixed?** | Not yet — bug documented, fix pending |
| **How?** | Native `<select>` is hidden (`display:none`) by jQuery enhancement. Playwright's `select_option()` fails with visibility error. `force=True` sets value but jQuery UI does not update (event not triggered). Workaround: click jQuery custom DOM (trigger + `li[data-value]`). Fix requires InputAgent to detect hidden selects and generate interaction with custom DOM instead of `select_option()`. |
| **Page** | `bug_lab/pages/bug-jquery-select/index.html` |
| **Tests** | `bug_lab/tests/test_bug_jquery_select.py` — 22 tests (9 unit + 13 browser) — all pass |

---

## BUG: Datepicker — Operator Validation Bug

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — two bugs found |
| **Fixed?** | Yes — commits `9cb38cf` + fix commit (this change) |
| **How?** | Two bugs fixed: 1) Time-mismatch: `new Date()` includes wall-clock time so midnight < now → today always rejected. Fixed by normalizing both dates to midnight (`today.setHours(0,0,0,0)`). 2) Operator bug: `<=` rejected today (midnight <= midnight). Fixed by changing to `<`. |
| **Page** | `bug_lab/pages/bug-datepicker/index.html` |
| **Tests** | `bug_lab/tests/test_bug_datepicker.py` — 7 tests, all pass |

---

## BUG: UTF-8 Encoding — Special Characters Lost in Recording

| Field | Value |
|-------|-------|
| **Bug existed?** | Yes — encoding not validated end-to-end |
| **Fixed?** | **BUG CONFIRMED, NOT FIXED** — test page created, fix pending |
| **How?** | None yet. Test page validates that Playwright DOM reads UTF-8 correctly (charset, text, buttons, JSON round-trip). Fix will need UTF-8 guarantees at all pipeline layers: HTTP Content-Type, Python file I/O, JSON ensure_ascii=False, CSS selector escaping, regex patterns. |
| **Page** | `bug_lab/pages/bug-encoding/index.html` |
| **Tests** | `bug_lab/tests/test_bug_encoding.py` — 21 tests (all slow/browser), all pass — validates Spanish/Portuguese/German/French chars, symbols (€, ©, —, …), mojibake detection, button interaction with accented text, JSON round-trip, charset meta, lang attribute |

---

## Test Coverage Summary

```bash
# Unit tests (fast, no browser):
pytest bug_lab/tests/ -v -m "not slow"   # 35 tests

# Full suite (includes browser integration):
pytest bug_lab/tests/ -v                  # 120+ tests
pytest tests/ -v                          # 73+ tests
```

**Last validated:** 2026-06-17 — all 214+ tests pass (73 semantic + 141 bug_lab including 21 encoding), lint clean.
