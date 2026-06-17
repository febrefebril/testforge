# BUG: jQuery-Enhanced Select — select_option() Failure

## Symptom

Playwright recorder captures user selecting option from jQuery-enhanced
dropdown and generates `select_option()` against the hidden native
`<select>`. The `select_option()` call may fail or silently do nothing
because the native `<select>` has `display: none`.

Example recording output:
```python
page.get_by_label("Choose a fruit").select_option("apple")  # may fail
page.locator("#fruit-select").select_option("banana")        # may fail
```

Error seen:
```
playwright._impl._errors.Error: Select element is not visible
```

Or no error but the selection event (`change`) is not triggered
because jQuery enhancement does not always wire up event bubbling
from `select_option()`.

## Cause

jQuery plugins (Select2, Chosen, custom) hide the native `<select>`
and build a custom DOM structure with `<div>`, `<ul>`, `<li>` elements.
Playwright's `select_option()` targets the hidden native select.

Two issues:
1. **Visibility check**: Playwright may refuse to interact with
   hidden elements unless `force=True` is used.
2. **Event propagation**: `select_option()` sets the value programmatically
   but jQuery plugins often listen for `click` events on custom DOM,
   not `change` on the hidden select — so the value changes but the
   jQuery UI does not update and the application code never runs.

## Reproduction

```bash
# Start test server
cd bug_lab/pages && python -m http.server 8700

# Open browser
open http://localhost:8700/bug-jquery-select/index.html

# Try Playwright:
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:8700/bug-jquery-select/index.html")

    # This may fail — native select is display:none
    page.locator("#fruit-select").select_option("apple")

    # Workaround: force override visibility check
    page.locator("#fruit-select").select_option("banana", force=True)
    # But this only sets the value — the jQuery UI won't update

    # Proper fix: interact with the jQuery custom DOM instead
    page.locator(".jq-select-trigger").click()
    page.locator('.jq-select-dropdown li[data-value="cherry"]').click()
```

## Validation

```bash
pytest bug_lab/tests/test_bug_jquery_select.py -v
```

## Fix Strategy

1. Detect that the original selector is a hidden `<select>` with
   a jQuery-enhanced UI wrapper
2. Instead of `select_option()`, generate interaction code that:
   - Clicks the dropdown trigger (custom element)
   - Clicks the desired option in the custom dropdown
3. Or use `select_option(force=True)` if the jQuery plugin correctly
   handles `change` events from the hidden select
