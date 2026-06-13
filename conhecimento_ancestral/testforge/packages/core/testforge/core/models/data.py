from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FieldMapping:
    field_name: str
    value: Any
    detected_type: str = ""
    original_value: Any = None
    auto_generated: bool = False


@dataclass
class DataContract:
    test_name: str = ""
    fields: dict[str, FieldMapping] = field(default_factory=dict)
    teardown: list[dict[str, str]] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        mapping = self.fields.get(key)
        if mapping is None:
            return default
        return mapping.value

    def set(self, key: str, value: Any) -> None:
        if key in self.fields:
            self.fields[key].value = value
        else:
            self.fields[key] = FieldMapping(field_name=key, value=value)
