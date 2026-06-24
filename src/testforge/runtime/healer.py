"""Runtime multi-attribute self-healing — resolve selectors by scoring live DOM elements
against the recorded fingerprint.

Heuristic over strict — score 0.0-1.0, threshold gates confidence.
Designed to be called from generated test scripts when Playwright locator fails.

Catalogo auto-aprendido: successful heal resolutions are recorded to a JSONL file.
Next time the same fingerprint appears, the catalog returns instantly (<1ms)
instead of re-scoring against the live DOM.

Usage (generated script)::

    from testforge.runtime.healer import resolve_selector
    _best = resolve_selector(page, ["input#foo", "input[name='bar']"], {"tag": "input", "placeholder": "R$0,00"})
    if _best:
        page.fill(_best, "5000")
    else:
        raise AssertionError("fill step 1 falhou")
"""

import json
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default confidence threshold — below this, None is returned
CONFIDENCE_THRESHOLD = 0.40

# Default catalog path (relative to CWD)
_DEFAULT_CATALOG_PATH = ".testforge/heal_catalog.jsonl"

# Max entries in catalog before oldest eviction
_CATALOG_MAX_ENTRIES = 1000

# Entry TTL: 30 days in seconds
_CATALOG_TTL = 30 * 24 * 3600

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


# ---------------------------------------------------------------------------
# Catalog auto-aprendido — records successful heal resolutions for <1ms reuse
# ---------------------------------------------------------------------------

def _fp_key(fp: dict) -> str:
    """Canonical JSON key for a fingerprint (sorted keys for determinism)."""
    return json.dumps(fp, sort_keys=True, ensure_ascii=False, default=str)


@dataclass
class _CatalogEntry:
    fingerprint: dict
    selector: str
    score: float
    success_count: int
    last_success: float  # epoch seconds


class HealCatalog:
    """Persistent catalog of successful heal resolutions.

    Maps element fingerprints to selectors that worked before.
    Lookup is O(1) dict keyed by canonical JSON fingerprint.

    Storage is JSONL at ``path`` — one JSON object per line.
    Default path is ``.testforge/heal_catalog.jsonl`` (override via
    ``TESTFORGE_HEAL_CATALOG`` env var). Set path to ``""`` for
    memory-only (no persistence).
    """

    def __init__(self, path: str | None = None):
        env_path = os.environ.get("TESTFORGE_HEAL_CATALOG", "")
        self.path = (
            path if path is not None
            else env_path if env_path
            else _DEFAULT_CATALOG_PATH
        )
        self._entries: dict[str, _CatalogEntry] = {}
        self._load()

    def lookup(self, fingerprint: dict) -> str | None:
        """Return best selector for *exact* fingerprint match, or None.

        Expired entries (30d since last success) are skipped and evicted.
        """
        if not fingerprint:
            return None
        key = _fp_key(fingerprint)
        entry = self._entries.get(key)
        if entry is None:
            return None
        age = time.time() - entry.last_success
        if age > _CATALOG_TTL:
            del self._entries[key]
            return None
        logger.info("heal_catalog: HIT fp_key=%s sel=%s score=%.2f n=%d",
                     key, entry.selector, entry.score, entry.success_count)
        return entry.selector

    def record(self, fingerprint: dict, selector: str, score: float):
        """Record or reinforce a successful healing.

        New entries are appended. Existing entries have their count
        incremented and score updated to max(old, new).
        """
        if not fingerprint or not selector:
            return
        key = _fp_key(fingerprint)
        now = time.time()
        if key in self._entries:
            entry = self._entries[key]
            entry.success_count += 1
            entry.last_success = now
            if score > entry.score:
                entry.score = score
        else:
            self._entries[key] = _CatalogEntry(
                fingerprint=fingerprint,
                selector=selector,
                score=score,
                success_count=1,
                last_success=now,
            )
        self._save()

    def _key_set(self) -> set[str]:
        return set(self._entries.keys())

    # ----- serialization -----

    def _load(self):
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("heal_catalog: skip bad line in %s: %r",
                                       self.path, line[:80])
                        continue
                    entry = _CatalogEntry(
                        fingerprint=data["fp"],
                        selector=data["sel"],
                        score=data["score"],
                        success_count=data.get("n", 1),
                        last_success=data.get("ts", 0.0),
                    )
                    self._entries[_fp_key(entry.fingerprint)] = entry
            # Evict expired at load time
            now = time.time()
            expired = [k for k, e in self._entries.items()
                       if now - e.last_success > _CATALOG_TTL]
            for k in expired:
                del self._entries[k]
        except Exception as exc:
            logger.warning("heal_catalog: load error %s — %s", self.path, exc)

    def _save(self):
        if not self.path:
            return
        try:
            # Evict oldest if over limit
            if len(self._entries) > _CATALOG_MAX_ENTRIES:
                sorted_entries = sorted(
                    self._entries.items(),
                    key=lambda x: x[1].last_success,
                )
                excess = len(sorted_entries) - _CATALOG_MAX_ENTRIES
                for k, _ in sorted_entries[:excess]:
                    del self._entries[k]

            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            now = time.time()
            with open(self.path, "w", encoding="utf-8") as f:
                for entry in self._entries.values():
                    # Skip expired at write time
                    if now - entry.last_success > _CATALOG_TTL:
                        continue
                    f.write(json.dumps({
                        "fp": entry.fingerprint,
                        "sel": entry.selector,
                        "score": entry.score,
                        "n": entry.success_count,
                        "ts": entry.last_success,
                    }, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("heal_catalog: save error %s — %s", self.path, exc)

    def clear(self):
        """Clear all entries (used in tests)."""
        self._entries.clear()
        if self.path and os.path.exists(self.path):
            try:
                os.remove(self.path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Global catalog singleton — transparent to generated scripts
# ---------------------------------------------------------------------------

_CATALOG: HealCatalog | None = None


def _get_catalog() -> HealCatalog:
    """Lazy-init global catalog singleton."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = HealCatalog()
    return _CATALOG


def reset_catalog():
    """Reset catalog singleton and clear persistent file (for test isolation)."""
    global _CATALOG
    if _CATALOG is not None:
        _CATALOG.clear()
    _CATALOG = None


def resolve_selector(
    page,
    selectors: list[str],
    fingerprint: dict | None = None,
    threshold: float | None = None,
) -> str | None:
    """Try each CSS selector against live DOM and score matches against fingerprint.

    Checks the :class:`HealCatalog` first — if a previous successful resolution
    exists for the exact fingerprint, returns it instantly (<1ms).

    Otherwise falls through to live DOM scoring. On success, automatically
    records the result in the catalog for future reuse.

    Args:
        page: Playwright Page (sync API).
        selectors: CSS selector strings to evaluate.
        fingerprint: Dict of recorded element attributes (from SemanticTarget).
        threshold: Minimum score to accept a match. Defaults to CONFIDENCE_THRESHOLD.

    Returns:
        Best-matching selector string, or None if none score above threshold.
    """
    thresh = threshold if threshold is not None else CONFIDENCE_THRESHOLD

    # Fast path: catalog lookup (<1ms, no DOM interaction)
    if fingerprint:
        cat = _get_catalog()
        cached = cat.lookup(fingerprint)
        if cached is not None:
            return cached

    # Slow path: live DOM scoring
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
        # Auto-record in catalog for future reuse
        if fingerprint:
            try:
                _get_catalog().record(fingerprint, best_sel, best_score)
            except Exception:
                pass
        return best_sel

    logger.info("resolve_selector: best=%s score=%.2f below threshold=%.2f", best_sel, best_score, thresh)
    return None
