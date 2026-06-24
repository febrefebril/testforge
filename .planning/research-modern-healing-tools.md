# State-of-the-Art Web-Test Recording & Self-Healing (2024-2026)

Reference brief for criticizing TestForge's architecture (Python + Playwright recorder, L0 catalog -> L1 ranked candidates -> L2 specialist agents -> L3 LLM healer).

Date: 2026-06-24

---

## A. Playwright codegen + Trace Viewer + WebDriver BiDi (Microsoft, OSS)

### A.1 Codegen locator priority chain

Playwright's codegen analyzes the DOM and emits the highest-stability locator it can find, in this strict order:

1. `getByRole(role, { name })` - reflects the accessibility tree (role + accessible name); preferred for any interactive element.
2. `getByText(text)` - for non-interactive content (divs, spans, headings).
3. `getByLabel(text)` - form controls associated with a `<label>`.
4. `getByPlaceholder(text)` - inputs that only have a placeholder.
5. `getByAltText(text)` - images and elements with alt.
6. `getByTitle(text)` - elements with a title attribute.
7. `getByTestId(id)` - explicit `data-testid` (configurable via `testIdAttribute`).
8. CSS / XPath fallback - last resort, considered fragile.

If multiple elements match the chosen strategy, codegen "improves the locator to make it resilient that uniquely identifies the target element," typically by adding a chained `.filter({ hasText })` or by narrowing through a parent locator.

The `testIdAttribute` is configurable in `playwright.config.ts`:

```ts
use: { testIdAttribute: 'data-pw' }
```

**Strengths to copy.** The priority chain itself is the right default: role/name first because it is what assistive tech sees and what the LLM can reproduce from a natural-language description. Codegen's "chain locators to narrow scope" approach (e.g. `getByRole('listitem').filter({ hasText: 'foo' }).getByRole('button')`) survives most layout changes.

**Weaknesses to avoid.** Codegen is *one-shot*: it picks a locator at record time and never re-evaluates. It also has no notion of "compound candidates" - if `getByRole('button', { name: 'Save' })` is ambiguous, it falls back to CSS rather than keeping multiple candidates and ranking them at run time. TestForge's `LocatorCandidate[]` plus L1 fallback is a strict improvement here.

Sources: [Playwright codegen docs](https://playwright.dev/docs/codegen), [Playwright Locators docs](https://playwright.dev/docs/locators), [Playwright Best Practices](https://playwright.dev/docs/best-practices).

### A.2 Trace Viewer

A trace is a binary recording captured per test run. With `snapshots: true` (default), Playwright stores **three DOM snapshots per action** (before / at-input / after), every network request, every console message, the action timeline, and a stitched video. Traces open in `trace.playwright.dev` (no install) and let you scrub through every action with the DOM rendered in an iframe sandbox.

**Strengths to copy.** Time-travel debugging with before/at-input/after triple snapshots is the gold standard. Hosting a viewer at a public static URL (open the binary in-browser, no server) makes triage trivial.

**Weaknesses to avoid.** Trace files are large (multi-MB per test) - not designed to be archived for thousands of runs. They are aimed at *human* debugging, not LLM consumption.

Sources: [Playwright Trace Viewer docs](https://playwright.dev/docs/trace-viewer), [TestDino Trace Viewer guide](https://testdino.com/blog/playwright-trace-viewer).

### A.3 WebDriver BiDi

W3C-standard bidirectional WebSocket protocol shipped in Chrome 106 / Firefox 102 (late 2022) and now mature in 2025-2026. Adds vs CDP-only: a *standardized* (cross-browser) wire format, push events for network/console/JS errors, network interception/mocking, and accessibility-tree queries that work the same in Firefox and Chrome.

Playwright support is *still experimental* in mid-2026 - GitHub issue [microsoft/playwright#32577](https://github.com/microsoft/playwright/issues/32577) lists locale emulation, timezone emulation, and other gaps blocking adoption. Selenium 4.1+ and Puppeteer 24+ already default to BiDi.

**Strengths to copy.** Streamed console + network events let the recorder timestamp side-effects, not poll for them. The accessibility-tree endpoint is the same primitive Playwright MCP uses.

**Weaknesses to avoid.** Don't bet on Playwright BiDi yet - the protocol is mature but Playwright's adapter is not. Keep the CDP path.

Sources: [W3C WebDriver BiDi](https://www.w3.org/TR/webdriver-bidi/), [Chrome BiDi 2023 status](https://developer.chrome.com/blog/webdriver-bidi-2023), [Selenium BiDi docs](https://www.selenium.dev/documentation/webdriver/bidi/).

---

## B. Cypress Studio + Cypress 13 selectors

Cypress Studio records UI interactions inside the open Cypress test runner. The selector playground catches `data-cy`, `data-test`, and `data-testid` (and falls back to id/class/tag). Heuristic preference: `data-cy` > `data-test` > `data-testid` > `id` > tag + class.

Open issues ([cypress#3595](https://github.com/cypress-io/cypress/issues/3595), [cypress#27165](https://github.com/cypress-io/cypress/issues/27165)) show the long-standing request for configurable data attributes and emitting `cy.getByCy()` calls - i.e., Cypress is **behind Playwright** on flexible test-id configuration.

`cypress-real-events` is a community plugin that issues *native* CDP events (real keypresses, mouse moves with cursor) instead of synthetic dispatches - works around bugs where libraries (Stripe, Material UI) ignore JS-synthesized events.

**Strengths to copy.** The convention "if `data-cy` exists, prefer it absolutely" is a useful short-circuit. Native CDP events are non-negotiable for masked inputs and rich text editors (TestForge already does `press_sequentially`).

**Weaknesses to avoid.** Cypress's locator chain is shallow (one attribute) and only emits a string selector - no candidate ranking, no semantic fallback. Studio cannot record cross-origin or new-tab flows.

Sources: [Cypress Best Practices](https://docs.cypress.io/app/core-concepts/best-practices), [Cypress selector-playground issue](https://github.com/cypress-io/cypress/issues/3595).

---

## C. Selenium IDE + Side Runner

Selenium IDE's main self-healing trick is **multi-locator capture at record time** plus **fallback at playback time**. For every click/type it stores `linkText`, an XPath, and a CSS selector. At runtime, if the primary fails, SIDE tries each backup in order until one resolves; the test fails only if *all* fail.

**Strengths to copy.** Storing multiple alternative locators per step is the simplest, cheapest healing mechanism that exists - it is essentially TestForge's L1 layer minus scoring. The "succeed if any one works" model is robust.

**Weaknesses to avoid.** No ranking, no learning, no introspection of *why* a locator broke. Locators are pure-string with no semantic role/name component - in 2026 this is obsolete. Side Runner has no parallelism, no trace, no network mocking.

Sources: [Selenium Locator Strategies](https://www.selenium.dev/documentation/webdriver/elements/locators/), [Opensource.com SIDE features](https://opensource.com/article/19/4/features-selenium-ide).

---

## D. Healenium (OSS self-healing for Selenium / Appium)

Algorithm is **Longest Common Subsequence (LCS) with per-attribute weights** plus a heuristic node-distance pass. Workflow:

1. On the first successful step, Healenium serializes the element's full XPath plus a per-node attribute snapshot (tag, id, class, value, etc.) to a Postgres database.
2. On a later run, when Selenium throws `NoSuchElementException`, Healenium intercepts via a custom `WebDriverEventListener`.
3. It fetches the stored path, walks the current DOM, computes LCS distance between stored vs current paths using *weighted* edit-distance over tag/id/class/value matches.
4. For nodes whose path distance >= max LCS distance, it computes a heuristic node-distance (attribute Jaccard plus position) - this skips obviously irrelevant subtrees and is the perf optimization.
5. Ranks all candidates by combined score, picks top match (above a config threshold), executes the action, and writes the new selector + confidence to Postgres for human review.

Healed selectors live in a relational schema: `selector` (original) -> `healing` (timestamp, score) -> `node_path` (the new XPath). A web dashboard at `healenium-web` lets a human accept/reject heals.

**Strengths to copy.** The *persistence* model is excellent: every heal is a database row with confidence + before/after, reviewable by humans. Weighted LCS is a cheap, deterministic, *no-LLM* baseline that should be tried before any model call. TestForge's L0 `HealingCatalog.jsonl` is the same idea, less normalized.

**Weaknesses to avoid.** LCS over XPath only - blind to role/aria/text changes that *should* heal. No semantic fallback. Postgres dependency is heavy for small teams. Algorithm has known false positives on pages with many sibling rows (table cells all look similar by LCS).

Sources: [Healenium official site](https://healenium.io/), [Automate The Planet writeup](https://www.automatetheplanet.com/healenium-self-healing-tests/), [Medium technical deep-dive](https://medium.com/geekculture/healenium-self-healing-library-for-selenium-test-automation-26c2358629c5).

---

## E. Commercial AI testers

### E.1 Mabl

At record time mabl captures **30+ attributes per element** (id, class, all `data-*`, ARIA, visible text, ancestors up N levels, custom test-id) and stores them as the step's "element history." At run time, each attribute is independently scored for stability vs the recorded baseline; the engine picks the highest-stability subset that uniquely identifies an element. "Advanced auto-heal" (GA late 2024) layers a generative LLM on top to **describe the element's purpose** in natural language and locate semantically equivalent elements when the DOM has changed significantly (e.g. button moved into a different component, label rewritten).

**Copy:** the 30-attribute snapshot is a strict superset of TestForge's current `LocatorCandidate[]`. Ancestor context (up N levels) is a missing piece - useful for "click the Save button *inside the dialog*."

**Avoid:** mabl's healing is fully closed-source and reviewable only inside their UI - no JSONL audit trail.

Source: [mabl How auto-heal works](https://help.mabl.com/hc/en-us/articles/19078583792404-How-auto-heal-works).

### E.2 Testim (Tricentis)

Hundreds of attributes per element with per-attribute weights learned across all customer tests. Each locator has a **stability score 0-100%**; when the score drops below **70%** the engine auto-improves the locator by re-running attribute selection. Mobile uses a separate ML model that emits a confidence score per match; users can tune a confidence threshold to trade precision for recall.

**Copy:** the explicit per-locator stability score with a numeric threshold is a clean UX. TestForge should expose a `confidence` per `LocatorCandidate` and surface it in the readiness report.

**Avoid:** closed-source weights, no published training set, model is shared across customers (privacy concern for enterprise UIs).

Source: [Tricentis Testim locator technologies](https://www.tricentis.com/blog/testim-locator-technologies), [Testim Auto Improve docs](https://docs.tricentis.com/testim/content/test-management/locators-auto-improve.htm).

### E.3 Functionize

**Vision-first** approach. Each element gets a "visual fingerprint" computed by a CNN on a cropped screenshot plus a DOM fingerprint. At run time, screenshots before/during/after each action go through CV models for element detection and classification; the engine matches by visual similarity even when DOM is unstable (legacy enterprise apps, canvas-rendered UIs).

**Copy:** for canvas / shadow-DOM / Flash-like elements, vision is the only fallback. Adding a *screenshot-of-the-element* to each `LocatorCandidate` would let a future L4 CV layer do template matching.

**Avoid:** CV is expensive (GPU, latency, training data) and brittle to A/B tests that change colors/sizes. Functionize never publishes model details - all marketing.

Source: [Functionize CV architecture blog](https://www.functionize.com/blog/computer-vision-meets-qa-the-technical-architecture-behind-self-healing-tests), [Functionize smart object selection](https://www.functionize.com/blog/what-is-smart-object-selection).

### E.4 Katalon (relevant because OSS-flavored)

Two tiers: a "Smart XPath" attribute fallback (CSS -> XPath -> attribute -> image) that picks the first match, and (added January 2026) an LLM-powered second tier that ingests **page source + accessibility tree + full-page screenshot + element screenshot** when the classic chain fails. Healed locators are suggested to the user with one-click accept.

**Copy:** the 4-input bundle (DOM + AX tree + page screenshot + element screenshot) is the right LLM prompt for L3 healing. Suggest-don't-apply UX (human approval) is wise.

**Avoid:** the classic fallback is order-of-strategies (no scoring), so Katalon tends to pick a bad attribute selector before getting to the LLM tier.

Source: [Katalon self-healing docs](https://docs.katalon.com/katalon-studio/maintain-tests/self-healing-tests-in-katalon-studio), [Katalon AI Self-Healing blog](https://katalon.com/resources-center/blog/self-healing-test-automation).

---

## F. Recent OSS / research projects (2024-2026)

### F.1 Stagehand (Browserbase)

TypeScript+Python SDK wrapping Playwright. Four primitives: `act(intent)` runs a natural-language step, `extract(schema)` returns Zod/Pydantic-typed JSON from the page, `observe()` returns the *list of possible actions* on the current page (the agent's options menu), `agent()` runs multi-step plans. Internally:

- Default mode is **accessibility-tree based** (DOM mode). It serializes the AX tree, passes it to the LLM, the LLM returns a semantic action plus Playwright arguments. Compatible with Playwright `Page` objects directly.
- Computer-Use Agent (CUA) mode is **vision-based** (coordinate clicks on screenshots). Hybrid mode lets the agent use both per-step.
- v3 is CDP-native (44% faster than the Playwright wrapper).
- **Cache**: on first successful run, the resolved selector + action is keyed by `(intent text, page URL signature)` and replayed without LLM on later runs. Cache keys use only *variable names*, not values, so the same workflow works with different inputs. Replay is sub-100ms.

**Copy:** `observe()` is brilliant - exposing "what can the agent click here?" as a first-class API. The cache-replay-and-fall-back-to-LLM pattern is exactly TestForge's L0->L3 flow but with intent as the cache key. The intent-as-cache-key idea is worth stealing for TestForge's L0 catalog.

**Avoid:** TS-first SDK; Python is a port. Closed Browserbase hosting is the default - self-hosted has rougher edges.

Sources: [Stagehand GitHub](https://github.com/browserbase/stagehand), [Stagehand agent docs](https://docs.stagehand.dev/v3/basics/agent), [DEV.to deep dive](https://dev.to/stevengonsalvez/stagehand-ai-primitives-for-playwright-that-actually-stick-47bm).

### F.2 browser-use

Python agent-first framework that recently **dropped Playwright entirely for raw CDP**. Reasons (from their engineering post):

- Playwright's Node.js relay adds a network hop and meaningful latency over thousands of CDP calls.
- State drift across browser / Playwright relay / Python client caused hung sessions requiring full reconnect.
- They wanted parallel connections to multiple targets and proper cross-origin iframe support, which Playwright abstracted away.

DOM representation for the LLM uses **"super-selectors"**: `(targetId, frameId, backendNodeId, position, fallbackSelector)` - a stable ordinal index that survives DOM changes and crosses origins. Their separate `browser-harness` project is ~592 LOC of Python and lets the LLM *write its own helper functions mid-task*.

**Copy:** super-selectors (multi-field tuple instead of one string) is exactly what `LocatorCandidate` should look like. `backendNodeId` from CDP is far more stable than CSS in a single session.

**Avoid:** raw-CDP-only means no built-in trace viewer, no fixtures, no parallel-test runner. Re-reasoning every step costs LLM tokens per action.

Sources: [Closer to the Metal: Leaving Playwright for CDP](https://browser-use.com/posts/playwright-to-cdp), [browser-use/browser-harness GitHub](https://github.com/browser-use/browser-harness).

### F.3 Skyvern

**Vision-LLM-first**. Their thesis: "the DOM is a lie" - it works on visual-heavy / legacy pages where DOM is unreliable (canvas, Salesforce, internal banking apps). Uses GPT-4-vision-class models on full-page screenshots; element identification is bounding-box based.

**Copy:** for the long-tail of "DOM is hostile" pages, vision is sometimes the only option. Worth thinking about a vision-fallback L4 for TestForge.

**Avoid:** vision is expensive and slow per action; not viable as the primary path.

Source: [Skyvern GitHub](https://github.com/Skyvern-AI/skyvern).

### F.4 LaVague

Two-agent architecture: a **World Model** plans the next high-level instruction from the user's goal + current page state; an **Action Engine** does RAG over the DOM + a screenshot to emit Selenium code. Open-source, Hugging Face / LlamaIndex under the hood.

**Copy:** the two-agent split (plan vs execute) is what TestForge already does (intent reconstruction -> compiler), and worth keeping explicit.

**Avoid:** Selenium-based, smaller ecosystem.

Source: [LaVague docs](https://docs.lavague.ai/en/latest/docs/get-started/quick-tour/).

### F.5 ZeroStep / Auto-Playwright

Plain-English steps inside Playwright tests: `await ai('click the login button')`. Each call sends the DOM snapshot + the instruction to OpenAI and gets back Playwright code that is then executed. No caching - LLM runs every test run.

**Copy:** the *embedded* DSL (one helper inside otherwise normal Playwright code) is great UX.

**Avoid:** no cache, no L0/L1 path, LLM-on-every-step cost. This is exactly the model the 2026 zero-cost-self-healing paper (below) argues against.

Source: [ZeroStep](https://zerostep.com/).

### F.6 Playwright MCP (Microsoft, March 2025)

A Model Context Protocol server that exposes 40+ browser tools (click, navigate, type, evaluate, screenshot, network mock, storage, devtools tracing, locator generation). The agent's primary input is a **YAML accessibility-tree snapshot** of the page; each element gets a stable `[ref=e<N>]` reference. The agent calls `browser_click(ref=e5)` or `browser_type(ref=e7, text)` against those refs. Process-faster-than-vision: YAML snapshot is orders of magnitude cheaper than sending screenshots to GPT-4-vision.

There is also a **Playwright CLI** (early 2026) tuned for coding agents (Claude Code, Cursor, Copilot) that *saves snapshots to disk as YAML files* instead of streaming them into the agent context, letting the agent grep for what it needs.

**Copy:** the YAML AX-tree-with-stable-refs is the single most important pattern of 2025-2026. TestForge should adopt the same intermediate representation - it is what the LLM healer (L3) wants as input *and* what the runtime locator engine should be expressing intent in.

**Avoid:** MCP refs are session-scoped (don't survive page reload); not a persistent identifier.

Sources: [Playwright MCP GitHub](https://github.com/microsoft/playwright-mcp), [Playwright MCP docs](https://playwright.dev/docs/getting-started-mcp), [TestDino MCP guide](https://testdino.com/blog/playwright-mcp).

### F.7 SeleniumBase

OSS Selenium wrapper. Self-healing is a `MasterQA` mode where failures pause for human input; less algorithmic than Healenium. Worth mentioning only to note that mature OSS Selenium has *not* converged on a single self-healing approach.

### F.8 Academic research

- **"Beyond LLM-based test automation: A Zero-Cost Self-Healing Approach Using DOM Accessibility Tree Extraction"** (arXiv 2603.20358, March 2026). Builds a **10-tier priority-ranked locator hierarchy** (top tiers: `get_by_role`, `data-testid`, ARIA labels, CSS class fragments, visible text - the abstract doesn't list all ten). Discovers all locators in a *single one-time pass* over the live DOM accessibility tree, then on failure **re-extracts only the broken selector** rather than re-doing full discovery. Reports 31/31 (100%) pass rate on a 10-workflow benchmark across Desktop Chrome / Desktop Safari / iPhone 15, 22s parallel run, healing in <1s, **zero LLM API cost**. Main argument: LLM-based self-healing is too expensive at enterprise scale (300+ tests).

- **Ramadan et al. (2025)** - systematic review of 100 AI-driven test automation tools; identifies **cost and latency** as the primary barriers to enterprise adoption of LLM approaches.

- **"Machine Learning Approaches for Auto-Repairing Tests"** (IJECS, Nov 2025) - taxonomy of locator-repair, flakiness, wait-automation methods.

- **WebTestPilot** (arXiv 2602.11724, 2026) - agentic E2E web testing against natural-language specs, infers oracles via symbolized GUI elements (interesting parallel to TestForge's "semantic intent" framing).

**Copy:** the zero-cost paper validates TestForge's core thesis - *use the accessibility tree first, save LLM for true outliers*. The "re-extract only the broken selector" pattern (not full re-discovery) is more efficient than what TestForge currently does and worth implementing.

Sources: [arXiv 2603.20358](https://arxiv.org/abs/2603.20358), [Ramadan et al. ML for auto-repair](https://www.ijecs.in/index.php/ijecs/article/view/5299/4400), [WebTestPilot](https://arxiv.org/pdf/2602.11724).

---

## G. WebDriver BiDi accessibility tree - what's new (2024-2026)

In 2022 the AX tree was available only via CDP `Accessibility.getFullAXTree` (Chrome-only, undocumented, frequent breakage). As of 2025-2026:

- **Standardized across browsers**: BiDi exposes the AX tree via the `browsingContext.captureScreenshot` and accessibility modules - same API in Chrome, Firefox, Edge.
- **Streaming events**: subscribe to `log.entryAdded`, `network.responseStarted`, `script.message` and get them pushed over WebSocket - no polling.
- **Network interception**: pause + modify requests / responses without leaving the protocol.
- **The Playwright MCP / Playwright CLI YAML snapshot format is the de-facto consumer format** for the AX tree - structured roles+names+states+refs, ready for an LLM.

What this enables that wasn't possible 2 years ago:
- Recorder can snapshot the AX tree at the moment of each click and store it alongside the DOM - useful for healing because it's *what the LLM also sees*.
- Healing can match by `(role, accessible_name)` across browsers without browser-specific tweaks.
- Console + network can be timestamped into the same trace stream as user actions.

Sources: [W3C BiDi spec](https://www.w3.org/TR/webdriver-bidi/), [TestDino accessibility tree comparison](https://testdino.com/blog/accessibility-tree).

---

## H. AI-native test design patterns

### H.1 Page Object Model -> Intent Object Model

Traditional POM: `LoginPage.usernameField.fill('foo')`. The page object stores selectors. Emerging pattern (Stagehand, ZeroStep, browser-use): the page object stores **intents**, not selectors:

```python
class LoginPage:
    async def enter_username(self, value: str):
        await page.act(f"enter '{value}' in the username field")
```

Resolution happens at run time. Cache the resolved Playwright call (Stagehand) and you get POM-like speed.

### H.2 Semantic test contracts

The shift is from "describe the *DOM* you're targeting" (Page Object) to "describe the *user intent* and let the framework resolve the DOM" (Intent Object / semantic contract). Synpress (for web3), Auto-Playwright, ZeroStep, and Stagehand all sit on this spectrum.

### H.3 LLM-driven runtime locator discovery - "click the login button" without a recorded locator

Three working strategies in production:

1. **AX-tree-as-YAML + ref clicks** (Playwright MCP, Stagehand DOM mode). Serialize the tree, the LLM picks `[ref=e5]`, the framework maps ref->Playwright locator->click. Cheap, deterministic, fast.
2. **DOM-as-text + LLM-emits-Playwright-code** (Auto-Playwright, ZeroStep). Send the HTML, the LLM returns `page.getByRole('button', { name: 'Login' }).click()`. Higher tokens, more flexible.
3. **Screenshot + coordinate click** (Skyvern, Stagehand CUA, browser-use vision mode). Send the image to GPT-4-vision-class, get back `(x, y)` and click. Most expensive, most resilient on canvas / shadow DOM.

The 2025-2026 consensus is "try (1) first, fall through to (2), only use (3) when DOM is canvas." This is **exactly the TestForge L0 -> L1 -> L2 -> L3 staircase** with the vision tier added as L4.

### H.4 What this means for TestForge

Things to copy:
- **YAML AX-tree snapshot** as the L3 LLM input format (matches Playwright MCP).
- **Intent text as cache key** for L0 healing (matches Stagehand cache).
- **Per-attribute stability score** surfaced to users (matches Testim).
- **30+ attribute capture** including ancestor context (matches mabl).
- **Super-selector tuple** with `backendNodeId` (matches browser-use).
- **Persisted heal history** in a JSONL/SQLite store, human-reviewable (matches Healenium).
- **Re-extract only the broken selector** on heal (matches arXiv 2603.20358).

Things to skip:
- **Pure-vision-first** (Skyvern, Functionize) - too expensive as primary path.
- **LLM on every step** (ZeroStep) - no caching, doesn't scale.
- **Side Runner-style multi-locator with no scoring** - already obsolete.
- **CDP-only with no Playwright** (browser-use) - loses too much tooling.

---

## TL;DR criticism of TestForge

What TestForge already does well vs the state of the art:
- 4-layer staircase (L0 catalog -> L1 candidates -> L2 agents -> L3 LLM) matches the consensus pattern; L0 catalog mirrors Stagehand's cache and Healenium's persisted heals.
- 11-family failure taxonomy is more granular than any commercial tool's public taxonomy.
- L0.5 fuzzy `get_by_role` with regex is a unique mid-tier between exact and LLM that nobody else publishes.

Likely gaps worth a phase:
1. No **YAML AX-tree snapshot** alongside steps - L3 prompts would be cheaper and more accurate with it.
2. `LocatorCandidate` is a flat string list - should be a **super-selector tuple** (role, name, AX path, backendNodeId, CSS, XPath) with a confidence per field.
3. No **per-locator stability score** surfaced in `readiness_report.md` (Testim does this).
4. No **ancestor-N-levels context** captured per element (mabl does this; helps with "Save button inside Dialog").
5. Heal events should record **why it healed** (which attribute changed) - currently just records the new locator.
6. L3 healing currently re-discovers everything; should **re-extract only the broken selector** (arXiv 2603.20358 pattern).
7. No vision L4 - fine for now, but a `screenshot_path` field per `LocatorCandidate` would make adding one cheap later.

---

## Sources

- [Playwright codegen docs](https://playwright.dev/docs/codegen)
- [Playwright Locators docs](https://playwright.dev/docs/locators)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [Playwright MCP GitHub](https://github.com/microsoft/playwright-mcp)
- [Playwright MCP docs](https://playwright.dev/docs/getting-started-mcp)
- [BiDi adoption blockers issue](https://github.com/microsoft/playwright/issues/32577)
- [W3C WebDriver BiDi spec](https://www.w3.org/TR/webdriver-bidi/)
- [Chrome BiDi 2023 status](https://developer.chrome.com/blog/webdriver-bidi-2023)
- [Selenium BiDi docs](https://www.selenium.dev/documentation/webdriver/bidi/)
- [Selenium Locator Strategies](https://www.selenium.dev/documentation/webdriver/elements/locators/)
- [Opensource.com SIDE features](https://opensource.com/article/19/4/features-selenium-ide)
- [Cypress Best Practices](https://docs.cypress.io/app/core-concepts/best-practices)
- [Cypress selector-playground issue](https://github.com/cypress-io/cypress/issues/3595)
- [Healenium official site](https://healenium.io/)
- [Healenium algorithm writeup (Automate The Planet)](https://www.automatetheplanet.com/healenium-self-healing-tests/)
- [Healenium Medium deep-dive](https://medium.com/geekculture/healenium-self-healing-library-for-selenium-test-automation-26c2358629c5)
- [mabl How auto-heal works](https://help.mabl.com/hc/en-us/articles/19078583792404-How-auto-heal-works)
- [Tricentis Testim locator technologies](https://www.tricentis.com/blog/testim-locator-technologies)
- [Testim Auto Improve docs](https://docs.tricentis.com/testim/content/test-management/locators-auto-improve.htm)
- [Functionize CV architecture](https://www.functionize.com/blog/computer-vision-meets-qa-the-technical-architecture-behind-self-healing-tests)
- [Functionize smart object selection](https://www.functionize.com/blog/what-is-smart-object-selection)
- [Katalon self-healing docs](https://docs.katalon.com/katalon-studio/maintain-tests/self-healing-tests-in-katalon-studio)
- [Stagehand GitHub](https://github.com/browserbase/stagehand)
- [Stagehand agent docs](https://docs.stagehand.dev/v3/basics/agent)
- [Stagehand DEV.to deep dive](https://dev.to/stevengonsalvez/stagehand-ai-primitives-for-playwright-that-actually-stick-47bm)
- [browser-use: leaving Playwright for CDP](https://browser-use.com/posts/playwright-to-cdp)
- [browser-use/browser-harness GitHub](https://github.com/browser-use/browser-harness)
- [Skyvern GitHub](https://github.com/Skyvern-AI/skyvern)
- [LaVague docs](https://docs.lavague.ai/en/latest/docs/get-started/quick-tour/)
- [ZeroStep](https://zerostep.com/)
- [arXiv 2603.20358 - Zero-Cost Self-Healing via AX Tree](https://arxiv.org/abs/2603.20358)
- [WebTestPilot arXiv 2602.11724](https://arxiv.org/pdf/2602.11724)
- [ML Approaches for Auto-Repairing Tests (IJECS, 2025)](https://www.ijecs.in/index.php/ijecs/article/view/5299/4400)
- [TestDino Accessibility Tree comparison](https://testdino.com/blog/accessibility-tree)
- [TestDino Playwright AI Ecosystem 2026](https://testdino.com/blog/playwright-ai-ecosystem)
