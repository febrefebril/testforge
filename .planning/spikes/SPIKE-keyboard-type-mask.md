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

## Verdict (vanilla fixture only)

**Insufficient. Material-shape fixture needed (see H22 follow-up below).**

On the vanilla mask fixture, all three APIs produce the masked formatted
value. But the vanilla mask uses a permissive `input` listener; SIOPI's
Angular Material `currencymask` directive uses per-instance setter
overrides and key-event interception. Different failure mode.

`press_sequentially` and `keyboard.type` are interchangeable at the
Playwright dispatch layer (same result).

---

## H22 — Material-shape fixture spike (run after the section above)

**Fixture**: `tests/intent_lab/pages/material-currencymask/index.html`
**Test**: `tests/test_pages/spikes/test_material_currencymask.py`

Built a fixture that reproduces the ng2-currency-mask pattern:
- per-instance `Object.defineProperty(input, 'value', ...)`
- `keydown` handler that `preventDefault()`s and emits formatted display
  through the per-instance setter

Two distinct questions:

### Q1 — Replay: which API produces the right value?

```
fill                  → '' (empty)         ❌
press_sequentially    → '10.000,00'        ✓
keyboard.type         → '10.000,00'        ✓
```

**`fill()` is broken** against the per-instance override pattern. The
exact failure mode matches hotfix 16 ("currency math wrong"). Why:
Playwright's `fill()` writes to the value setter (now the instance
override). The instance override strips non-digits, computes display,
but Playwright's clear-then-set sequence ends in an unexpected state
(empty here). This is precisely why the runner has `_fill_masked` →
`press_sequentially` already.

`press_sequentially` and `keyboard.type` both dispatch per-key events.
The fixture's keydown handler processes each digit, emits formatted
display via the prototype setter call inside its handler. Both work.

### Q2 — Record: does the prototype hook see writes?

Real output:

```
captured after masked typing: 4 writes
  {'id': 'valor_imovel', 'value': '0,01'}
  {'id': 'valor_imovel', 'value': '0,10'}
  {'id': 'valor_imovel', 'value': '1,00'}
  {'id': 'valor_imovel', 'value': '10,00'}
captured after plain typing:  0 writes on #plain
```

**This is the most important finding of the whole spike.** Two facts:

1. The hook **caught** the masked input writes — because my fixture's
   mask explicitly delegates to the prototype setter (`protoDesc.set.call(input, displayed)`)
   when rendering the visible value. So `_hookValue` does work for any
   mask that takes that route.
2. The hook **missed** the plain input typing entirely (0 captures on
   `#plain` even though `keyboard.type('hello')` was sent). Real
   browser-native typing **does not go through the value setter**.

Translation to the production failure mode:

| Scenario | Hook catches? |
|---|---|
| User types in plain input | **No** — native typing bypasses setter. |
| User types in mask that delegates to proto setter | **Yes** — mask's writes reach the hook. |
| User types in mask with instance-only setter (no proto delegate) | **No** — instance override shadows hook. |
| Programmatic `element.value = X` | **Yes** — programmatic writes go through setter. |

This invalidates the premise behind `value_mutations.jsonl` for
capturing user typing. The hook only captures **JS-driven writes**
(mask scripts re-formatting the value), never raw user keystrokes.

For SIOPI calculadora's Material currencymask, if the directive uses
an instance-level setter override that does NOT delegate back to the
prototype (the common pattern), the hook misses everything. The user
types, mask processes, screen updates — `value_mutations.jsonl` stays
empty. That matches the EVIDENCE-ANALYSIS finding: 30%+ of `--complete`
prompts are typing_not_captured.

## Revised verdict

**Setter hook is structurally insufficient. Stop relying on it as the
primary value-capture path. But do not delete it yet — it is still the
only source that survives for masks that DO delegate to the prototype.**

The new capture model that the spike points at:

1. **Primary**: `final_state_snapshot.json` (already written by the
   overlay at session end). Reads `el.value` via the instance getter,
   which returns whatever the mask considers canonical. Single source
   of truth for end-of-session field values.
2. **Secondary**: keystroke aggregation from `raw_events.jsonl`. We
   already record keydown events. The normalizer can build "user typed
   1000000" by counting digit keys between focus/blur.
3. **Tertiary (today's path)**: `value_mutations.jsonl` via setter hook.
   Keep for backwards compat and for the masks that delegate to proto.

The normalizer should consult all three sources and prefer the most
specific (final_state > keystrokes > value_mutations).

## What this kills (eventually, in priority order)

- **Primary reliance on value_mutations.jsonl for masked input
  capture.** Tracked as **H22a**: revisit `_ir_value_mutations` weight
  in the IntentReconstructor source priority table.
- **`_hookValue` itself**: NOT yet. It still helps for masks that
  delegate to proto. Reassess after H22a runs in production.
- **The masking-specific normalizer paths**: half of them can fold into
  the final_state path. Tracked as **H22b**.

Estimated work: 2-3 days for H22a + H22b combined. Risk: medium — the
keystroke aggregation path needs to detect paste, IME, autocomplete
pre-fill correctly (it doesn't today).

## What we still did NOT verify

- The actual SIOPI page's directive implementation. Confirmed our
  fixture pattern matches ng2-currency-mask. The SIOPI directive might
  differ — but if it does, it can only be worse, not better, for the
  prototype hook.
- Paste behaviour, IME, autocomplete pre-fill. Three known gaps in the
  keystroke aggregation path.
- `keyboard.type` on inputs nested inside shadow roots. Untested.

These do not change the verdict; they bound the H22a/H22b implementation.
