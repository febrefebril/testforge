from testforge.runtime import step


def test_gap01_when_first_candidate_fill_fails_then_retry_next_candidate():
    class _Locator:
        def __init__(self, fail=False):
            self._fail = fail
            self.first = self
            self._fills = 0

        def count(self):
            return 1

        def fill(self, value, timeout=1500):
            self._fills += 1
            if self._fail:
                raise RuntimeError("fill timeout")

        def press(self, key):
            return None

    class _Page:
        def __init__(self):
            self.bad = _Locator(fail=True)
            self.good = _Locator(fail=False)
            self.keyboard = type("K", (), {"press": lambda self, key: None})()

        def get_by_role(self, *args, **kwargs):
            return self.bad

        def get_by_label(self, *args, **kwargs):
            return self.good

        def wait_for_timeout(self, *args, **kwargs):
            return None

    page = _Page()

    step.fill(
        page,
        intent="Renda mensal",
        value="1000",
        candidates=[
            {
                "strategy": "role",
                "score": 0.9,
                "selector": 'page.get_by_role("textbox", name="Renda")',
                "playwright_call": 'get_by_role("textbox", name="Renda")',
            },
            {
                "strategy": "label",
                "score": 0.85,
                "selector": 'page.get_by_label("Renda")',
                "playwright_call": 'get_by_label("Renda")',
            },
        ],
    )

    assert page.bad._fills == 1
    assert page.good._fills == 1
