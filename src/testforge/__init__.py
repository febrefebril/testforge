"""TestForge — Gravador inteligente de testes E2E com self-healing deterministico."""

try:
    from importlib.metadata import version as _importlib_version
    __version__ = _importlib_version(__package__ or "testforge")
except Exception:
    __version__ = "unknown"
