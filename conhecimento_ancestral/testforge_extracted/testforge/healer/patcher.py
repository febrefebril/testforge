"""
TestForge — AST Patcher
Patches failing selectors in generated test files using Python AST manipulation.
Adds a # HEALED comment and updates selector values in-place.
"""
from __future__ import annotations

import ast
import logging
import re
from datetime import datetime
from pathlib import Path

log = logging.getLogger("testforge.patcher")


def patch_selector(
    test_path: Path,
    old_selector: str,
    new_selector: str,
    action_id: int | None = None,
) -> bool:
    """
    Find `old_selector` string in the test file and replace with `new_selector`.
    Adds a HEALED comment on the same line.
    Returns True if a replacement was made.
    """
    content = test_path.read_text(encoding="utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    heal_comment = f"  # HEALED:{timestamp} was={old_selector!r}"

    # Direct string replacement (handles both single and double quotes)
    escaped = re.escape(old_selector)
    pattern = rf'(["\']){escaped}\1'

    def replacer(m):
        quote = m.group(1)
        return f"{quote}{new_selector}{quote}{heal_comment}"

    new_content, count = re.subn(pattern, replacer, content, count=1)

    if count == 0:
        log.warning(f"Selector not found for patching: {old_selector!r}")
        return False

    test_path.write_text(new_content, encoding="utf-8")
    log.info(f"Patched selector in {test_path.name}: {old_selector!r} → {new_selector!r}")
    return True


def add_fallback_selectors(
    test_path: Path,
    action_id: int,
    selectors: dict[str, str],
) -> bool:
    """
    Insert additional selector constants above a find_element call
    for a specific action_id.
    """
    content = test_path.read_text(encoding="utf-8")

    # Find the line referencing the action_id
    pattern = rf'(find_element\([^,]+,\s*{action_id}\s*[,)])'
    m = re.search(pattern, content)
    if not m:
        log.warning(f"No find_element call found for action_id={action_id}")
        return False

    # Build fallback comment block
    lines = [f"    # Fallback selectors for action {action_id}:"]
    for sel_type, sel_value in selectors.items():
        if sel_value:
            lines.append(f"    # {sel_type}: {sel_value!r}")
    fallback_block = "\n".join(lines) + "\n"

    # Insert before the match
    insert_pos = content.rfind("\n", 0, m.start()) + 1
    new_content = content[:insert_pos] + fallback_block + content[insert_pos:]

    test_path.write_text(new_content, encoding="utf-8")
    return True


def validate_python_syntax(test_path: Path) -> tuple[bool, str]:
    """
    Check that the test file has valid Python syntax.
    Returns (is_valid, error_message).
    """
    try:
        source = test_path.read_text(encoding="utf-8")
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"
