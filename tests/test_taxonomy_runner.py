"""Testes da Taxonomia, ShadowValidator e FallbackRunner."""
from playwright.sync_api import Page

from testforge.taxonomy import FailureClassifier, FailureFamily
from testforge.runner import ShadowValidator, FallbackRunner


class TestFailureClassifier:
    def test_locator_not_found(self):
        c = FailureClassifier()
        result = c.classify("element not found", {"count": 0})
        assert result.family == FailureFamily.LOCATOR_RESOLUTION
        assert result.code == "SEL-004"
        assert result.confidence == 0.9
        assert result.matched_by == "keyword"

    def test_locator_ambiguous(self):
        c = FailureClassifier()
        result = c.classify("multiple elements found for strict locator", {"count": 5})
        assert result.family == FailureFamily.LOCATOR_RESOLUTION
        assert result.code == "SEL-009"

    def test_overlay_obscured(self):
        c = FailureClassifier()
        result = c.classify("element is obscured by overlay")
        assert result.family == FailureFamily.STATE
        assert result.code == "STA-002"

    def test_disabled(self):
        c = FailureClassifier()
        result = c.classify("element is not enabled. disabled")
        assert result.family == FailureFamily.STATE
        assert result.code == "STA-002"

    def test_timeout(self):
        c = FailureClassifier()
        result = c.classify("Timeout waiting for selector")
        assert result.family == FailureFamily.SYNCHRONIZATION
        assert result.code == "TIM-005"

    def test_network_error(self):
        c = FailureClassifier()
        result = c.classify("net::ERR_CONNECTION_REFUSED")
        assert result.family == FailureFamily.SYNCHRONIZATION
        assert result.code == "TIM-003"

    def test_stale_element(self):
        c = FailureClassifier()
        result = c.classify("stale element reference: element is not attached")
        assert result.family == FailureFamily.DYNAMIC_DOM
        assert result.code == "DOM-001"

    def test_captcha(self):
        c = FailureClassifier()
        result = c.classify("captcha challenge required")
        assert result.family == FailureFamily.BROWSER_LIMITS
        assert result.code == "LIM-001"
        assert result.recoverable is False

    def test_unknown_fallback(self):
        c = FailureClassifier()
        result = c.classify("something completely unexpected happened here")
        assert result.family == FailureFamily.EXECUTION
        assert result.code == "OBS-001"
        assert result.confidence == 0.0
        assert result.matched_by == ""

    def test_group_fallback(self):
        """Sem keyword match — cai no group fallback (regex)."""
        c = FailureClassifier()
        result = c.classify("the iframe inside the modal reloaded after submit")
        # "iframe" matches keyword, should be FAM-03
        assert result.family == FailureFamily.CONTEXT_SCOPE
        assert result.confidence == 0.9  # keyword match

    def test_family_code_property(self):
        c = FailureClassifier()
        result = c.classify("element not found")
        assert result.family_code == "FAM-01"

    def test_legacy_codes_still_in_catalog(self):
        """Legacy codes still accessible via KNOWN_FAILURES dict."""
        from testforge.taxonomy import KNOWN_FAILURES
        assert "LOCATOR_NOT_FOUND" in KNOWN_FAILURES
        assert "TIMEOUT" in KNOWN_FAILURES
        assert "ORACLE_FAILED" in KNOWN_FAILURES
        assert "NETWORK_ERROR" in KNOWN_FAILURES


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
        assert suggestion.failure.code == "SEL-004"

    def test_no_suggest_for_oracle_fail(self):
        sv = ShadowValidator(None)
        sv._page = None
        suggestion = sv.evaluate_failure("step_1", "oracle assertion failed")
        assert suggestion is None

    def test_state_failure_keeps_original_selector(self):
        """Falhas de estado (overlay) mantem seletor original, status shadow."""
        sv = ShadowValidator(None)
        sv._page = None
        suggestion = sv.evaluate_failure(
            "step_1", "element is obscured by overlay",
            original_selector="#btn-foo", candidates=[]
        )
        assert suggestion is not None
        assert suggestion.suggested_selector == "#btn-foo"  # unchanged
        assert suggestion.failure.family == FailureFamily.STATE

    def test_pending_reviews(self):
        sv = ShadowValidator(None)
        sv._page = None
        candidates = [{"selector": "#btn", "score": 0.9}]
        s1 = sv.evaluate_failure("s1", "element not found", candidates=candidates)
        s2 = sv.evaluate_failure("s2", "element is obscured by overlay")
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
