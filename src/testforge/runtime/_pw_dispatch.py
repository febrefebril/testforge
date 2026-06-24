"""Phase 3: Safe dispatcher for Playwright `get_by_*` call strings.

Parses strings such as `get_by_role("button", name="Salvar")` using
the `ast` module — no `eval` — then invokes the corresponding method
on a Playwright `Page` or `Locator`. Supports method chaining:
`get_by_role("dialog").get_by_role("button", name="Salvar")`.

Only allowlisted methods are dispatchable; anything else raises
`ValueError`. This is the supply chain that lets a JSON candidate file
become a live `Locator` without ever executing arbitrary code.
"""
from __future__ import annotations

import ast
from typing import Any

_ALLOWED_METHODS = {
    "get_by_role",
    "get_by_label",
    "get_by_placeholder",
    "get_by_text",
    "get_by_title",
    "get_by_alt_text",
    "get_by_test_id",
    "locator",
    "filter",
    "first",
    "last",
    "nth",
}


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return -node.operand.value
    raise ValueError(f"Unsupported literal in playwright call: {ast.dump(node)}")


def dispatch(receiver, call_str: str):
    """Apply `call_str` against `receiver` (Page or Locator) and return the result.

    Example:
        dispatch(page, 'get_by_role("button", name="Salvar")')
            -> page.get_by_role("button", name="Salvar")

        dispatch(page, 'get_by_role("dialog").get_by_role("button", name="X")')
            -> page.get_by_role("dialog").get_by_role("button", name="X")
    """
    tree = ast.parse(call_str.strip(), mode="eval")
    return _eval(receiver, tree.body)


def _eval(receiver, node: ast.AST):
    # Method call: foo.bar(arg1, kw=val) OR bare bar(arg1, kw=val) on receiver
    if isinstance(node, ast.Call):
        args = [_literal(a) for a in node.args]
        kwargs = {kw.arg: _literal(kw.value) for kw in node.keywords if kw.arg}
        if isinstance(node.func, ast.Name):
            # Bare call: get_by_role(...) means receiver.get_by_role(...)
            if node.func.id not in _ALLOWED_METHODS:
                raise ValueError(f"Method not allowed: {node.func.id}")
            func = getattr(receiver, node.func.id)
        elif isinstance(node.func, ast.Attribute):
            target = _eval(receiver, node.func.value)
            if node.func.attr not in _ALLOWED_METHODS:
                raise ValueError(f"Method not allowed: {node.func.attr}")
            func = getattr(target, node.func.attr)
        else:
            raise ValueError(f"Unsupported call func: {ast.dump(node.func)}")
        return func(*args, **kwargs)

    # Attribute access without call: foo.first (property)
    if isinstance(node, ast.Attribute):
        target = _eval(receiver, node.value)
        if node.attr not in _ALLOWED_METHODS:
            raise ValueError(f"Attribute not allowed: {node.attr}")
        return getattr(target, node.attr)

    raise ValueError(f"Unsupported node in playwright call: {ast.dump(node)}")
