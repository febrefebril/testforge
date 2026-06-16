"""Template test demonstrating the bug lab cycle: reproduce → verify → fix → validate."""
import pytest


@pytest.mark.slow
def test_counter_increment_reset(test_server, page):
    """Demonstrate: reproduce a scenario, verify behavior, fix/validate result.
    
    Cycle:
      1. reproduce  — load page, observe initial state
      2. verify     — assert current behavior matches expectation (or bug)
      3. fix        — code change in src/testforge/ (simulated here)
      4. validate   — run test again, confirm fix resolved the issue
    """
    # 1. REPRODUCE: load the minimal page
    page.goto(f"{test_server}/template/index.html")

    # 2. VERIFY: initial state is correct
    display = page.locator("#counter-display")
    assert display.text_content() == "Count: 0"

    # 3. EXERCISE: trigger the behavior under test
    page.locator("#increment-btn").click()
    page.locator("#increment-btn").click()
    assert display.text_content() == "Count: 2"

    # 4. VALIDATE: reset returns to known-good state
    page.locator("#reset-btn").click()
    assert display.text_content() == "Count: 0"
