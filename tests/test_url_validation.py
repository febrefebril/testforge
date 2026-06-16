"""Tests for URL validation — unquoted ampersand and truncation detection."""

import pytest
from testforge.validation.url_validator import UrlValidator, validate_url


class TestUrlValidator:
    """Unit tests for UrlValidator."""

    @pytest.fixture
    def validator(self):
        return UrlValidator()

    # --- Valid URLs (no warnings) ---

    def test_valid_https_url_no_warnings(self, validator):
        """Simple HTTPS URL should produce no warnings."""
        warnings = validator.validate("https://example.com/page")
        assert len(warnings) == 0

    def test_valid_http_localhost_no_warnings(self, validator):
        """Localhost URL should produce no warnings."""
        warnings = validator.validate("http://localhost:8765")
        assert len(warnings) == 0

    def test_valid_url_with_query_params_no_warnings(self, validator):
        """URL with properly quoted query parameters should be fine."""
        warnings = validator.validate("https://example.com/search?q=hello&page=1&sort=asc")
        assert len(warnings) == 1  # & present → warning expected
        assert warnings[0].is_critical

    def test_empty_url_is_critical(self, validator):
        """Empty URL should produce a critical warning."""
        warnings = validator.validate("")
        assert len(warnings) == 1
        assert warnings[0].is_critical

    def test_whitespace_only_url_is_critical(self, validator):
        """Whitespace-only URL should produce a critical warning."""
        warnings = validator.validate("   ")
        assert len(warnings) >= 1
        assert warnings[0].is_critical

    # --- Ampersand detection ---

    def test_url_with_ampersand_warns(self, validator):
        """URL containing & should produce a critical warning."""
        warnings = validator.validate("http://example.com/page?arg=1&other=2")
        assert len(warnings) >= 1
        assert any("&" in w.message for w in warnings)
        assert any(w.is_critical for w in warnings)

    def test_url_with_multiple_ampersands_warns(self, validator):
        """URL with multiple & should still warn."""
        warnings = validator.validate("http://example.com?a=1&b=2&c=3")
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 1
        assert any("&" in w.message for w in critical)

    # --- Truncation: query ends with = ---

    def test_query_ends_with_equals_is_truncated(self, validator):
        """Query string ending with = indicates truncation."""
        warnings = validator.validate("http://example.com/page?arg=")
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 1
        assert any("ends with '='" in w.message for w in critical)

    def test_url_ends_with_equals_is_truncated(self, validator):
        """URL ending with = (no ?) also indicates truncation."""
        warnings = validator.validate("http://example.com/page?arg=1&other=")
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 2  # ampersand warning + truncation warning
        assert any("ends with '='" in w.message for w in critical)

    # --- Truncation: URL ends with ? ---

    def test_url_ending_with_question_mark_is_truncated(self, validator):
        """URL ending with ? indicates truncated query string."""
        warnings = validator.validate("http://example.com/page?")
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 1
        assert any("ends with '?'" in w.message for w in critical)

    # --- Truncation: parameter without value ---

    def test_query_param_no_value_is_truncated(self, validator):
        """Query parameter with empty value (after shell truncation)."""
        warnings = validator.validate("http://example.com/page?arg=1&other")
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 1
        assert any("no value" in w.message for w in critical)

    # --- No scheme warning ---

    def test_missing_scheme_warns_non_critical(self, validator):
        """URL without http/https produces a non-critical warning."""
        warnings = validator.validate("localhost:8765")
        non_critical = [w for w in warnings if not w.is_critical]
        assert len(non_critical) >= 1
        assert any("http://" in w.message for w in non_critical)

    def test_ftp_url_warns_non_critical(self, validator):
        """URL with wrong scheme produces non-critical warning."""
        warnings = validator.validate("ftp://example.com")
        # ftp not matching http/https
        assert any("http://" in w.message for w in warnings if not w.is_critical)

    # --- is_valid helper ---

    def test_is_valid_returns_true_for_good_url(self, validator):
        """is_valid should return True for clean URLs."""
        assert validator.is_valid("https://example.com/page")

    def test_is_valid_returns_false_for_truncated_url(self, validator):
        """is_valid should return False for truncated URLs."""
        assert not validator.is_valid("http://example.com/page?arg=")

    def test_is_valid_returns_false_for_ampersand_url(self, validator):
        """is_valid should return False for URLs with ampersand."""
        assert not validator.is_valid("http://example.com/page?a=1&b=2")

    # --- Convenience function ---

    def test_validate_url_convenience_function(self):
        """validate_url() convenience function works."""
        warnings = validate_url("https://example.com")
        assert len(warnings) == 0

    # --- URL with properly encoded ampersand (%26) ---

    def test_encoded_ampersand_does_not_warn(self, validator):
        """URL-encoded ampersand (%26) should not trigger the raw & warning."""
        warnings = validator.validate("https://example.com/search?q=hello%26world")
        critical = [w for w in warnings if w.is_critical and "&" in w.message]
        assert len(critical) == 0

    # --- Real-world truncation scenarios ---

    def test_aspnet_postback_truncation(self, validator):
        """ASP.NET __doPostBack URL truncated at &."""
        url = "http://example.com/page?__doPostBack=ctl00$MainContent$btnSave"
        # If truncated by shell: http://example.com/page?__doPostBack=ctl00$MainContent$btnSave
        # This has no & so should be fine unless there's an = end truncation
        warnings = validator.validate(url)
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) == 0

    def test_google_search_truncation(self, validator):
        """Simulate Google search URL truncated at &."""
        url = "http://example.com/search?q=test&"
        warnings = validator.validate(url)
        critical = [w for w in warnings if w.is_critical]
        assert len(critical) >= 1

    def test_multiple_truncation_symptoms(self, validator):
        """URL with both & and = truncation signs."""
        url = "http://example.com/api?token=abc123&user="
        warnings = validator.validate(url)
        critical = [w for w in warnings if w.is_critical]
        # Should have: ampersand warning + ends with = warning + query ends with = warning
        assert len(critical) >= 2
