# BUG: Dynamic Button ID — Selector Healing via Text Fallback

## Symptom
Playwright throws `strict mode violation: locator '#btn-dynamic-0' resolved to 0 elements`
when clicking a button whose `id` attribute changes dynamically after page load.
Simulates React/Angular hash-based IDs that invalidate recorded selectors.

**Error message:**
```
playwright._impl._errors.TimeoutError: locator.click: Timeout 30000ms exceeded.
...
strict mode violation: locator "#btn-dynamic-0" resolved to 0 elements
```

## Cause
Button ID rotates from `btn-dynamic-0` → `btn-dynamic-1` → `btn-dynamic-2` → ...
every 2 seconds (or 500ms with `?error=1`). Selector `#btn-dynamic-0` is stale
after the first rotation. Playwright strict mode requires exactly 1 element — finding
0 is a violation.

Root cause chain:
1. Dynamic ID generation (common in React/Angular with hash-based IDs)
2. Test recording captures concrete ID at record time
3. Replay uses stale ID → locator resolves to 0 elements
4. Strict mode violation → test fails

## Page Variants

| URL | Rotation Speed | Use Case |
|-----|---------------|----------|
| `index.html` | 2s (normal) | Matches real-world React/Angular |
| `index.html?error=1` | 500ms (fast) | Guaranteed failure, CI testing |

Two buttons: primary ("Clique Dinâmico") + secondary ("Ação Secundária").
Each has independent ID rotation intervals and distinct text fallback.

## Reproduction
```bash
# 1. Normal mode — stale after 3.5s wait
pytest bug_lab/tests/test_bug_dynamic_id.py::test_stale_id_click_reproduces_failure -v

# 2. Error mode — stale after 1.5s (fast rotation)
pytest bug_lab/tests/test_bug_dynamic_id.py::test_error_mode_stale_id_faster_failure -v

# 3. Run all dynamic ID tests (9 total)
pytest bug_lab/tests/test_bug_dynamic_id.py -v
```

**Manual reproduction:**
1. Load `bug_lab/pages/bug-dynamic-id/index.html?error=1`
2. Wait 1.5s → button ID has changed to `btn-dynamic-3` (or higher)
3. Try `page.locator("#btn-dynamic-0").click()` → **FAILS** with TimeoutError
4. Try `page.locator('text="Clique Dinâmico"').click()` → **SUCCEEDS**

## Fix
SelectorAgent._try_text() (`src/testforge/healing/agents/selector_agent.py:122`) produces
a `has_text_fallback` proposal converting the stale ID selector to an exact text selector:

```python
# Before (fails after ID rotation)
page.locator("#btn-dynamic-0").click()

# After healing (always works)
page.locator('text="Clique Dinâmico"').click()
```

**Healing pipeline:** L0 catalog check → L1 deterministic fallback → L2 SelectorAgent._try_text()
→ produces `text="Clique Dinâmico"` selector with confidence 0.70.

**Commits:**
- `d9b8f24` feat: add bug_lab entry for dynamic button ID with text fallback healing
- `ee795b5` fix: use exact text matching in SelectorAgent._try_text()
- `a8864c8` feat: FASE-04 — enhance dynamic ID page with error mode and secondary button
- `d95a018` test: FASE-04 — extend tests with error mode, multi-click, healing pipeline integration

## Validation
```bash
# Bug lab tests (9 tests)
pytest bug_lab/tests/test_bug_dynamic_id.py -v

# Curation tests (6 tests — healing pipeline integration)
pytest tests/test_pages/test_dynamic_id_healing.py -v

# Full suite
pytest bug_lab/ tests/ -v
```

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_stale_id_click_reproduces_failure` | Stale ID fails (normal mode) |
| `test_text_locator_clicks_succeeds` | Text fallback works (normal mode) |
| `test_initial_id_click_succeeds_before_rotation` | Initial ID valid before rotation |
| `test_error_mode_stale_id_faster_failure` | Stale ID fails (fast rotation) |
| `test_error_mode_text_fallback_still_works` | Both buttons via text fallback |
| `test_multi_click_tracking_via_text_fallback` | 3 clicks tracked via text |
| `test_two_buttons_distinct_text_fallback` | Distinct buttons, distinct text |
| `test_healing_pipeline_text_fallback_integration` | SelectorAgent._try_text() E2E |
| `test_classify_stale_id_error` | FailureClassifier → FAM-01, SEL-* |
