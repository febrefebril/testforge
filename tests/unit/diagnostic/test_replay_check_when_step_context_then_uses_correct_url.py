"""RC-6 regression: ReplayCheck.drain() must navigate to step URL before probing.

Before fix: drain() called _do_check() against whatever DOM was current
(final recording URL). Steps from earlier pages always returned resolved=False
because those elements no longer existed.

Fix: store capture URL with each pending step; navigate before probing.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from testforge.diagnostic.replay_check import ReplayCheck


def _page_finds(url="http://x/page1"):
    page = MagicMock()
    page.url = url
    loc = MagicMock()
    loc.count.return_value = 1
    page.locator.return_value = loc
    return page


def _page_misses(url="http://x/final"):
    page = MagicMock()
    page.url = url
    loc = MagicMock()
    loc.count.return_value = 0
    page.locator.return_value = loc
    return page


@pytest.mark.unit
class TestReplayCheckUrlContext:
    def test_batched_stores_capture_url(self):
        """RC-6: each pending step stores the URL at time of capture."""
        page = _page_finds("http://x/form")
        rc = ReplayCheck(page, mode="batched")

        rc.check("step_001", [{"strategy": "css", "selector": "#name", "score": 0.8}])

        assert len(rc._pending) == 1
        sid, cands, url = rc._pending[0]
        assert sid == "step_001"
        assert url == "http://x/form"

    def test_drain_navigates_when_url_differs(self):
        """RC-6: drain() calls page.goto when step URL != current URL."""
        page = _page_finds("http://x/form")
        rc = ReplayCheck(page, mode="batched")

        rc.check("step_001", [{"strategy": "css", "selector": "#ok", "score": 0.9}])

        # Simulate page moved to final URL
        page.url = "http://x/final"
        page.goto.return_value = None

        with patch.object(rc, "_do_check", return_value={"step_id": "step_001", "resolved": True}) as mock_check:
            drained = rc.drain()

        page.goto.assert_called_once_with(
            "http://x/form", timeout=5000, wait_until="domcontentloaded"
        )
        mock_check.assert_called_once()
        assert len(drained) == 1

    def test_drain_skips_goto_when_url_same(self):
        """RC-6: drain() must NOT navigate when page already on correct URL."""
        page = _page_finds("http://x/form")
        rc = ReplayCheck(page, mode="batched")

        rc.check("step_001", [{"strategy": "css", "selector": "#ok", "score": 0.9}])

        # Page stays on same URL
        page.goto.return_value = None

        with patch.object(rc, "_do_check", return_value={"step_id": "step_001", "resolved": True}):
            rc.drain()

        page.goto.assert_not_called()

    def test_drain_records_url_context_unavailable_on_nav_failure(self):
        """RC-6: if navigation fails, step is marked url_context_unavailable, not crash."""
        page = _page_finds("http://x/form")
        rc = ReplayCheck(page, mode="batched")

        rc.check("step_001", [{"strategy": "css", "selector": "#ok", "score": 0.9}])

        page.url = "http://x/final"
        page.goto.side_effect = Exception("net::ERR_CONNECTION_REFUSED")

        drained = rc.drain()

        assert len(drained) == 1
        rec = drained[0]
        assert rec["resolved"] is False
        assert "url_context_unavailable" in rec["error"]

    def test_drain_handles_multiple_steps_different_urls(self):
        """RC-6: drain navigates to each step's URL in sequence."""
        page = MagicMock()
        page.url = "http://x/final"
        page.goto.return_value = None

        rc = ReplayCheck(page, mode="batched")

        # Simulate two steps captured at different URLs
        page.url = "http://x/step1"
        rc.check("step_001", [{"strategy": "css", "selector": "#a", "score": 0.8}])
        page.url = "http://x/step2"
        rc.check("step_002", [{"strategy": "css", "selector": "#b", "score": 0.8}])

        page.url = "http://x/final"

        with patch.object(rc, "_do_check", return_value={"step_id": "x", "resolved": True}):
            rc.drain()

        assert page.goto.call_count == 2
        urls_navigated = [c.args[0] for c in page.goto.call_args_list]
        assert "http://x/step1" in urls_navigated
        assert "http://x/step2" in urls_navigated

    def test_drain_clears_pending_after_run(self):
        """RC-6: pending queue cleared even when nav fails."""
        page = _page_finds("http://x/form")
        rc = ReplayCheck(page, mode="batched")
        rc.check("s1", [{"strategy": "css", "selector": "#a", "score": 0.5}])

        page.url = "http://x/other"
        page.goto.side_effect = Exception("timeout")

        rc.drain()

        assert rc._pending == []
        assert rc.drain() == []
