"""Tests for centralized browser launch with fallback chain."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from testforge.browser import (
    BrowserType,
    _FALLBACK_CHAIN,
    _reorder_chain,
    launch_browser,
)


# ── _reorder_chain tests ──────────────────────────────────────────────


class TestReorderChain:
    """Test fallback chain reordering for browser preferences."""

    def test_prefer_chromium_moves_chromium_first(self):
        """When preferred=browser=chromium, bare chromium launch is first."""
        result = _reorder_chain("chromium", headless=False)
        assert result[0][0] == "chromium"
        assert result[0][1] == {"headless": False}
        assert len(result) == 3
        # Remaining entries unchanged
        assert result[1][0] == "msedge"
        assert result[2][0] == "chrome"

    def test_prefer_chrome_moves_chrome_first(self):
        """When preferred=browser=chrome, channel=chrome runs first."""
        result = _reorder_chain("chrome", headless=True)
        assert result[0][0] == "chrome"
        assert result[0][1] == {"channel": "chrome", "headless": True}
        assert len(result) == 3

    def test_prefer_edge_moves_msedge_first(self):
        """Edge maps to channel=msedge internally; moves it to front."""
        result = _reorder_chain("edge", headless=False)
        assert result[0][0] == "msedge"
        assert result[0][1] == {"channel": "msedge", "headless": False}
        assert len(result) == 3

    def test_all_entries_present_after_reorder(self):
        """Reordering preserves all 3 strategies (no duplicates or drops)."""
        for preferred in ("chromium", "chrome", "edge"):
            result = _reorder_chain(preferred, headless=False)
            names = [name for name, _ in result]
            assert sorted(names) == ["chrome", "chromium", "msedge"], (
                f"Missing entries for preferred={preferred}"
            )

    def test_headless_propagates_to_all_entries(self):
        """--headless flag applies to every strategy in the chain."""
        result = _reorder_chain("chromium", headless=True)
        for _, kwargs in result:
            assert kwargs["headless"] is True

    def test_non_headless_propagates_false(self):
        result = _reorder_chain("edge", headless=False)
        for _, kwargs in result:
            assert kwargs["headless"] is False

    def test_unknown_browser_defaults_to_chromium_first(self):
        """Invalid browser_type falls back to chromium-first ordering."""
        result = _reorder_chain("firefox", headless=False)  # type: ignore[arg-type]
        assert result[0][0] == "chromium"
        assert len(result) == 3


# ── launch_browser tests ──────────────────────────────────────────────


class TestLaunchBrowser:
    """Test launch_browser with mocked Playwright."""

    @pytest.fixture
    def mock_pw(self):
        """Return a mock Playwright instance with chromium.launch and .connect_over_cdp."""
        pw = MagicMock()
        pw.chromium.launch = MagicMock()
        pw.chromium.connect_over_cdp = MagicMock()
        return pw

    def test_first_strategy_succeeds(self, mock_pw):
        """When preferred browser launches, returns it immediately."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.return_value = expected_browser

        result = launch_browser(mock_pw, "chromium", headless=False)

        assert result is expected_browser
        mock_pw.chromium.launch.assert_called_once_with(headless=False)
        mock_pw.chromium.connect_over_cdp.assert_not_called()

    def test_edge_preferred_launches_msedge_first(self, mock_pw):
        """--browser edge tries channel=msedge before chromium/chrome."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.return_value = expected_browser

        result = launch_browser(mock_pw, "edge", headless=True)

        assert result is expected_browser
        mock_pw.chromium.launch.assert_called_once_with(
            channel="msedge", headless=True
        )

    def test_first_fails_second_succeeds(self, mock_pw):
        """Fallback: if first strategy fails, tries next in chain."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.side_effect = [
            RuntimeError("chromium not found"),  # 1st fails
            expected_browser,                     # 2nd (msedge) succeeds
        ]

        result = launch_browser(mock_pw, "chromium", headless=False)

        assert result is expected_browser
        assert mock_pw.chromium.launch.call_count == 2
        # First call: bare chromium; second call: msedge
        from unittest.mock import call
        mock_pw.chromium.launch.assert_has_calls([
            call(headless=False),
            call(channel="msedge", headless=False),
        ])

    def test_all_launch_fail_cdp_succeeds(self, mock_pw):
        """When all launch strategies fail, falls back to connect_over_cdp."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.side_effect = RuntimeError("nope")
        mock_pw.chromium.connect_over_cdp.return_value = expected_browser

        result = launch_browser(
            mock_pw, "chromium", headless=False, cdp_url="http://localhost:9222"
        )

        assert result is expected_browser
        assert mock_pw.chromium.launch.call_count == 3
        mock_pw.chromium.connect_over_cdp.assert_called_once_with(
            "http://localhost:9222"
        )

    def test_all_strategies_fail_raises_runtime_error(self, mock_pw):
        """When every strategy including CDP fails, raises RuntimeError."""
        mock_pw.chromium.launch.side_effect = [
            RuntimeError("no chromium"),
            RuntimeError("no msedge"),
            RuntimeError("no chrome"),
        ]
        mock_pw.chromium.connect_over_cdp.side_effect = RuntimeError("cdp refused")

        with pytest.raises(RuntimeError, match="All browser launch strategies failed"):
            launch_browser(mock_pw, "chromium", headless=False)

        assert mock_pw.chromium.launch.call_count == 3
        mock_pw.chromium.connect_over_cdp.assert_called_once()

    def test_chrome_preferred_reorders_chain(self, mock_pw):
        """--browser chrome moves channel=chrome to first position."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.return_value = expected_browser

        launch_browser(mock_pw, "chrome", headless=False)

        mock_pw.chromium.launch.assert_called_once_with(
            channel="chrome", headless=False
        )

    def test_cdp_with_custom_port(self, mock_pw):
        """Custom CDP URL is respected in the last-resort fallback."""
        expected_browser = MagicMock()
        mock_pw.chromium.launch.side_effect = RuntimeError("fail")
        mock_pw.chromium.connect_over_cdp.return_value = expected_browser

        result = launch_browser(
            mock_pw, "chromium", headless=False, cdp_url="http://192.168.1.100:9333"
        )

        assert result is expected_browser
        mock_pw.chromium.connect_over_cdp.assert_called_once_with(
            "http://192.168.1.100:9333"
        )

    def test_launch_browser_type_annotation(self):
        """BrowserType literal accepts only valid values at type-check time."""
        valid: BrowserType
        valid = "chromium"
        valid = "chrome"
        valid = "edge"
        assert valid in ("chromium", "chrome", "edge")


# ── Fallback chain structure ──────────────────────────────────────────


class TestFallbackChainStructure:
    """Structural invariants of the fallback chain."""

    def test_chain_has_three_entries(self):
        assert len(_FALLBACK_CHAIN) == 3

    def test_chain_entries_are_callable_builders(self):
        for name, builder in _FALLBACK_CHAIN:
            assert callable(builder)
            kwargs = builder(headless=False)
            assert "headless" in kwargs

    def test_msedge_uses_channel_msedge(self):
        _, builder = _FALLBACK_CHAIN[1]  # msedge is index 1
        kwargs = builder(headless=True)
        assert kwargs["channel"] == "msedge"
        assert kwargs["headless"] is True

    def test_chrome_uses_channel_chrome(self):
        _, builder = _FALLBACK_CHAIN[2]  # chrome is index 2
        kwargs = builder(headless=True)
        assert kwargs["channel"] == "chrome"
        assert kwargs["headless"] is True

    def test_chromium_bare_has_no_channel(self):
        _, builder = _FALLBACK_CHAIN[0]
        kwargs = builder(headless=True)
        assert "channel" not in kwargs
