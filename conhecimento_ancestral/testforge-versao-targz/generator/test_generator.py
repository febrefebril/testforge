"""
TestForge — Test Generator (Phase 2)
Sends recording JSON to Azure LLM and produces a pytest file.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from generator.llm_client import chat, extract_code_block

log = logging.getLogger("testforge.generator")

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
ASSERT_STRATEGIES_PATH = Path(__file__).parent / "prompts" / "assert_strategies.txt"

GENERATED_DIR = Path("tests/generated")


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_user_prompt(recording: dict[str, Any]) -> str:
    meta = recording.get("meta", {})
    events = recording.get("events", [])
    stack = recording.get("stack", {})
    raw_code = recording.get("raw_code", "")

    # Summarize events to avoid exceeding context
    event_summary = []
    for ev in events:
        entry = {
            "id": ev.get("id"),
            "type": ev.get("type"),
            "selectors": ev.get("selectors", {}),
            "context": ev.get("context", {}),
            "value": ev.get("value"),
            "url": ev.get("url", ""),
            "iframe": ev.get("iframe", {}),
            "shadow": ev.get("shadow", {}),
        }
        event_summary.append(entry)

    last_action = events[-1] if events else {}

    assert_strategies = _load_prompt(ASSERT_STRATEGIES_PATH)

    prompt = f"""## RECORDING METADATA
{json.dumps(meta, indent=2, ensure_ascii=False)}

## DETECTED STACK
{json.dumps(stack, indent=2)}

## LAST ACTION (most important for assert)
{json.dumps(last_action, indent=2)}

## RECORDED EVENTS ({len(events)} total)
{json.dumps(event_summary, indent=2, ensure_ascii=False)}

{f'## CODEGEN RAW CODE (reference only, do not copy verbatim){chr(10)}```python{chr(10)}{raw_code}{chr(10)}```' if raw_code else ''}

## ASSERT STRATEGY GUIDE
{assert_strategies}

## YOUR TASK
Generate a complete pytest file for the test "{meta.get('name', 'test')}".
- Test function name: `test_{_safe_name(meta.get('name', 'test'))}`
- File must be self-contained with all imports
- Include the `find_element` helper function
- End with the most specific assert possible based on all hints above
- The explicit assert hint from the user is: "{meta.get('expected_assert', 'not provided')}"
"""
    return prompt


def _safe_name(name: str) -> str:
    """Convert a human name to a safe Python identifier."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name or "test_case"


def generate_test(recording: dict[str, Any], output_dir: Path = GENERATED_DIR) -> Path:
    """
    Generate a pytest file from a recording dict.
    Returns the path to the generated file.
    """
    from rich.console import Console
    console = Console()

    meta = recording.get("meta", {})
    name = _safe_name(meta.get("name", "test"))

    console.print(f"\n[bold blue]⚙  Phase 2 — Generating test:[/bold blue] [cyan]{name}[/cyan]")

    system = _load_prompt(SYSTEM_PROMPT_PATH)
    user = _build_user_prompt(recording)

    console.print(f"  [dim]Sending {len(user)} chars to LLM...[/dim]")

    raw_response = chat(system=system, user=user, temperature=0.2, max_tokens=4096)
    code = extract_code_block(raw_response, lang="python")

    # Ensure valid Python prefix
    if not code.strip().startswith(("import", "from", "#", '"""')):
        # LLM might have returned explanation before code, try extracting
        code = extract_code_block(raw_response, lang="")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"test_{name}.py"
    output_path.write_text(code, encoding="utf-8")

    console.print(f"  [green]✓ Test saved:[/green] {output_path}")
    log.info(f"Test generated: {output_path} ({len(code)} chars)")

    return output_path
