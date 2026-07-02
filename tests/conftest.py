"""Test-wide pytest hooks for TestForge-specific markers."""

from __future__ import annotations

import pytest


PATH_MARKERS = {
    "tests/unit/": "unit",
    "tests/integration/": "integration",
    "tests/e2e/": "e2e",
    "tests/regression/": "regression",
    "tests/contract/": "contract",
}


def pytest_collection_modifyitems(config, items):
    """Apply xfail behavior for known_bug-marked tests.

    Tests generated with @pytest.mark.known_bug(...) are expected to fail while
    documenting a product defect. We force strict xfail to surface unexpected
    passes as potential bug fixes.
    """

    for item in items:
        path = str(item.fspath).replace("\\", "/")
        for prefix, marker in PATH_MARKERS.items():
            if prefix in path:
                item.add_marker(getattr(pytest.mark, marker))

        mark = item.get_closest_marker("known_bug")
        if not mark:
            continue

        bug_id = mark.kwargs.get("bug_id", "UNKNOWN")
        observed = mark.kwargs.get("observed", "")
        reason = f"Known bug {bug_id}"
        if observed:
            reason = f"{reason}: {observed}"

        item.add_marker(pytest.mark.xfail(reason=reason, strict=True))
