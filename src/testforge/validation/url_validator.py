"""URL validation — warn about unquoted ampersands and truncated URLs.

Problem: shell interprets & as background operator. User runs:
  tf record http://example.com/page?arg=1&other=2
Shell splits at &, CLI receives only http://example.com/page?arg=1

This validator detects the common symptoms of an unquoted URL.
"""

from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import re


@dataclass
class UrlWarning:
    """A validation warning for a URL that may be malformed due to shell processing."""

    message: str
    is_critical: bool = False
    url: str = ""


class UrlValidator:
    """Validates URLs for common shell-truncation issues."""

    # URL must match this to be considered a valid http/https URL
    _URL_RE = re.compile(r"^https?://", re.IGNORECASE)

    def validate(self, url: str) -> list[UrlWarning]:
        """Validate a URL and return list of warnings.

        Args:
            url: The URL string to validate.

        Returns:
            List of UrlWarning objects. Empty list means no warnings.
        """
        warnings: list[UrlWarning] = []

        if not url or not url.strip():
            warnings.append(UrlWarning("URL is empty", is_critical=True, url=url))
            return warnings

        url = url.strip()

        # Detect direct ampersand in URL — almost certainly unquoted shell input.
        # The shell would have already stripped everything after & so this only
        # triggers when ampersand appears within the remaining fragment.
        if "&" in url:
            warnings.append(
                UrlWarning(
                    "URL contains '&' character. "
                    "If using shell, wrap URL in quotes to prevent truncation "
                    "at ampersand (shell background operator). "
                    f"Current URL may be incomplete or truncated: {url}",
                    is_critical=True,
                    url=url,
                )
            )

        # Detect truncated URLs — symptoms of shell ampersand split.
        truncation_warnings = self._detect_truncation(url)
        warnings.extend(truncation_warnings)

        # Validate URL scheme.
        if not self._URL_RE.match(url):
            warnings.append(
                UrlWarning(
                    f"URL does not start with http:// or https://: {url}",
                    is_critical=False,
                    url=url,
                )
            )

        return warnings

    def _detect_truncation(self, url: str) -> list[UrlWarning]:
        """Detect symptoms of a URL truncated by shell ampersand processing."""
        warnings: list[UrlWarning] = []

        try:
            parsed = urlparse(url)
        except Exception:
            return warnings

        # Symptom 1: query string ends with = (parameter name without value).
        if parsed.query and parsed.query.endswith("="):
            warnings.append(
                UrlWarning(
                    "URL query string ends with '=' — possible truncation. "
                    "Did the shell strip everything after an unquoted '&'? "
                    f"Query: ?{parsed.query}",
                    is_critical=True,
                    url=url,
                )
            )

        # Symptom 2: query string has parameter names without values.
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            for name, values in params.items():
                if not values or all(v == "" for v in values):
                    warnings.append(
                        UrlWarning(
                            f"Query parameter '{name}' has no value — "
                            "possible truncation after shell ampersand split.",
                            is_critical=True,
                            url=url,
                        )
                    )

        # Symptom 3: URL ends with ? (query string started but got truncated).
        if url.rstrip().endswith("?"):
            warnings.append(
                UrlWarning(
                    "URL ends with '?' — query string appears truncated. "
                    "Wrap URL in quotes when using shell.",
                    is_critical=True,
                    url=url,
                )
            )

        # Symptom 4: URL ends with = (parameter assignment truncated).
        if url.rstrip().endswith("="):
            warnings.append(
                UrlWarning(
                    "URL ends with '=' — parameter value appears truncated. "
                    "Wrap URL in quotes when using shell.",
                    is_critical=True,
                    url=url,
                )
            )

        return warnings

    def is_valid(self, url: str) -> bool:
        """Check if URL passes validation without critical warnings."""
        warnings = self.validate(url)
        return not any(w.is_critical for w in warnings)


def validate_url(url: str) -> list[UrlWarning]:
    """Convenience function to validate a URL and return warnings.

    Args:
        url: The URL string to validate.

    Returns:
        List of UrlWarning objects. Empty list means no warnings.
    """
    return UrlValidator().validate(url)
