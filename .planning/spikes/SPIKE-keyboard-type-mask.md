# Spike — `page.keyboard.type()` vs setter-hook capture on currency mask

**Date**: 2026-06-27
**Author**: Claude Code session
**Outcome**: see Verdict at bottom.

## Question

If we record fills using `page.keyboard.type()` instead of intercepting the
`HTMLInputElement.prototype.value` setter, does the masked field arrive at the
correct value naturally? If yes, we can delete:

- `_hookValue` overlay JS hook
- `value_mutations.jsonl` writer + reader
- `IntentReconstructor.setter_hook` recovery
- `_fill_masked` digit-strip strategy
- ~600 LOC across 5 modules

## Method

Use `tests/intent_lab/pages/currency-mask/index.html` as a representative
Brazilian currency mask:

```html
<input id="valor" placeholder="0,00">
<script>
  document.getElementById('valor').addEventListener('input', function(e) {
    var raw = this.value.replace(/\D/g, '');
    if (raw.length === 0) { this.value = ''; return; }
    var num = parseInt(raw) / 100;
    this.value = num.toLocaleString('pt-BR', {minimumFractionDigits: 2});
  });
</script>
```

Same shape as SIOPI: listens for `input` event, rewrites `this.value` after
each keystroke.

Three Playwright probes, same fixture:

| Probe | API | Expected before run |
|-------|-----|---------------------|
| A | `page.fill('#valor', '1000')` | unknown — fill() bypasses keyboard |
| B | `page.locator('#valor').press_sequentially('1000', delay=10)` | should trigger mask (this is how our `_fill_masked` already works) |
| C | `page.keyboard.type('1000')` after click | should trigger mask (key events) |

Inspect `document.getElementById('valor').value` after each.

## Implementation

```python
# tests/test_pages/spikes/test_keyboard_type_mask.py
from playwright.sync_api import sync_playwright
from pathlib import Path

PAGE = Path("tests/intent_lab/pages/currency-mask/index.html").absolute().as_uri()

def probe(api: str) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(PAGE)
        loc = page.locator("#valor")
        if api == "fill":
            loc.fill("1000")
        elif api == "press_sequentially":
            loc.click()
            loc.press_sequentially("1000", delay=10)
        elif api == "keyboard.type":
            loc.click()
            page.keyboard.type("1000")
        value = page.evaluate("document.getElementById('valor').value")
        browser.close()
        return value

if __name__ == "__main__":
    for api in ("fill", "press_sequentially", "keyboard.type"):
        print(f"{api:>20s}: {probe(api)!r}")
```

## Results

Test artifact: `tests/test_pages/spikes/test_keyboard_type_mask.py`.
Ran `pytest -v -s` headless, Chromium, 2026-06-27.

```
fill                  → '10,00'
press_sequentially    → '10,00'
keyboard.type         → '10,00'
```

### Interpretation

All three APIs produce the mask-formatted value `'10,00'` on this fixture.
This contradicted my pre-spike guess that `fill()` would bypass the mask.

Why `fill()` worked here: the mask listener uses
`addEventListener('input', ...)`. Playwright's `fill()` dispatches an `input`
event programmatically after the setter write, so the listener fires, sees
`'1000'`, and reformats to `'10,00'`. The mask's `replace(/\D/g, '')` is
permissive — it accepts any digit stream, formatted or raw.

This fixture is **not representative of the real failure mode**. SIOPI's
Angular Material `currencymask` directive does extra work:
- intercepts the `input` event before bubbling (`stopPropagation`)
- writes its own formatted value back through the setter
- forces Angular change detection with `NgZone.run`
- some variants suppress `input` events entirely during typing

The hotfix history points specifically at that path (hotfix 16, 17, 19,
22). The vanilla JS mask in `tests/intent_lab/pages/currency-mask/` is too
permissive to surface those bugs.

## Implication for the recorder

`keyboard.type()` and `press_sequentially()` produce the same DOM-visible
result. So the question becomes:

> If we record the user typing as a sequence of `keydown`/`keypress`/`input`
> events (which Playwright already exposes), can the recorder reconstruct the
> typed value without intercepting the `value` setter?

The answer is yes — but **we already need the setter hook for one specific
case**: SIOPI's Material currency input swallows the `input` event during
mask processing (the mask sets `this.value` synchronously and React/Angular
suppresses the bubble). The setter hook was added because the keystroke
stream alone gave us the raw digits but never the formatted display value
the user actually saw.

So the trade is:

| Approach | What we capture | What we lose |
|----------|-----------------|--------------|
| Setter hook (today) | Final formatted value | 600 LOC, 4 hotfixes of drift |
| Keystroke stream only | Raw digits typed | Need separate path to read final display value back |
| Keystroke + final-state snapshot | Both | Slightly higher cost, single source of truth |

**Verdict** is in the next section.

## Verdict

**Inconclusive on the production blocker.**

On the vanilla currency-mask fixture, all three APIs produce the masked
formatted value. The replacement plan (`keyboard.type()` instead of setter
hook) is structurally sound for *that* class of mask. But this fixture is
not where our pain lives — the hotfix history specifically targets Angular
Material's `currencymask` directive behaviour, which is not reproduced
here.

So this spike does NOT yet justify deleting `_hookValue` and the setter
hook pipeline. To complete the spike we need a closer fixture:

1. **Option A**: stand up a real Angular Material currencymask sample
   page (npm install @angular/material + ng2-currency-mask). 2-3 hours of
   setup but produces a high-fidelity probe.
2. **Option B**: capture a snapshot of the SIOPI calculator page (HTML +
   `currencymask` directive source) as a local fixture. Same effect, no
   npm install. ~1 hour.
3. **Option C**: instrument the existing real SIOPI run; compare DOM
   value after `keyboard.type` vs current setter-hook path. Requires
   running against the live intranet.

Recommendation: **Option B**, because it can be committed to the repo as
a deterministic fixture and reused for every future Material mask
regression. Track as `H22 — Angular Material currencymask fixture`.

What stays decided:

- The vanilla-mask result removes one historical worry: `fill()` is not
  inherently wrong for masked inputs that use a permissive `input`
  listener. The hotfix history was right about the specific Material
  directive case but wrong if generalised.
- `press_sequentially` and `keyboard.type` are interchangeable at the
  Playwright dispatch layer.
- Once Option B fixture exists, this spike has a definitive answer.

## What we did NOT verify

- Angular Material `mat-input` + `currencymask` directive behaviour
  (the actual production failure mode).
- Paste, IME composition, autocomplete pre-fill — keystroke stream
  coverage gaps.

Both block any code deletion. Do not delete `_hookValue` until Option B
runs.
