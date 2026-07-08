# Bug Lab — Tests

Pytest files that reproduce bugs.

## Convention

```
bug_lab/tests/bugs/BUG-XXX/
└── test_bug_XXX.py
```

## Template: test_bug_XXX.py

```python
"""BUG-XXX: Short description of the bug."""
import pytest
from pathlib import Path
from testforge.browser import create_browser_context


PAGE_DIR = Path(__file__).parent.parent.parent / "pages" / "BUG-XXX"


@pytest.mark.asyncio
async def test_bug_xxx_reproduces_failure():
    """Reproduce BUG-XXX: the failing behavior."""
    page_path = PAGE_DIR / "index.html"
    page_url = page_path.as_uri()

    async with create_browser_context() as (browser, context, page):
        await page.goto(page_url)

        # Steps that trigger the bug
        await page.click("#target")

        # Assertion that should pass but currently fails
        assert await page.locator("#result").text_content() == "expected"


@pytest.mark.asyncio
async def test_bug_xxx_fix_works():
    """Verify BUG-XXX fix: the correct behavior after patch."""
    page_path = PAGE_DIR / "index.html"
    page_url = page_path.as_uri()

    async with create_browser_context() as (browser, context, page):
        await page.goto(page_url)
        await page.click("#target")

        # This assertion passes after the fix
        assert await page.locator("#result").text_content() == "expected"
```

## Rules

- One test file per bug directory.
- First test reproduces the bug (may be marked `@pytest.mark.xfail` before fix).
- Second test verifies the fix (must pass).
- Use `create_browser_context` from `testforge.browser`.
- Reference pages via `Path(__file__).parent.parent.parent / "pages" / "BUG-XXX"`.
- Keep tests fast. No sleeps — use `page.wait_for_selector()` or `expect()`.
