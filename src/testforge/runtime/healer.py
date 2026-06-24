"""Runtime multi-attribute self-healing — resolve selectors by scoring live DOM elements
against the recorded fingerprint.

Heuristic over strict — score 0.0-1.0, threshold gates confidence.
Designed to be called from generated test scripts when Playwright locator fails.

Usage (generated script)::

    from testforge.runtime.healer import resolve_selector
    _best = resolve_selector(page, ["input#foo", "input[name='bar']"], {"tag": "input", "placeholder": "R$0,00"})
    if _best:
        page.fill(_best, "5000")
    else:
        raise AssertionError("fill step 1 falhou")
"""

import logging

logger = logging.getLogger(__name__)

# Default confidence threshold — below this, None is returned
CONFIDENCE_THRESHOLD = 0.40

# Injected JS to extract live element attributes for scoring
_LIVE_ATTRS_JS = """(el) => ({
    tag: (el.tagName || '').toLowerCase(),
    role: el.getAttribute('role') || '',
    accessible_name: el.getAttribute('aria-label') || '',
    placeholder: el.getAttribute('placeholder') || '',
    name: el.getAttribute('name') || '',
    id: el.id || '',
    text: (el.textContent || '').trim().slice(0, 60),
})"""


def _score_match(live: dict, fingerprint: dict) -> float:
    """Score 0.0-1.0 how well a live element matches the recorded fingerprint.

    Each fingerprint key contributes its weight only when present.
    Matches are exact unless marked fuzzy (substring allowed at 0.6x).
    """
    if not fingerprint or not live:
        return 0.0

    total_weight = 0.0
    matched_weight = 0.0

    # (live_key, fp_key, weight, allow_substring)
    checks = [
        ("tag", "tag", 0.15, False),
        ("role", "role", 0.20, False),
        ("accessible_name", "accessible_name", 0.25, True),
        ("placeholder", "placeholder", 0.15, True),
        ("name", "name", 0.10, False),
        ("id", "id", 0.10, False),
        ("text", "text", 0.15, True),
    ]

    for live_key, fp_key, weight, allow_substring in checks:
        lv = (live.get(live_key) or "").strip()
        fv = (fingerprint.get(fp_key) or "").strip()
        if not fv:
            continue  # not recorded in fingerprint, skip
        total_weight += weight
        if not lv:
            continue  # element lacks this attr, no match
        if allow_substring:
            lv_lower = lv.lower()
            fv_lower = fv.lower()
            if lv_lower == fv_lower:
                matched_weight += weight
            elif fv_lower in lv_lower or lv_lower in fv_lower:
                matched_weight += weight * 0.6
        else:
            if lv == fv:
                matched_weight += weight

    if total_weight == 0.0:
        return 0.0
    return min(matched_weight / total_weight, 1.0)


def resolve_selector(
    page,
    selectors: list[str],
    fingerprint: dict | None = None,
    threshold: float | None = None,
) -> str | None:
    """Try each CSS selector against live DOM and score matches against fingerprint.

    Args:
        page: Playwright Page (sync API).
        selectors: CSS selector strings to evaluate.
        fingerprint: Dict of recorded element attributes (from SemanticTarget).
        threshold: Minimum score to accept a match. Defaults to CONFIDENCE_THRESHOLD.

    Returns:
        Best-matching selector string, or None if none score above threshold.
    """
    thresh = threshold if threshold is not None else CONFIDENCE_THRESHOLD
    candidates: list[tuple[float, str]] = []

    for sel in selectors:
        loc = page.locator(sel)
        try:
            count = loc.count()
        except Exception:
            continue
        if count == 0:
            continue

        # Extract attributes from the first (and typically only) match
        try:
            handle = loc.first.element_handle()
            if not handle:
                continue
            live = page.evaluate(_LIVE_ATTRS_JS, handle)
            if not live:
                continue
        except Exception:
            continue

        score = _score_match(live, fingerprint or {})
        if score > 0.0:
            candidates.append((score, sel))
            logger.debug("resolve_selector: sel=%s score=%.2f live=%s", sel, score, live)

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_sel = candidates[0]
    if best_score >= thresh:
        logger.info("resolve_selector: best=%s score=%.2f threshold=%.2f", best_sel, best_score, thresh)
        return best_sel

    logger.info("resolve_selector: best=%s score=%.2f below threshold=%.2f", best_sel, best_score, thresh)
    return None
