"""RC-7 regression: framework detection must retry when DOM not yet populated.

Before fix: Angular SPA returns primary='unknown' on first call because
Angular bootstrap not complete yet (interactive_elements=0).

Fix: detect() retries _detect_once() up to 3x with 500ms delay when
primary==unknown AND interactive_elements < 5 AND no bundle evidence.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from testforge.diagnostic.framework_detector import FrameworkDetector


def _detector_with_page(url="http://app/"):
    page = MagicMock()
    page.url = url
    return FrameworkDetector(page)


@pytest.mark.unit
class TestFrameworkDetectorRetry:
    def test_no_retry_when_framework_detected_on_first_call(self):
        """RC-7: no retry wasted when first detect() succeeds."""
        det = _detector_with_page()
        angular_result = {
            "primary": "angular-material",
            "interactive_elements": 20,
            "angular_version": "16.0.0",
            "angular_material": True,
            "angular": True,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 100,
            "max_depth": 10, "form_count": 2,
            "evidence": ["bundle[angular]:runtime.angular-16.0.0.js"],
        }
        with patch.object(det, "_detect_once", return_value=angular_result) as mock:
            result = det.detect()

        mock.assert_called_once()
        assert result["primary"] == "angular-material"

    def test_retries_when_unknown_and_dom_empty(self):
        """RC-7: detect() retries up to 3x when primary=unknown + empty DOM."""
        det = _detector_with_page()
        unknown = {
            "primary": "unknown",
            "interactive_elements": 2,
            "angular_version": None, "angular_material": False,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 3,
            "max_depth": 2, "form_count": 0,
            "evidence": [],
        }
        angular = {**unknown, "primary": "angular", "interactive_elements": 15,
                   "angular": True, "angular_version": "15.0.0",
                   "evidence": ["window.ng present"]}

        with patch.object(det, "_detect_once", side_effect=[unknown, angular]) as mock, \
             patch("time.sleep") as sleep_mock:
            result = det.detect()

        assert mock.call_count == 2
        assert result["primary"] == "angular"
        sleep_mock.assert_called_once_with(0.5)

    def test_stops_retrying_after_3_attempts(self):
        """RC-7: max 3 retries even if DOM stays empty."""
        det = _detector_with_page()
        unknown = {
            "primary": "unknown",
            "interactive_elements": 0,
            "angular_version": None, "angular_material": False,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 1,
            "max_depth": 1, "form_count": 0,
            "evidence": [],
        }
        with patch.object(det, "_detect_once", return_value=unknown) as mock, \
             patch("time.sleep"):
            result = det.detect()

        assert mock.call_count == 4  # 1 initial + 3 retries
        assert result["primary"] == "unknown"

    def test_no_retry_when_bundle_evidence_present(self):
        """RC-7: no retry when bundle evidence exists (Angular loading slowly)."""
        det = _detector_with_page()
        unknown_with_bundle = {
            "primary": "unknown",
            "interactive_elements": 0,
            "angular_version": None, "angular_material": False,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 1,
            "max_depth": 1, "form_count": 0,
            "evidence": ["bundle[angular]:runtime.angular-16.js"],
        }
        with patch.object(det, "_detect_once", return_value=unknown_with_bundle) as mock, \
             patch("time.sleep") as sleep_mock:
            result = det.detect()

        mock.assert_called_once()
        sleep_mock.assert_not_called()
        assert result["primary"] == "unknown"

    def test_no_retry_when_page_eval_failed(self):
        """RC-7: no retry when page evaluation itself failed (page closed)."""
        det = _detector_with_page()
        page_failed = {
            "primary": "unknown",
            "interactive_elements": 0,
            "angular_version": None, "angular_material": False,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 0,
            "max_depth": 0, "form_count": 0,
            "evidence": ["page_eval_failed: Target closed"],
        }
        with patch.object(det, "_detect_once", return_value=page_failed) as mock, \
             patch("time.sleep") as sleep_mock:
            result = det.detect()

        mock.assert_called_once()
        sleep_mock.assert_not_called()

    def test_retry_adds_evidence_tag(self):
        """RC-7: successful retry adds evidence tag for observability."""
        det = _detector_with_page()
        unknown = {
            "primary": "unknown", "interactive_elements": 1,
            "angular_version": None, "angular_material": False,
            "primefaces": False, "mui": False, "vue": None, "react": None,
            "jsf": False, "zone_js": False, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 2,
            "max_depth": 1, "form_count": 0, "evidence": [],
        }
        success = {**unknown, "primary": "angular", "interactive_elements": 10,
                   "evidence": []}

        with patch.object(det, "_detect_once", side_effect=[unknown, success]), \
             patch("time.sleep"):
            result = det.detect()

        assert any("framework_retry_succeeded_attempt_1" in e
                   for e in result.get("evidence", []))
