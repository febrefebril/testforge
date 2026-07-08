from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BrowserConfig:
    type: str = "chromium"
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 720
    record_video: bool = False


@dataclass
class LLMConfig:
    api_key: str = ""
    azure_endpoint: str = ""
    model: str = "gpt-4.1-mini"
    api_version: str = "2025-03-01-preview"
    temperature: float = 0.3
    max_retries: int = 3


@dataclass
class RecordingConfig:
    max_duration_minutes: int = 30
    auto_pause_on_navigation: bool = True


@dataclass
class LoggingConfig:
    level: str = "info"
    retention_days: int = 30


@dataclass
class GitConfig:
    auto_pr: bool = True
    branch_prefix: str = "testforge/"


@dataclass
class Config:
    default_env: str = "production"
    timeout: int = 30000
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    git: GitConfig = field(default_factory=GitConfig)
