"""TestForge — LLM Healing Prompts.

11 family-specific prompts + generic CURATION_PROMPT_TEMPLATE.
All prompts in English for maximum LLM accuracy.
Each prompt ≤1500 chars, includes valid strategies and JSON format.

Reference: conhecimento_ancestral/projeto-anterior/llm/prompts.py
"""
from __future__ import annotations

CURATION_PROMPT_TEMPLATE = """You are a Playwright test healing specialist.
Your task: return ONLY a JSON object with the healing proposal. No other text.

## Step Context
- Action: {action}
- Failed selector: {selector}
- Value: {value}
- Intention: {intention}

## Original Error
{error_message}

## DOM Snippet (sanitized)
{dom_snippet}

## Console Errors (last 5)
{console_errors}

## Network (last 3 requests)
{network_summary}

## Available Taxonomies
{taxonomy_hint}

## Response Format (MANDATORY — JSON ONLY)
{{
  "taxonomy_id": "SEL-004",
  "family": "FAM-01",
  "strategy": "semantic_locator_conversion",
  "new_locator": "button:has-text('Search')",
  "confidence": 0.85,
  "rationale": "One sentence explaining the fix"
}}

Rules:
- taxonomy_id: valid code from the list above
- family: corresponding FAM code
- strategy: one of: semantic_locator_conversion, has_text_fallback, masked_input_detection, press_sequentially, dialog_handler, visibility_wait, iframe_switch, label_click, synthetic_click, xpath_fallback
- new_locator: valid CSS/Playwright selector string (e.g., 'text=Search', 'button:has-text(\"Search\")', '[data-testid=\"btn\"]', '#my-id'). Do NOT use Playwright API chains like page.get_by_role() — use plain selectors only.
- confidence: 0.0 to 1.0 (>= 0.5 accepted for auto-healing)
- rationale: ONE sentence explaining the analysis

CRITICAL: Your ENTIRE response MUST be ONLY the JSON object above. No explanation. No markdown. No analysis text. JUST the JSON.
"""

FAM01_SEL_PROMPT = """You are a Playwright selector specialist.
Analyze the selector failure below and propose a new locator.

## Valid Strategies
- semantic_locator_conversion: convert to data-testid, id, name, aria-label, placeholder, or has-text
- has_text_fallback: use text= or :has-text() selector
- xpath_fallback: last resort, use absolute or relative XPath

## Selector Priority
1. data-testid (most stable)
2. id
3. name
4. aria-label
5. placeholder
6. has-text
7. href (for links)
8. alt (for images)
9. class
10. XPath / DOM path (fallback)

## Step Context
- Action: {action}
- Failed selector: {selector}
- Value: {value}
- Intention: {intention}

## Original Error
{error_message}

## DOM Snippet
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"SEL-004","family":"FAM-01","strategy":"semantic_locator_conversion","new_locator":"button:has-text('Example')","confidence":0.85,"rationale":"Element found by button text — ID changed but text is stable"}}"""

FAM02_TIM_PROMPT = """You are a Playwright timing specialist.
Analyze the timing/async failure below and propose a fix.

## Valid Strategies
- visibility_wait: waitForSelector with visible state + longer timeout
- dialog_handler: register page.on("dialog") before the action
- has_text_fallback: wait for visible text

## Typical Symptoms
- Timeout: element did not appear in time
- Stale element: DOM changed between locate and act
- Net::ERR: resource failed to load
- Wait: expect with too-short timeout

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"TIM-005","family":"FAM-02","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.9,"rationale":"Add waitForSelector with longer timeout before clicking"}}"""

FAM03_CTX_PROMPT = """You are a Playwright context/scope specialist.
Analyze the iframe/shadow DOM/popup failure below and propose a fix.

## Valid Strategies
- iframe_switch: page.frame() or page.frame_locator() before the action
- has_text_fallback: textual fallback when shadow DOM blocks
- synthetic_click: click via JS dispatch when element is in closed shadow DOM

## Typical Symptoms
- iframe: element is inside a frame
- shadow DOM: element is in a shadow root
- cross-origin: cross-domain iframe (no internal DOM access)
- popup: new tab/window blocked

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"CTX-001","family":"FAM-03","strategy":"iframe_switch","new_locator":"iframe[name='main'] >> text='{value}'","confidence":0.85,"rationale":"Element inside same-origin iframe; use iframe chained selector"}}"""

FAM04_STA_PROMPT = """You are a Playwright application state specialist.
Analyze the state failure (modal, dialog, overlay, session) below and propose a fix.

## Valid Strategies
- dialog_handler: page.on("dialog", lambda d: d.accept()) before the action
- visibility_wait: wait for overlay to disappear before interacting
- synthetic_click: force click via JS if element is covered
- label_click: click the <label> instead of the disabled input

## Typical Symptoms
- Dialog/alert/confirm: page blocked by modal
- Session expired: token expired, redirected to login
- Overlay: modal/cookie banner covering the element

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"STA-004","family":"FAM-04","strategy":"dialog_handler","new_locator":"{selector}","confidence":0.9,"rationale":"Add dialog handler to accept alert/confirm before interaction"}}"""

FAM05_DOM_PROMPT = """You are a Playwright dynamic DOM specialist.
Analyze the stale/reorder/lazy-load failure below and propose a fix.

## Valid Strategies
- semantic_locator_conversion: use semantic selector not dependent on position
- has_text_fallback: locate by text instead of index/nth-child
- visibility_wait: wait for lazy loading to complete

## Typical Symptoms
- Stale element: element was removed and re-inserted in the DOM
- Reorder: elements changed position
- Lazy loading: content loaded after default timeout
- SPA route: route changed, components remounted

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"DOM-001","family":"FAM-05","strategy":"has_text_fallback","new_locator":"text='{value}'","confidence":0.8,"rationale":"Stale element; relocate by exact text match instead of DOM position"}}"""

FAM06_INP_PROMPT = """You are a Playwright input/interaction specialist.
Analyze the form field failure below and propose a fix.

## Valid Strategies
- press_sequentially: type character by character (JS-masked fields)
- masked_input_detection: use raw JS setter + dispatch events
- label_click: click the <label> to focus the field before filling
- synthetic_click: force focus via JS before fill

## Typical Symptoms
- fill: does not trigger input events, field stays empty
- clear: field does not clear
- not editable: field is readonly or disabled
- masked input: masked field (SSN, ZIP, phone) rejects direct fill

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"INP-007","family":"FAM-06","strategy":"press_sequentially","new_locator":"{selector}","confidence":0.85,"rationale":"JS-masked field; use press_sequentially instead of fill"}}"""

FAM07_FILE_PROMPT = """You are a Playwright upload/download specialist.
Analyze the file operation failure below and propose a fix.

## Valid Strategies
- semantic_locator_conversion: locate input[type=file] by label, not class
- label_click: trigger upload by clicking the label that opens the file picker
- synthetic_click: force click on hidden file input via JS

## Typical Symptoms
- Hidden file input: input[type=file] with display:none
- Drag-and-drop: upload area accepts drop but has no visible input
- Multiple: upload only accepts 1 file but requirement needs multiple
- Download redirect: download URL redirects, Playwright doesn't follow

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"FILE-001","family":"FAM-07","strategy":"label_click","new_locator":"input[type=file]","confidence":0.8,"rationale":"Hidden file input; trigger via label that opens the file picker"}}"""

FAM08_AST_PROMPT = """You are a Playwright assertions specialist.
Analyze the assertion failure below and propose a fix.

## Valid Strategies
- visibility_wait: add wait before the assert (element may not have loaded)
- semantic_locator_conversion: fix the selector of the assert target element

## Typical Symptoms
- AssertionError: value does not match expected
- Expect: condition not satisfied within timeout
- Text mismatch: text differs (case, whitespace, partial content)

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"AST-001","family":"FAM-08","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.75,"rationale":"Assert failed because element was not yet visible; add wait"}}"""

FAM09_REC_PROMPT = """You are a Playwright recording specialist.
Analyze the recording failure below and propose a fix.

## Valid Strategies
- synthetic_click: simulate click on element that didn't fire click event
- has_text_fallback: locate element by text when recording selector fails
- xpath_fallback: fallback to XPath when no text or semantic attribute available

## Typical Symptoms
- Duplicate event: recording captured 2 events for 1 interaction
- Missed event: listener didn't capture the interaction
- Autocomplete: value changed after menu selection (needs extra fill)
- Pause/resume: overlay didn't respond to pause

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"REC-002","family":"FAM-09","strategy":"synthetic_click","new_locator":"{selector}","confidence":0.8,"rationale":"Element didn't fire click event; use dispatchEvent as fallback"}}"""

FAM10_OBS_PROMPT = """You are a Playwright execution/infrastructure specialist.
Analyze the execution failure below and propose a fix.

## Valid Strategies
- visibility_wait: increase timeout for slow pages
- dialog_handler: handle unexpected popups blocking execution
- xpath_fallback: fallback when error is selector not found

## Typical Symptoms
- Global timeout: entire page exceeded timeout
- Crash: browser crashed or closed unexpectedly
- Network: essential request failed (CDN, API)
- Fallback: step was already in fallback healing and failed again

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"OBS-004","family":"FAM-10","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.7,"rationale":"Execution failure likely caused by timeout; increase tolerance"}}"""

FAM11_LIM_PROMPT = """You are a Playwright browser limits specialist.
Analyze the failure below and document it as not safely automatable.

## Valid Strategies
- synthetic_click: final attempt via JS dispatch
- has_text_fallback: textual fallback when selector fails

## Typical Symptoms
- Cross-origin: cannot access cross-origin iframe DOM
- Popup blocker: browser blocked new tab
- Locale: page in different locale than expected
- SSL: invalid certificate blocked loading
- Headless: functionality that only works in headed mode

## Context
- Action: {action}
- Selector: {selector}
- Value: {value}
- Intention: {intention}

## Error
{error_message}

## DOM
{dom_snippet}

Respond with ONLY JSON:
{{"taxonomy_id":"LIM-001","family":"FAM-11","strategy":"synthetic_click","new_locator":"{selector}","confidence":0.4,"rationale":"Technical limit: cross-origin iframe with no internal DOM access"}}"""

FAMILY_PROMPTS: dict[str, str] = {
    "FAM-01": FAM01_SEL_PROMPT,
    "FAM-02": FAM02_TIM_PROMPT,
    "FAM-03": FAM03_CTX_PROMPT,
    "FAM-04": FAM04_STA_PROMPT,
    "FAM-05": FAM05_DOM_PROMPT,
    "FAM-06": FAM06_INP_PROMPT,
    "FAM-07": FAM07_FILE_PROMPT,
    "FAM-08": FAM08_AST_PROMPT,
    "FAM-09": FAM09_REC_PROMPT,
    "FAM-10": FAM10_OBS_PROMPT,
    "FAM-11": FAM11_LIM_PROMPT,
}
