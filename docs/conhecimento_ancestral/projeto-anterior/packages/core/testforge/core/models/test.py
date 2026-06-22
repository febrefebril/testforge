from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DataSchema:
    filename: str
    fields: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    teardown: list[dict[str, str]] = field(default_factory=list)


@dataclass
class TestCase:
    name: str
    script_path: str
    data_path: str
    config_path: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class TestArtifact:
    test_name: str
    script_path: str
    data_path: str
    config_path: str
    testforge_dir: str
