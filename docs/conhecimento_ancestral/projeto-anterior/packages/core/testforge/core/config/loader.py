from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol

from testforge.core.config.schema import Config, LLMConfig


class ConfigSource(ABC):
    @abstractmethod
    def load(self) -> Config: ...


class ConfigLoader:
    sources: list[ConfigSource]

    def __init__(self, sources: list[ConfigSource] | None = None):
        self.sources = sources or []

    def load(self, overrides: dict[str, Any] | None = None) -> Config:
        result = Config()
        for source in self.sources:
            partial = source.load()
            result = self._merge(result, partial)
        if overrides:
            result = self._merge_overrides(result, overrides)
        return result

    @staticmethod
    def _merge(base: Config, override: Config) -> Config:
        merged = Config()
        for field in Config.__dataclass_fields__:
            base_val = getattr(base, field)
            override_val = getattr(override, field)
            if override_val != Config.__dataclass_fields__[field].default:
                setattr(merged, field, override_val)
            else:
                setattr(merged, field, base_val)
        return merged

    @staticmethod
    def _merge_overrides(config: Config, overrides: dict[str, Any]) -> Config:
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


def _load_env_file() -> None:
    try:
        from dotenv import load_dotenv
        # busca .env no CWD, home, ou ao lado do pacote
        for candidate in (os.path.join(os.getcwd(), ".env"),
                          os.path.expanduser("~/.testforge.env")):
            if os.path.isfile(candidate):
                load_dotenv(candidate)
                break
    except ImportError:
        pass


def load_llm_config() -> LLMConfig | None:
    _load_env_file()
    api_key = os.environ.get("AZURE_OPENAI_KEY", "")
    if not api_key:
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    if not api_key:
        return None
    return LLMConfig(
        api_key=api_key,
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4.1-mini"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
    )
