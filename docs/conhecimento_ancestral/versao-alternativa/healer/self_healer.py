"""
TestForge — Self Healer (Phase 3)
Handles selector failures: tries local fallbacks first, then asks LLM.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from generator.llm_client import chat
from healer.patcher import patch_selector

log = logging.getLogger("testforge.healer")

LLM_HEAL_SYSTEM = """You are a Playwright selector repair assistant.
A test selector has stopped working. Your job is to suggest new selectors.

RESPOND ONLY with a JSON object (no markdown, no explanation):
{
  "data_testid": "...",
  "aria": "...",
  "text": "...",
  "css": "...",
  "xpath": "..."
}

Leave fields as null if you cannot determine a reliable selector.
Base your suggestions on the screenshot and current DOM HTML provided."""


class HealResult:
    def __init__(self):
        self.healed: bool = False
        self.original_selector: str = ""
        self.new_selector: str = ""
        self.method: str = ""  # "local_fallback" | "llm" | "failed"
        self.attempts: int = 0


def try_local_fallbacks(
    page,
    selectors: dict[str, str],
    skip_selector: str,
    timeout: int = 5000,
) -> Optional[str]:
    """
    Try all available selectors except the failing one.
    Returns the first selector that finds a visible element, or None.
    """
    priority = ["data_testid", "aria", "text", "css", "xpath"]

    for key in priority:
        sel = selectors.get(key)
        if not sel or sel == skip_selector:
            continue
        try:
            locator = _resolve_locator(page, key, sel)
            locator.wait_for(state="visible", timeout=timeout)
            log.info(f"Local fallback succeeded with [{key}]: {sel!r}")
            return sel
        except Exception:
            log.debug(f"Local fallback failed [{key}]: {sel!r}")
            continue

    return None


def _resolve_locator(page, key: str, selector: str):
    """Convert our selector dict entry into a Playwright locator."""
    if key == "text":
        # "text=Some Text" or "[placeholder=...]"
        if selector.startswith("text="):
            return page.get_by_text(selector[5:], exact=False)
        else:
            return page.locator(selector)
    elif key in ("data_testid", "aria", "css"):
        return page.locator(selector)
    elif key == "xpath":
        xpath = selector if selector.startswith("//") else f"//{selector}"
        return page.locator(f"xpath={xpath}")
    else:
        return page.locator(selector)


def try_llm_heal(
    page,
    failing_selector: str,
    original_context: dict,
    selectors: dict[str, str],
) -> Optional[str]:
    """
    Take a screenshot, send to LLM with DOM context, get new selectors back.
    Returns the best new selector string or None.
    """
    # Screenshot
    screenshot_b64 = None
    try:
        screenshot_bytes = page.screenshot(type="png")
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
    except Exception as e:
        log.warning(f"Screenshot failed: {e}")

    # DOM snippet (visible elements only, truncated)
    dom_snippet = ""
    try:
        dom_snippet = page.evaluate("""
            () => {
                const els = document.querySelectorAll(
                    'button, input, select, textarea, a, [role], [data-testid]'
                );
                return Array.from(els).slice(0, 60).map(el => el.outerHTML.slice(0, 200)).join('\\n');
            }
        """)
    except Exception:
        pass

    user_prompt = f"""The following selector stopped working: {failing_selector!r}

ORIGINAL ELEMENT CONTEXT:
{json.dumps(original_context, indent=2)}

OTHER SELECTORS THAT ALSO FAILED:
{json.dumps(selectors, indent=2)}

CURRENT DOM SNIPPET (first 60 interactive elements):
{dom_snippet[:3000]}

Please suggest new selectors for this element."""

    images = [screenshot_b64] if screenshot_b64 else None

    try:
        response = chat(
            system=LLM_HEAL_SYSTEM,
            user=user_prompt,
            temperature=0.1,
            max_tokens=512,
            images=images,
        )

        # Parse JSON response
        clean = re.sub(r"```json?\n?|```", "", response).strip()
        new_selectors = json.loads(clean)

        # Try each suggested selector
        priority = ["data_testid", "aria", "text", "css", "xpath"]
        for key in priority:
            sel = new_selectors.get(key)
            if not sel:
                continue
            try:
                locator = _resolve_locator(page, key, sel)
                locator.wait_for(state="visible", timeout=5000)
                log.info(f"LLM heal succeeded with [{key}]: {sel!r}")
                return sel
            except Exception:
                log.debug(f"LLM selector failed [{key}]: {sel!r}")
                continue

    except json.JSONDecodeError as e:
        log.warning(f"LLM returned invalid JSON: {e}")
    except Exception as e:
        log.error(f"LLM heal error: {e}")

    return None


def heal_selector(
    page,
    test_path: Path,
    failing_selector: str,
    selectors: dict[str, str],
    context: dict,
    llm_enabled: bool = True,
    max_attempts: int = 5,
) -> HealResult:
    """
    Full heal flow: local fallbacks → LLM → patch file.
    """
    result = HealResult()
    result.original_selector = failing_selector

    # 1. Try local fallbacks
    result.attempts += 1
    new_sel = try_local_fallbacks(page, selectors, skip_selector=failing_selector)
    if new_sel:
        result.healed = True
        result.new_selector = new_sel
        result.method = "local_fallback"
        patch_selector(test_path, failing_selector, new_sel)
        return result

    if not llm_enabled:
        result.method = "failed"
        return result

    # 2. LLM heal
    for attempt in range(1, max_attempts + 1):
        result.attempts += 1
        log.info(f"LLM heal attempt {attempt}/{max_attempts}")
        new_sel = try_llm_heal(page, failing_selector, context, selectors)
        if new_sel:
            result.healed = True
            result.new_selector = new_sel
            result.method = "llm"
            patch_selector(test_path, failing_selector, new_sel)
            return result

    result.method = "failed"
    return result
