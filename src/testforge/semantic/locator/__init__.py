"""Phase 2: Modern locator extraction pipeline.

Replaces the 16-strategy hand-rolled `_build_target` in `recording_normalizer`
with:

- `intent.py`            generates Stagehand-style intent text for L0 cache keying
- `scorer.py`            per-attribute stability heuristics (no magic numbers)
- `playwright_codegen.py` emits Playwright-native locator calls
                          (get_by_role, get_by_label, get_by_test_id, ...)
- `extractor.py`         orchestrates the above into a ranked super-selector
                          `LocatorCandidate[]` consuming the AX-tree snapshot
                          produced by the Phase 1 CDP recorder.

Feature-flagged via `RecordingNormalizer(use_v2_locator=True)` — when off,
the legacy `_build_target` path is used unchanged. When on, v2 candidates
are appended after legacy candidates so downstream code can opt in
incrementally (Phase 3 compiler will consume v2 directly).
"""

from .extractor import LocatorExtractor
from .intent import normalize_intent
from .playwright_codegen import emit_playwright_call
from .scorer import attribute_stability

__all__ = [
    "LocatorExtractor",
    "normalize_intent",
    "emit_playwright_call",
    "attribute_stability",
]
