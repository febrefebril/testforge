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
every 2 seconds. Selector `#btn-dynamic-0` is stale after the first rotation.
Playwright strict mode requires exactly 1 element — finding 0 is a violation.

Root cause chain:
1. Dynamic ID generation (common in React/Angular with hash-based IDs)
2. Test recording captures concrete ID at record time
3. Replay uses stale ID → locator resolves to 0 elements
4. Strict mode violation → test fails

## Reproduction
```bash
# 1. Load the reproduction page
# Page: bug_lab/pages/bug-dynamic-id/index.html

# 2. Run the failure test
pytest bug_lab/tests/test_bug_dynamic_id.py::test_stale_id_click_reproduces_failure -v

# 3. Observe: Playwright TimeoutError — "#btn-dynamic-0" resolves to 0 elements
```

**Steps:**
1. Load page → button has id="btn-dynamic-0"
2. Wait 3.5s → button now has id="btn-dynamic-2" (ID changed twice)
3. Try `page.locator("#btn-dynamic-0").click()` → **FAILS** with TimeoutError

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

**Commit:** `d9b8f24 feat: add dynamic button ID test page and text fallback healing tests`
**Commit:** `ee795b5 fix: use exact text matching in SelectorAgent._try_text()`

## Validation
```bash
# Run reproduction + fix tests
pytest bug_lab/tests/test_bug_dynamic_id.py -v

# Run full healing test suite
pytest tests/test_pages/test_dynamic_id_healing.py -v

# Run full suite
pytest bug_lab/ tests/ -v
```
