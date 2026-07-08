"""TestForge — Semantic module."""
from .model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate
from .recording_normalizer import RecordingNormalizer
from .compiler import PlaywrightCompiler

__all__ = [
    "SemanticTestCase", "SemanticAction", "SemanticTarget", "LocatorCandidate",
    "RecordingNormalizer", "PlaywrightCompiler",
]
