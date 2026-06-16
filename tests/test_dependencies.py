"""Tests for declared project dependencies."""

import sys


class TestDependencies:
    """Verify critical dependencies are importable."""

    def test_httpx_importable(self):
        """httpx must be importable — used by llm_client module."""
        import httpx  # noqa: F401

        assert "httpx" in sys.modules

    def test_llm_client_imports_httpx(self):
        """llm_client module imports cleanly — depends on httpx."""
        from testforge.healing.llm_client import chat  # noqa: F401

        assert callable(chat)
