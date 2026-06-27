# Market Scan — first pass

**Date**: 2026-06-27
**Reason**: user-requested process change. Before any architectural decision, scan how
mainstream tools solve the same problem. Pick library/pattern over rebuild.

> This is a first pass. Each row marked **TODO-deep** needs a second drill (read the
> tool's docs/code, run the recorder, compare on a SIOPI fixture). Do not promote a
> "match" to a decision until the deep dive runs.

---

## Problem catalog

The 5 root causes we identified for "0 of 11 recordings ran end-to-end":

| ID | Problem | Origin |
|---|---|---|
| P-SEG | 1 recording = N test scenarios (test-pos-hotfix8: 78 raw steps = 6 paths) | session 2026-06-27 |
| P-INL | Masked input values lost; user prompted only at end via `--complete` | recurring across SIOPI |
| P-VER | No record-time verification that the just-captured selectors will replay | `run-incremental` is a workaround |
| P-MID | Multi-instance same-shape fields (5 mat-input dates) have no stable identity | SIOPI calculadora |
| P-SHA | Shadow DOM detected but no resolution path (closed shadow roots in SIPBS) | evidence analysis B14 |

Plus 1 emission concern:

| ID | Problem | Origin |
|---|---|---|
| P-BDD | Gherkin emission today is auto-derived prose; not parseable into Cucumber-grade scenarios | gherkin_writer.py |

---

## Tool-by-tool

### Playwright (codegen + built-ins)

| Capability | Status |
|---|---|
| P-SEG | **No** — codegen records one script per session. No scenario boundary primitive. |
| P-INL | Partial — `page.pause()` opens codegen-controls window; manual gesture, not auto-triggered. |
| P-VER | **No** — codegen does not verify the emitted selectors against the live DOM. |
| P-MID | **No** — best-effort role/label/text priority chain (matches our v2 LocatorExtractor scoring). |
| P-SHA | **Yes** — automatic shadow DOM piercing, deep combinators (`>>>`). This is industry-leading. |
| P-BDD | **No** — emits raw Playwright; no Gherkin. |

**Takeaway**: Playwright's shadow DOM piercing is something we should rely on instead of
hand-rolling. The fix for P-SHA is in our `_extractTarget` (overlay JS) — make sure the
selectors we emit *use* Playwright's deep combinators when the recorded element is inside a
shadow root, instead of capturing a CSS path that stops at the shadow boundary.

### playwright-bdd (Vitalets)

| Capability | Status |
|---|---|
| P-SEG | **Yes** at execution time — N scenarios in 1 feature file → N native Playwright tests. |
| P-INL | n/a (not a recorder). |
| P-VER | n/a. |
| P-MID | n/a. |
| P-SHA | n/a (delegates to Playwright). |
| P-BDD | **Yes** — converts `.feature` files to native Playwright tests. Scoped step definitions, reusable step functions, decorators. |

**Takeaway**: this is the most important find. If our recorder emits a `.feature` file with
N scenarios + step definitions, **playwright-bdd takes over** and we delete our entire
`semantic/compiler.py` stage. Reduces our code surface significantly. **TODO-deep**: read
playwright-bdd source to confirm the step-definition contract is compatible with our
SemanticAction shape (`action / target / value / context`). If yes, this is a big refactor
target.

### Mabl

| Capability | Status |
|---|---|
| P-SEG | Suite-level scenarios (one record per scenario). No mid-session boundary. |
| P-INL | n/a (proprietary, no public docs found on mask handling). |
| P-VER | **Yes** — "Trainer" verifies selectors at record time and adds extra find strategies. |
| P-MID | Multi-signal scoring (attributes + visual + DOM position + surrounding structure). |
| P-SHA | **Yes** — records a "shadow parent" attribute and adds an extra find strategy specifically for shadow root descent. |
| P-BDD | No (proprietary low-code). |

**Takeaway**: two transferable patterns. (1) The "shadow parent" idea — at record time,
walk up from the target; if any ancestor is a shadow root, record that node's selector as
a `shadow_parent` field on the candidate. Resolver tries `parent.locator('...').first` as a
strategy. (2) Multi-signal scoring at record time confirms the locator before saving. We
already do (2) via `LocatorExtractor`; H17 just fixed the perf of (1) being run too
aggressively. **TODO-deep**: instrument our overlay JS to detect shadow root walks during
`_extractTarget`.

### Cypress Studio

| Capability | Status |
|---|---|
| P-SEG | **No** — one test per session. |
| P-INL | Pause/resume via Record button toggle. Manual. Sensitive fields (password, CC) are auto-excluded but not re-prompted. |
| P-VER | **No** — replay is a separate step. |
| P-MID | n/a. |
| P-SHA | **Not supported** (documented limitation). |
| P-BDD | No (emits `cy.*` commands). |

**Takeaway**: Cypress's defence is "use real keyboard simulation, not JS injection." That
sidesteps mask interception entirely — the field's onInput/onChange fires naturally and the
recorded value reflects what the user typed. We should test whether Playwright's
`page.keyboard.type()` (which dispatches OS-level KeyboardEvent) does the same. If yes,
**P-INL might dissolve**: we replace setter hooks with keyboard.type() during recording,
and the typed value reaches the masked field naturally. **TODO-deep**: prototype a recorder
that uses `page.keyboard.type()` for fill steps on SIOPI calculadora's currency input.

### Stagehand (Browserbase)

| Capability | Status |
|---|---|
| P-SEG | n/a (programmatic SDK, not a recorder). |
| P-INL | n/a. |
| P-VER | Session replay via Browserbase platform; not record-time. |
| P-MID | LLM disambiguates at runtime via `observe()`. |
| P-SHA | Delegates to Playwright. |
| P-BDD | No. |

**Takeaway**: Stagehand explicitly markets "we preserve intent through CDP commands." This
matches our architectural premise. They solve it by **not capturing CDP-level events at
all** — the test is written in natural language, and the LLM resolves intent at runtime.
This is the opposite direction from our recorder. We could borrow `observe()` as an L2.5
healing strategy: when locators fail, ask the LLM "find the element matching this intent."
**TODO-deep**: read Stagehand's `observe()` source; estimate cost per call (Stagehand bills
this). Our L3 LLM healer already does something similar but only on failure.

### Cypress / BugBug / Selenium IDE (recorder family)

| Capability | Status |
|---|---|
| P-SEG | Multi-test recording: TestCase Studio (premium feature, mechanics undocumented). Selenium IDE has `run` command for test reuse across suites but not for splitting one recording. |
| P-INL | BugBug + Cypress use real keyboard simulation. Selenium IDE captures DOM-level events. |
| P-VER | None native. Reflect.run replays in cloud post-record. |
| P-MID | Selenium IDE: weak. BugBug: visual matching as fallback. |
| P-SHA | Selenium IDE: workaround via `executeScript`. BugBug: limited. |
| P-BDD | TestRail: post-hoc mapping. Selenium IDE: no. |

**Takeaway**: nobody in this tier solves scenario segmentation in-session. Our `Shift+N`
primitive is novel territory. If it works, it is differentiating.

### Karate (UI)

| Capability | Status |
|---|---|
| P-SEG | **Yes** — Karate's Gherkin-first model lets one feature file hold many scenarios. Scenarios are first-class. |
| P-INL | Karate supports inline data tables in feature files. |
| P-VER | Has its own driver layer; CDP and Playwright integration. No record-time verification. |
| P-MID | n/a. |
| P-SHA | Via Playwright integration. |
| P-BDD | **Native** — Karate is Gherkin syntax for the test itself. |

**Takeaway**: Karate's "Gherkin is the test, not a wrapper" inverts the relationship.
Worth considering as a long-term simplification but it would mean rewriting the runner
stage in a JVM-friendly path or finding the Python equivalent.

---

## Cross-cutting findings

### Two-pass record/replay is an established pattern

Academic + industry record-replay frameworks use it: a fast probe replays incrementally to
catch deviations early, and a detailed replayer runs on demand for forensic detail. Our
`run` vs `run-incremental` split maps directly onto this pattern. **Decision**: keep the
split. It is not over-engineering, it is the well-known shape.

What we should adjust: the **default action** should be `run-incremental` for first runs
(catch divergence at the source) and `run` for re-runs against the same environment.
Today the CLI gives them equal weight; users pick `run` and hit the same bugs `run-incremental`
would have caught. **TODO**: change CLI to suggest `run-incremental` for first execution.

### Real keyboard simulation > setter hooks

Cypress, BugBug, Reflect all use real keyboard events, not JS value injection. This
sidesteps three of our worst bug classes: masked input capture failure, Angular zone
mutation, MutationObserver missing setter sets. **The single highest-leverage change
identified in this scan**: prototype real keyboard recording for fill steps.

If real keyboard works on SIOPI currency input, we deprecate:
- `value_mutations.jsonl` (entire writer + reader)
- `_hookValue` overlay hook
- IntentReconstructor setter_hook recovery
- 30%+ of the `--complete` retroactive prompt cases

This alone could collapse three pattern recurrences (P3, P1 in REGRESSION-PATTERNS).

### BDD/Gherkin emission is solved by playwright-bdd

Our `gherkin_writer.py` auto-derives prose. It is not consumed downstream. If the recorder
emits proper Gherkin `Scenario:` / `Given/When/Then` blocks keyed to the scenario boundaries
the user marks, `playwright-bdd` becomes our compiler stage. We delete our compiler. The
test author reads `.feature` files (business-readable, BDD goal) and `playwright-bdd`
generates and runs Playwright tests.

This aligns with the user's stated goal of "simple Gherkin BDD." TODO-deep: confirm
playwright-bdd's step-definition contract.

### Shadow DOM is a recorder bug, not a runner bug

Playwright already pierces shadow DOM. Our recorder's `_extractTarget` likely captures a
CSS path that stops at the shadow boundary. Fix is small (overlay JS), high-impact (B14,
B17 evidence).

### Multi-instance field identity has no off-the-shelf solution

Mabl uses multi-signal scoring at record time and runtime visual matching. Stagehand uses
LLM observe(). Neither is a drop-in library. We need our own fingerprint that combines:
- preceding sibling text (the visible label "Data de nascimento" left of the input)
- position in form (form index + field index)
- nearby static labels (parent fieldset legend)

This is original work. Estimated 1-2 days, contained in the normalizer + extractor.

### `run-incremental` is the right architecture (with one change)

It exists to isolate the 4 hypotheses (recording / compiler / runner / generated script)
in a clean room. The two-pass pattern from academic record/replay frameworks confirms the
shape. Keep it. Change: make it the default for the first execution after recording, not
a sibling command at equal weight.

---

## Decisions emitted from this scan

These are candidates, not commitments. Each needs the deep-dive marked TODO-deep.

| Decision candidate | If adopted, kills | Replaces | Cost |
|---|---|---|---|
| Adopt `playwright-bdd` as compiler stage | semantic/compiler.py, semantic_tests/ format | 1 module deletion + Gherkin emitter rewrite | 3-5 days |
| Replace setter hooks with `keyboard.type()` for fill | value_mutations.jsonl, _hookValue, IntentReconstructor setter recovery | overlay_inject.js fill capture | 2-3 days |
| Record shadow_parent in candidates (Mabl pattern) | B14/B17 shadow blind spots | LocatorExtractor + resolver `shadow_parent` strategy | 1-2 days |
| Multi-signal field fingerprint (Mabl-pattern, original) | P-MID confusion among same-shape inputs | normalizer field_key derivation | 1-2 days |
| `Shift+N` scenario boundary + `.feature` emission | linear blob, 0/6 verdict cascade | overlay_inject.js + recording_normalizer | 1-2 days |
| Make `run-incremental` the default first-run | "I picked wrong command and missed the bug" | cli/app.py UX | 2 hours |
| Stagehand-style `observe()` as L2.5 healing | brittle CSS path fallback | new healing layer between L2 and L3 | 2-3 days |

---

## What this scan did NOT verify (open questions for deep-dive)

1. Does `playwright-bdd` step-definition shape accept a `SemanticAction`-like contract?
2. Does Playwright's `page.keyboard.type()` actually trigger Angular Material currency
   mask events as a real keyboard would, or does the mask still intercept?
3. Does Mabl's `shadow_parent` survive a partial DOM swap (the case our healing has to
   handle)?
4. How expensive is Stagehand's `observe()` per call? Acceptable as an L2.5?
5. Is there an open-source equivalent of TestCase Studio's "Multi Test Case Recording"
   we missed?

Next deep-dive should target items 1 and 2 first — they have the largest blast radius
in our codebase.

---

## Sources

Tool docs / blog posts referenced during this scan:

- Playwright codegen: https://playwright.dev/docs/codegen
- Playwright shadow DOM: https://www.desplega.ai/blog/2026-01-12-deep-dive-shadow-dom-testing
- playwright-bdd: https://github.com/vitalets/playwright-bdd
- Mabl shadow DOM: https://help.mabl.com/hc/en-us/articles/19078157363348-Testing-in-the-shadow-DOM
- Mabl auto-heal: https://help.mabl.com/hc/en-us/articles/19078583792404-How-auto-heal-works
- Stagehand: https://stagehand.dev/
- Stagehand intent capture: https://www.browserbase.com/stagehand
- Cypress Studio: https://docs.cypress.io/app/guides/cypress-studio
- Selenium IDE: https://www.selenium.dev/selenium-ide/
- BugBug recorders survey: https://bugbug.io/blog/test-automation-tools/web-test-recorders/
- Karate UI: https://docs.karatelabs.io/extensions/ui-testing/
- TestCase Studio: https://selectorshub.com/testcase-studio/
- TestEvolve BDD recorder: https://www.testevolve.com/record-your-automated-web-tests
- Self-healing tooling roundup: https://www.shiplight.ai/blog/best-self-healing-test-automation-tools
- Record/replay academic context: https://hackernoon.com/record-replay-strategy-for-testing-event-driven-architecture
