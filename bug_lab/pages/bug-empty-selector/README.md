# BUG: Empty/Invalid Selector — Playwright Resolves to Zero Elements

## Symptom
Playwright throws `TimeoutError` or `strict mode violation` when attempting to interact
with a locator that matches zero elements in the DOM.

**Error message:**
```
playwright._impl._errors.TimeoutError: locator.click: Timeout 30000ms exceeded.
...
strict mode violation: locator "#saveButton" resolved to 0 elements
```

## Cause
CSS selector `#saveButton` (camelCase) does not match any element on the page.
Page only has `id="save-btn"` (kebab-case). Common causes:

1. **Selector typo** — naming mismatch (e.g. `#saveButton` vs `#save-btn`)
2. **Element not yet rendered** — DOM not populated when locator resolves
3. **Wrong page/route loaded** — replay on incorrect URL
4. **Dynamic ID changed** — hash-based ID between recordings (see also BUG-dynamic-id)

Playwright strict mode requires exactly 1 match. Finding 0 is a violation.

## Reproduction
```bash
# 1. Start test server
cd bug_lab/pages && python -m http.server 8700

# 2. Run xfail test — confirms bug exists
pytest bug_lab/tests/bug-empty-selector_test.py::test_empty_selector_reproduces_failure -v

# 3. Run correct selector test — shows workaround
pytest bug_lab/tests/bug-empty-selector_test.py::test_correct_selector_works -v

# 4. Run all
pytest bug_lab/tests/bug-empty-selector_test.py -v
```

**Manual reproduction:**
1. Load `bug_lab/pages/bug-empty-selector/index.html`
2. Try `page.locator("#saveButton").click()` → **FAILS** with TimeoutError
3. Try `page.locator("#save-btn").click()` → **SUCCEEDS**

## Fix
**NOT YET FIXED** — bug documented, xfail test confirms exists.

Potential fix approaches:
1. **Selector validation**: Validate selectors before passing to Playwright — reject empty/invalid CSS selectors and provide clear error messaging.
2. **Self-healing fallback**: When locator resolves to 0 elements, the SelectorAgent should detect the empty match and fall back to alternative selectors (data-testid, text content, aria-label, etc.).
3. **N-gram normalization**: During recording normalization, normalize camelCase ↔ kebab-case variants of IDs and names to prevent typo-mismatches.

## Commits
- `07d64ba` test: add bug-empty-selector reproduction page and xfail test

## Validation
```bash
# Bug lab tests (2 tests: 1 xfail, 1 pass)
pytest bug_lab/tests/bug-empty-selector_test.py -v

# Full suite
pytest bug_lab/ tests/ -v
```

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_empty_selector_reproduces_failure` (xfail) | Wrong selector `#saveButton` throws TimeoutError |
| `test_correct_selector_works` | Correct selector `#save-btn` finds element and click succeeds |
