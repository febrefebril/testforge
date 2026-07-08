"""RC-8 regression: URL drift false-positive normalization.

Symptom: raw string compare causes inconsistent results when same URL has
different query param ordering across requests.

Fix: normalize URL before compare — sort query params. Fragment is kept
(fragment change = SPA navigation = valid URL change).

Scenario A (false positive PASS before fix): URL with reordered query params
was treated as navigation → passed=True. After fix: normalized to same URL →
treated as SPA no-nav.

Scenario B (correct detection): fragment change (`/calc` → `/calc#result`)
correctly detected as navigation → passed=True.
"""
import pytest
from unittest.mock import MagicMock

from testforge.runner.step_postcondition import StepPostconditionValidator, _normalize_url_for_compare


def _mock_page(url):
    page = MagicMock()
    page.url = url
    page.wait_for_selector.side_effect = Exception("not found")
    return page


def _nav_step():
    step = MagicMock()
    step.action = "click"
    step.context = {"causes_navigation": True}
    step.target = None
    return step


# ---------------------------------------------------------------------------
# Unit tests for _normalize_url_for_compare

@pytest.mark.unit
class TestNormalizeUrlForCompare:
    def test_identical_simple_urls_equal(self):
        url = "http://example.com/page"
        assert _normalize_url_for_compare(url) == _normalize_url_for_compare(url)

    def test_fragment_kept_different_from_no_fragment(self):
        """Fragment is navigation — kept for comparison."""
        a = "http://example.com/page"
        b = "http://example.com/page#section"
        assert _normalize_url_for_compare(a) != _normalize_url_for_compare(b)

    def test_query_param_order_normalized(self):
        a = "http://example.com/page?b=2&a=1"
        b = "http://example.com/page?a=1&b=2"
        assert _normalize_url_for_compare(a) == _normalize_url_for_compare(b)

    def test_different_paths_not_equal(self):
        a = "http://example.com/form"
        b = "http://example.com/result"
        assert _normalize_url_for_compare(a) != _normalize_url_for_compare(b)

    def test_empty_string(self):
        assert _normalize_url_for_compare("") == ""

    def test_query_sorted_fragment_preserved(self):
        """Query params sorted, fragment unchanged."""
        a = "http://x.com/p?z=3&a=1#top"
        b = "http://x.com/p?a=1&z=3#top"
        assert _normalize_url_for_compare(a) == _normalize_url_for_compare(b)


# ---------------------------------------------------------------------------
# Integration tests with StepPostconditionValidator

@pytest.mark.unit
class TestUrlDriftNormalization:
    def test_fragment_change_detected_as_navigation(self):
        """RC-8: fragment-only URL change counts as SPA navigation → passed=True.

        Angular SPA adds #resultado after submit. Fragment is real navigation.
        """
        before = "http://example.com/simulador/calc"
        after  = "http://example.com/simulador/calc#resultado"
        page = _mock_page(after)
        val = StepPostconditionValidator(page)
        step = _nav_step()

        result = val.validate(step, url_before=before)

        assert result.passed is True, (
            f"RC-8: fragment nav must be PASS. Got: passed={result.passed}, "
            f"failures={result.failures}"
        )
        assert result.checks.get("url_changed") is True

    def test_query_reorder_normalized_to_same_url(self):
        """RC-8: query param reorder must NOT be treated as navigation (false positive pass).

        Before fix: raw string compare → changed=True → passed=True (false positive).
        After fix: normalized → same URL → changed=False → SPA handling.
        SPA fallback with no next_step → passed=False (correct: no nav happened).
        """
        before = "http://app.com/page?session=abc&tab=1"
        after  = "http://app.com/page?tab=1&session=abc"
        page = _mock_page(after)
        val = StepPostconditionValidator(page)
        step = _nav_step()

        result = val.validate(step, url_before=before)

        # After normalization: same URL → changed=False → SPA handling fails
        # This is CORRECT — no real navigation happened
        assert "url_not_changed" in result.failures, (
            "RC-8: query reorder must not produce false positive PASS"
        )

    def test_truly_different_url_still_passes(self):
        """Sanity: real URL change with causes_navigation must still pass."""
        page = _mock_page("http://app.com/result")
        val = StepPostconditionValidator(page)
        step = _nav_step()

        result = val.validate(step, url_before="http://app.com/form")

        assert result.passed is True
        assert result.checks.get("url_changed") is True

    def test_unchanged_url_with_nav_expected_still_fails(self):
        """Existing behavior preserved: URL truly unchanged with navigation expected = fail."""
        url = "http://localhost/same"
        page = _mock_page(url)
        val = StepPostconditionValidator(page)
        step = _nav_step()

        result = val.validate(step, url_before=url)

        assert "url_not_changed" in result.failures
