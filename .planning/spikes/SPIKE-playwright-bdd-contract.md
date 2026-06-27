# Spike — playwright-bdd contract compatibility with SemanticAction

**Date**: 2026-06-27
**Author**: Claude Code session
**Outcome**: see Verdict at bottom.

## Question

Can we adopt `playwright-bdd` (vitalets) as the compiler stage,
deleting our `semantic/compiler.py` (885 LOC) and inheriting native
multi-scenario emission + tags + parallelization?

## Method

Read playwright-bdd docs + GitHub + DeepWiki. Map our `SemanticAction`
(action / target.candidates[] / value / context / escalation) onto the
playwright-bdd step-definition contract.

## Findings

### Hard blocker: language mismatch

**playwright-bdd is JavaScript / TypeScript only.** No Python support.

Confirmed in:
- https://github.com/vitalets/playwright-bdd README (TS / JS / Gherkin
  source mix; no Python interpreter or runtime support).
- DeepWiki documentation: "JavaScript/TypeScript only — no Python
  support mentioned."

Our project is Python (pytest, Playwright Python bindings, FastAPI for
the dashboard, all healing pipeline in Python). Adopting playwright-bdd
means a full migration to TypeScript — at minimum: recorder, compiler,
runner, healing layers, taxonomy, telemetry. That is not in scope.

### Step-definition shape (for reference, in case we ever go TS)

```typescript
import { createBdd } from 'playwright-bdd';
const { Given, When, Then } = createBdd();

Given('I am on Playwright home page', async ({ page }) => {
  await page.goto('https://playwright.dev');
});
When('I click link {string}', async ({ page }, name) => {
  await page.getByRole('link', { name }).click();
});
```

Signature: `(fixtures, ...stepArgs) => void`. Step arguments are
extracted from Gherkin patterns as scalars (`{string}`, `{int}`).
DataTable + doc strings handle simple structured data.

**Complex objects** (like a `LocatorCandidate[]` array with score +
strategy + fallback chain) **cannot** ride a Gherkin step natively.
Workarounds: load from a side-channel JSON file keyed by step ID, or
wrap in a custom World fixture.

## Python alternative — `pytest-bdd`

The Python equivalent stack: `pytest-bdd` + `pytest-playwright`. Already
used by community for the same goal.

### Step-definition shape

```python
from pytest_bdd import given, when, then, parsers

@given("the user is on the home page")
def home_page(page):
    page.goto(BASE_URL)

@when(parsers.parse('the user fills "{field}" with "{value}"'))
def fill_field(page, field, value):
    page.locator(f'input[aria-label="{field}"]').fill(value)
```

Signature: `(fixtures, *parsed_args) => None`. Same constraint as
playwright-bdd: complex objects need a side channel.

### Adoption cost — Python path

Replacing our compiler with `pytest-bdd` is **not a clean delete**:

| Aspect | Today | With `pytest-bdd` |
|---|---|---|
| Multi-scenario emit (P-SEG) | Manual blob split | Native (Scenario: blocks) |
| Tags, hooks, parallelization | DIY in `incremental_runner` | Native (`@scenarios`, conftest) |
| Pytest integration | Hand-rolled | Native |
| Locator candidate list | `SemanticAction.target.candidates[]` inline | Side-channel JSON loaded by step fn |
| Healing escalation L0→L3 | Wired into compiler output | Wired into step fn body |
| Compiler LOC saved | — | ~400 LOC (rough) |
| New code needed | — | Gherkin emitter + step-fn loader + side-channel JSON spec |

**Net LOC: probably similar.** What we save in the compiler we pay back
in the emitter + side-channel adapter.

What we DO gain:

- P-SEG (6-scenarios-in-1) solved by native multi-`Scenario:` blocks.
- Tag-driven scenario selection (`@critical`, `@smoke`).
- Pytest-native parallelization (`pytest-xdist`).
- Business-readable artefact (`.feature`) that matches the user's stated
  preference for simple Gherkin BDD.
- Future scenario reuse across recordings via `@Scenario reuse` patterns
  documented in `pytest-bdd`.

What we DO NOT gain:

- Selector self-healing (that lives in our `LocatorResolver`, unchanged).
- LLM healing (lives in `healing/llm_healer.py`, unchanged).
- Telemetry spans (lives in `metrics/telemetry.py`, unchanged).

## Comparison with our current compiler

Our `semantic/compiler.py` does the following in 885 LOC:

1. Read SemanticTestCase → emit a `test_st_<name>.py` script.
2. Per step, generate a `_sels = [...]` list (the candidate selectors).
3. Wrap in a `for _sel in _sels: try ... break` loop (this is our
   L0.5 in-script fallback).
4. Emit `page.wait_for_timeout(...)` per action kind (SPA navigation,
   DOM render, etc).
5. Emit `page.fill / click / etc` calls.
6. Emit a `field_value_map` JSON load + `field_map:` selector
   syntax for fills.
7. Emit final `expect(...)` assertions.

If we adopt pytest-bdd, items (2)-(6) move into a small step-definition
library (call it `testforge.bdd.steps`), and the recorder emits a
`.feature` file pointing at those generic steps. The script-per-test
shape goes away. The library is ~150 LOC of step functions.

**Realistic deletion**: 600-700 LOC of compiler.py → ~150 LOC of step
library + ~100 LOC of Gherkin emitter + side-channel candidates loader.
Net: **-400 LOC, +1 well-known dependency (`pytest-bdd`)**.

## Verdict

**Not playwright-bdd. Consider `pytest-bdd` later.**

1. playwright-bdd is JS/TS only. Hard no without language migration.
2. `pytest-bdd` is the right comparable in Python. Adoption is a real
   refactor (not a clean delete) but the P-SEG win is structural and
   the .feature artefact aligns with user goal.
3. The adoption refactor is mid-sized (~3-5 days). Not on the critical
   path while the recorder still has unresolved blockers (P-INL, P-MID,
   P-SHA).
4. **Order of operations**: fix the recorder first (close the
   P-INL/P-MID/P-SHA gaps), then evaluate `pytest-bdd` adoption with a
   stable baseline. Adopting BDD on top of a broken recorder will hide
   recorder bugs in unfamiliar plumbing.

## Tracking tickets

- **H23** — Evaluate `pytest-bdd` + `pytest-playwright` for compiler
  stage. Prereq: P-INL, P-MID, P-SHA resolved on current architecture.
  Estimate 3-5 days.
- **H24** — If H23 lands, emit Gherkin from the recorder. Today's
  `gherkin_writer.py` is auto-derived prose; needs upgrade to proper
  `Scenario:` / `Given/When/Then` blocks keyed off the (still
  hypothetical) `Shift+N` scenario boundaries.

## What we did NOT verify

- pytest-bdd's DataTable handling for our side-channel candidate JSON
  pattern. The DataTable API is documented less than the basic step
  parsing. **TODO-deep**: write a 30-line proof-of-concept that feeds a
  candidates JSON into a `@when` step via a fixture, before committing
  to H23.
- pytest-bdd's parallel-scenario isolation under shared browser
  fixtures. Some users report flakiness when scenarios share the
  Playwright `page` fixture. Needs a smoke test.

## Sources

- https://github.com/vitalets/playwright-bdd
- https://vitalets.github.io/playwright-bdd/
- https://deepwiki.com/vitalets/playwright-bdd/4.2-step-definitions
- https://dev.to/abbazs/implementing-bdd-with-pytest-bdd-and-pytest-playwright-for-web-testing-9fj
- https://www.inexture.com/bdd-automation-framework-playwright-pytest/
- https://github.com/cmoir/playwright_pytest_bdd_example
