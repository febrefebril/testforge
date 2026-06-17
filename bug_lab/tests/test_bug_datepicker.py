"""BUG: Datepicker — operator validation bug.

Symptom:
    Selecting today's date in the datepicker and clicking "Validate" shows
    "Date must not be in the past." — even though today should be accepted.

Cause:
    JavaScript validation used `<=` (less-than-or-equal) instead of `<` (less-than)
    when comparing selected date against today's midnight.
    `midnight <= midnight` → true → today's date incorrectly rejected.

Fix:
    Change `<=` to `<` so equal timestamps (same day at midnight) are accepted.
"""
from datetime import date, timedelta

import pytest


def _today_iso() -> str:
    """Return today's date as ISO string (YYYY-MM-DD)."""
    return date.today().isoformat()


def _future_iso(days: int = 30) -> str:
    """Return a future date as ISO string."""
    return (date.today() + timedelta(days=days)).isoformat()


def _past_iso(days: int = 7) -> str:
    """Return a past date as ISO string."""
    return (date.today() - timedelta(days=days)).isoformat()


# ── Reproduction: bug in action ────────────────────────────────────────

@pytest.mark.slow
def test_today_date_accepted(test_server, page):
    """Validate: today's date passes all rules (operator bug fixed with < instead of <=)."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    today = _today_iso()
    page.fill("#booking-date", today)

    page.locator("#validate-btn").click()

    status = page.locator("#status").text_content()
    assert "valid" in status.lower(), \
        f"Expected 'valid' for today ({today}), got: {status}"


# ── Bug fix validation tests ───────────────────────────────────────────

@pytest.mark.slow
def test_future_date_accepted(test_server, page):
    """Validate: date 30 days from now passes all rules (works despite bug)."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    future = _future_iso(30)
    page.fill("#booking-date", future)
    page.locator("#validate-btn").click()

    status = page.locator("#status").text_content()
    assert "valid" in status.lower(), \
        f"Expected 'valid' for {future}, got: {status}"

    error_msg = page.locator("#error-msg").text_content() or ""
    assert "past" not in error_msg.lower(), \
        f"Unexpected error for future date: {error_msg}"


@pytest.mark.slow
def test_empty_date_rejected(test_server, page):
    """Validate: empty input shows 'Please select a date.'"""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    # Don't fill anything — input is empty
    page.locator("#validate-btn").click()

    error_msg = page.locator("#error-msg").text_content() or ""
    assert "select a date" in error_msg.lower(), \
        f"Expected empty-date error, got: {error_msg}"

    status = page.locator("#status").text_content()
    assert "invalid" in status.lower(), \
        f"Expected 'Invalid' status, got: {status}"


@pytest.mark.slow
def test_past_date_rejected(test_server, page):
    """Validate: past date correctly rejected (this rule works fine)."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    past = _past_iso(7)
    page.fill("#booking-date", past)
    page.locator("#validate-btn").click()

    error_msg = page.locator("#error-msg").text_content() or ""
    assert "past" in error_msg.lower(), \
        f"Expected past-date error, got: {error_msg}"

    status = page.locator("#status").text_content()
    assert "invalid" in status.lower(), \
        f"Expected 'Invalid' status, got: {status}"


@pytest.mark.slow
def test_beyond_90_days_rejected(test_server, page):
    """Validate: date beyond 90 days rejected."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    far_future = _future_iso(100)
    page.fill("#booking-date", far_future)
    page.locator("#validate-btn").click()

    error_msg = page.locator("#error-msg").text_content() or ""
    assert "90 days" in error_msg.lower(), \
        f"Expected 90-day limit error, got: {error_msg}"


@pytest.mark.slow
def test_submit_enabled_after_validation(test_server, page):
    """Validate: submit button enabled after successful validation."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    # Submit initially disabled
    assert page.locator("#submit-btn").is_disabled(), \
        "Submit button should be disabled before validation"

    future = _future_iso(30)
    page.fill("#booking-date", future)
    page.locator("#validate-btn").click()

    # After successful validation, submit enabled
    assert not page.locator("#submit-btn").is_disabled(), \
        "Submit button should be enabled after successful validation"


@pytest.mark.slow
def test_submit_shows_confirmation(test_server, page):
    """Validate: submitting after valid date shows confirmation."""
    page.goto(f"{test_server}/bug-datepicker/index.html")

    future = _future_iso(30)
    page.fill("#booking-date", future)
    page.locator("#validate-btn").click()
    page.locator("#submit-btn").click()

    status = page.locator("#status").text_content()
    assert "submitted" in status.lower(), \
        f"Expected 'Submitted' in status, got: {status}"
    assert future in status, \
        f"Expected date {future} in status, got: {status}"
