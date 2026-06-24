"""Regression test — Bug 2/6: no_viewport=True in headed mode."""
import pytest


def test_make_context_kwargs_headless():
    from testforge.cli.app import _make_context_kwargs
    kw = _make_context_kwargs(True)
    assert kw == {"viewport": {"width": 1280, "height": 720}}


def test_make_context_kwargs_headed():
    from testforge.cli.app import _make_context_kwargs
    kw = _make_context_kwargs(False)
    assert kw == {"no_viewport": True}
    assert "viewport" not in kw


def test_app_py_no_bare_viewport_none():
    """app.py must not pass viewport=None to new_context — must use no_viewport=True."""
    from pathlib import Path
    src = (Path(__file__).parent.parent / "src/testforge/cli/app.py").read_text(encoding="utf-8")
    assert "viewport=None" not in src, "viewport=None found — use no_viewport=True for headed mode"
    assert "new_context(viewport=_vp)" not in src
    assert "new_context(viewport=viewport)" not in src
