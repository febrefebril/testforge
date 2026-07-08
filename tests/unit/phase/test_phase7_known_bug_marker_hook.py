import pytest


def test_known_bug_marker_is_registered(pytestconfig):
    markers = pytestconfig.getini("markers")
    assert any(m.startswith("known_bug:") for m in markers)


@pytest.mark.known_bug(bug_id="BUG-20260701-00001", observed="500 on save")
def test_known_bug_sample_placeholder():
    # This test intentionally fails and is converted to strict xfail by hook.
    assert False
