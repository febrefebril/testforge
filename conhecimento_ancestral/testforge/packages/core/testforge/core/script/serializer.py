from __future__ import annotations

import json
from pathlib import Path

from testforge.core.script.builder import ScriptBuilder

def _pytest_safe_name(name: str) -> str:
    """Ensure name starts with test_ for pytest compatibility."""
    if name.startswith("test_"):
        return name
    return f"test_{name}"


def generate_test_files(
    test_name: str,
    steps: list,
    output_dir: Path,
) -> tuple[Path, Path]:
    safe_name = _pytest_safe_name(test_name)
    builder = ScriptBuilder(safe_name)

    for step in steps:
        builder.add_step(step)

    script_content = builder.serialize()
    data_content = builder.build_data_json()

    script_path = output_dir / f"{safe_name}.py"
    data_path = output_dir / f"{safe_name}.data.json"

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data_content, f, ensure_ascii=False, indent=2)

    return script_path, data_path
