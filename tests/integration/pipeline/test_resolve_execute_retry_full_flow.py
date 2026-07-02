from testforge.runtime import step


def test_integration_resolve_execute_retry_full_flow():
    class _Locator:
        def __init__(self, fail=False):
            self._fail = fail
            self._clicked = 0

        def count(self):
            return 1

        def click(self, timeout=1500):
            self._clicked += 1
            if self._fail:
                raise RuntimeError("not clickable")

    class _Page:
        def __init__(self):
            self.bad = _Locator(fail=True)
            self.good = _Locator(fail=False)

        def get_by_role(self, *args, **kwargs):
            return self.bad

        def get_by_test_id(self, *args, **kwargs):
            return self.good

        def wait_for_timeout(self, *args, **kwargs):
            return None

    page = _Page()
    step.click(
        page,
        intent="click salvar",
        candidates=[
            {
                "strategy": "role",
                "score": 0.9,
                "selector": 'page.get_by_role("button", name="Salvar")',
                "playwright_call": 'get_by_role("button", name="Salvar")',
            },
            {
                "strategy": "test_id",
                "score": 0.85,
                "selector": 'page.get_by_test_id("save")',
                "playwright_call": 'get_by_test_id("save")',
            },
        ],
    )

    assert page.bad._clicked == 1
    assert page.good._clicked == 1
