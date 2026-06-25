"""Hotfix 6 — wait for CDK overlay before clicking datepicker dates."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from testforge.runner.step_executor import _inside_cdk_overlay


class TestInsideCdkOverlay:
    @pytest.mark.parametrize("selector,expected", [
        ("div.cdk-overlay-container button", True),
        ("mat-calendar .mat-day", True),
        ("mat-datepicker-content .day", True),
        ("mat-dialog-container button", True),
        ("mat-autocomplete-panel mat-option", True),
        ("button.primary", False),
        ("#user-email", False),
        ("[data-testid='x']", False),
        ("", False),
        (None, False),
    ])
    def test_detection(self, selector, expected):
        assert _inside_cdk_overlay(selector) == expected


class TestExecuteClickWaitsForOverlay:
    def _executor(self, page):
        from testforge.runner.step_executor import StepExecutor
        return StepExecutor(page)

    def _step(self):
        s = MagicMock()
        s.action = "click"
        return s

    def test_wait_called_when_selector_inside_overlay(self):
        page = MagicMock()
        page.wait_for_selector = MagicMock()
        page.wait_for_timeout = MagicMock()
        page.click = MagicMock()
        page.locator = MagicMock()
        exe = self._executor(page)
        exe._execute_click(self._step(), ["mat-calendar td.mat-day"])
        page.wait_for_selector.assert_called_once()
        args, kwargs = page.wait_for_selector.call_args
        assert ".cdk-overlay-container" in args[0]
        assert kwargs["state"] == "visible"
        page.click.assert_called_once_with("mat-calendar td.mat-day", timeout=exe.DEFAULT_TIMEOUT)

    def test_wait_skipped_when_selector_outside_overlay(self):
        page = MagicMock()
        page.wait_for_selector = MagicMock()
        page.click = MagicMock()
        exe = self._executor(page)
        exe._execute_click(self._step(), ["button#login"])
        page.wait_for_selector.assert_not_called()
        page.click.assert_called_once_with("button#login", timeout=exe.DEFAULT_TIMEOUT)

    def test_wait_failure_does_not_abort_click(self):
        page = MagicMock()
        page.wait_for_selector = MagicMock(
            side_effect=Exception("overlay never appeared"))
        page.click = MagicMock()
        exe = self._executor(page)
        result = exe._execute_click(self._step(),
                                      ["mat-calendar td.mat-day"])
        page.click.assert_called_once()
        assert result == "mat-calendar td.mat-day"
