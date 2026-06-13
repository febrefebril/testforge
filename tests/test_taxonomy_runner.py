"""Testes da Taxonomia, ShadowValidator e FallbackRunner."""
from playwright.sync_api import Page

from testforge.taxonomy import FailureClassifier, FailureFamily
from testforge.runner import ShadowValidator, FallbackRunner


class TestFailureClassifier:
    def test_locator_not_found(self):
        c = FailureClassifier()
        result = c.classify("element not found", {"count": 0})
        assert result.family == FailureFamily.LOCATOR_RESOLUTION
        assert result.code == "LOCATOR_NOT_FOUND"

    def test_locator_ambiguous(self):
        c = FailureClassifier()
        result = c.classify("strict locator", {"count": 5})
        assert result.code == "LOCATOR_AMBIGUOUS"

    def test_overlay_obscured(self):
        c = FailureClassifier()
        result = c.classify("element is obscured by overlay")
        assert result.family == FailureFamily.ACTIONABILITY
        assert result.code == "ACTIONABILITY_OBSCURED"

    def test_disabled(self):
        c = FailureClassifier()
        result = c.classify("element is not enabled. disabled")
        assert result.code == "ACTIONABILITY_DISABLED"

    def test_timeout(self):
        c = FailureClassifier()
        result = c.classify("Timeout waiting for selector")
        assert result.family == FailureFamily.SYNCHRONIZATION

    def test_network_error(self):
        c = FailureClassifier()
        result = c.classify("net::ERR_CONNECTION_REFUSED")
        assert result.family == FailureFamily.ENVIRONMENT

    def test_unknown_fallback(self):
        c = FailureClassifier()
        result = c.classify("something completely unexpected happened here")
        assert result.family == FailureFamily.CONTEXT
        assert result.code == "UNKNOWN"


class TestShadowValidator:
    def test_suggests_for_locator_failure(self):
        sv = ShadowValidator(None)  # no page needed for this test
        sv._page = None
        candidates = [{"selector": "#btn", "score": 0.95}, {"selector": "button", "score": 0.80}]
        suggestion = sv.evaluate_failure(
            "step_1", "locator not found",
            original_selector="#old-id", candidates=candidates
        )
        assert suggestion is not None
        assert suggestion.mode == "shadow"
        assert suggestion.status == "pending_review"
        assert suggestion.failure.code == "LOCATOR_NOT_FOUND"

    def test_no_suggest_for_oracle_fail(self):
        sv = ShadowValidator(None)
        sv._page = None
        suggestion = sv.evaluate_failure("step_1", "oracle assertion failed")
        assert suggestion is None

    def test_pending_reviews(self):
        sv = ShadowValidator(None)
        sv._page = None
        candidates = [{"selector": "#btn", "score": 0.9}]
        s1 = sv.evaluate_failure("s1", "locator not found", candidates=candidates)
        s2 = sv.evaluate_failure("s2", "overlay obscured")
        if s1:
            sv.add_suggestion(s1)
        if s2:
            sv.add_suggestion(s2)
        pending = sv.pending_reviews()
        assert len(pending) >= 1


class TestFallbackRunner:
    def test_fill_fallback_success(self, page: Page):
        page.set_content('<input id="real" placeholder="test">')
        fr = FallbackRunner(page)
        candidates = [
            {"selector": "#fake", "score": 0.9},
            {"selector": "#real", "score": 0.8},
        ]
        ok = fr.try_fill(candidates, "hello")
        assert ok

    def test_fill_all_fail(self, page: Page):
        page.set_content("<input id='x'>")
        fr = FallbackRunner(page)
        candidates = [{"selector": "#y", "score": 0.9}]
        ok = fr.try_fill(candidates, "hello")
        assert not ok

    def test_click_fallback(self, page: Page):
        page.set_content('<button id="btn">OK</button>')
        fr = FallbackRunner(page)
        candidates = [{"selector": "#btn", "score": 0.9}]
        ok = fr.try_click(candidates)
        assert ok

    def test_click_with_fallback_strings(self, page: Page):
        page.set_content('<button id="ok">Go</button>')
        fr = FallbackRunner(page)
        ok, used = fr.try_click_with_fallback("#nope", ["#ok"])
        assert ok
        assert used == "#ok"
