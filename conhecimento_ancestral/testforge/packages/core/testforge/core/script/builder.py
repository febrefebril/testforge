from __future__ import annotations

import ast
from typing import Any, Optional

from testforge.core.models.step import RecordedStep
from testforge.core.script.selectors import SelectorStrategy, generate_strategies

ASSERT_INIT = "ASSERT_INIT_DONE"


class ScriptBuilder:
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.class_name = test_name.replace("test_", "Test").title().replace("_", "")
        self.steps: list[RecordedStep] = []
        self.fields: dict[str, Any] = {}

    def add_step(self, step: RecordedStep) -> None:
        self.steps.append(step)

    def set_field(self, key: str, value: Any) -> None:
        self.fields[key] = value

    def build_ast(self) -> ast.Module:
        imports = [
            ast.Import(names=[ast.alias(name="pytest", asname=None)]),
            ast.Import(names=[ast.alias(name="json", asname=None)]),
            ast.ImportFrom(
                module="pathlib",
                names=[ast.alias(name="Path", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module="playwright.sync_api",
                names=[ast.alias(name="Page", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module="playwright.sync_api",
                names=[ast.alias(name="expect", asname=None)],
                level=0,
            ),
        ]

        class_body: list[ast.stmt] = []

        data_path_assign = ast.Assign(
            targets=[ast.Name(id="DATA_PATH", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Name(id="Path", ctx=ast.Load()),
                        args=[ast.Name(id="__file__", ctx=ast.Load())],
                        keywords=[],
                    ),
                    attr="with_suffix",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=".data.json")],
                keywords=[],
            ),
        )
        class_body.append(data_path_assign)

        setup_method = self._build_setup_method()
        class_body.append(setup_method)

        test_method = self._build_test_method()
        class_body.append(test_method)

        class_def = ast.ClassDef(
            name=self.class_name,
            bases=[],
            keywords=[],
            body=class_body,
            decorator_list=[],
        )

        module = ast.Module(body=[*imports, class_def], type_ignores=[])
        module = ast.fix_missing_locations(module)
        return module

    def _build_setup_method(self) -> ast.FunctionDef:
        body = [
            ast.Assign(
                targets=[ast.Attribute(
                    value=ast.Name(id="self", ctx=ast.Load()),
                    attr="page",
                    ctx=ast.Store(),
                )],
                value=ast.Name(id="page", ctx=ast.Load()),
            ),
            ast.With(
                items=[
                    ast.withitem(
                        context_expr=ast.Call(
                            func=ast.Name(id="open", ctx=ast.Load()),
                            args=[ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr="DATA_PATH",
                                ctx=ast.Load(),
                            )],
                            keywords=[],
                        ),
                        optional_vars=ast.Name(id="f", ctx=ast.Store()),
                    )
                ],
                body=[
                    ast.Assign(
                        targets=[ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr="data",
                            ctx=ast.Store(),
                        )],
                        value=ast.Call(
                            func=ast.Name(id="json.load", ctx=ast.Load()),
                            args=[ast.Name(id="f", ctx=ast.Load())],
                            keywords=[],
                        ),
                    )
                ],
            ),
        ]

        return ast.FunctionDef(
            name="setup",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self"),
                    ast.arg(arg="page", annotation=ast.Name(id="Page", ctx=ast.Load())),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body,
            decorator_list=[
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="pytest", ctx=ast.Load()),
                        attr="fixture",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[ast.keyword(arg="autouse", value=ast.Constant(value=True))],
                ),
            ],
            returns=None,
        )

    def _build_test_method(self) -> ast.FunctionDef:
        body: list[ast.stmt] = []

        for i, step in enumerate(self.steps):
            step_comment = ast.Expr(value=ast.Constant(value=f" Passo {i + 1}: {step.action}"))
            body.append(step_comment)

            strategies = generate_strategies(
                selector=step.selector_used,
                tag_name=step.tag_name,
                text=step.text,
                value=step.value,
                attrs=step.attrs,
            )

            fallback_comment = ast.Expr(value=ast.Constant(
                value=f" Seletores: {' | '.join(s.css for s in strategies[:3])}"
            ))
            body.append(fallback_comment)

            action_code = self._build_action(step, i, strategies)
            if action_code:
                body.append(action_code)

        return ast.FunctionDef(
            name="test_run",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self"),
                    ast.arg(arg="page", annotation=ast.Name(id="Page", ctx=ast.Load())),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

    def _build_action(self, step: RecordedStep, index: int, strategies: list[SelectorStrategy]) -> Optional[ast.stmt]:
        primary = strategies[0].css if strategies else step.selector_used
        action = step.action
        url = step.url

        if action == "navigate" or (index == 0 and url):
            return ast.Expr(value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="page", ctx=ast.Load()),
                    attr="goto",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=url)],
                keywords=[],
            ))

        elif action == "click":
            if primary:
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="page", ctx=ast.Load()),
                        attr="click",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=primary)],
                    keywords=[],
                ))
            return ast.Expr(value=ast.Constant(value=" # clique registrado"))

        elif action in ("fill", "input"):
            if primary:
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="page", ctx=ast.Load()),
                        attr="fill",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=primary),
                        ast.Subscript(
                            value=ast.Subscript(
                                value=ast.Subscript(
                                    value=ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr="data",
                                        ctx=ast.Load(),
                                    ),
                                    slice=ast.Constant(value="steps"),
                                    ctx=ast.Load(),
                                ),
                                slice=ast.Constant(value=index),
                                ctx=ast.Load(),
                            ),
                            slice=ast.Constant(value="value"),
                            ctx=ast.Load(),
                        ),
                    ],
                    keywords=[],
                ))

        elif action == "select":
            if primary:
                tag = step.tag_name.lower() if step.tag_name else ""
                input_type = (step.attrs or {}).get("type", "")
                if tag == "input" and input_type in ("radio", "checkbox"):
                    return ast.Expr(value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="page", ctx=ast.Load()),
                            attr="click",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=primary)],
                        keywords=[],
                    ))
                label = step.text
                if label:
                    return ast.Expr(value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="page", ctx=ast.Load()),
                            attr="select_option",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value=primary)],
                        keywords=[ast.keyword(
                            arg="label",
                            value=ast.Constant(value=label),
                        )],
                    ))
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="page", ctx=ast.Load()),
                        attr="select_option",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=primary),
                        ast.Subscript(
                            value=ast.Subscript(
                                value=ast.Subscript(
                                    value=ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr="data",
                                        ctx=ast.Load(),
                                    ),
                                    slice=ast.Constant(value="steps"),
                                    ctx=ast.Load(),
                                ),
                                slice=ast.Constant(value=index),
                                ctx=ast.Load(),
                            ),
                            slice=ast.Constant(value="value"),
                            ctx=ast.Load(),
                        ),
                    ],
                    keywords=[],
                ))

        elif action == "upload":
            if primary:
                return ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="page", ctx=ast.Load()),
                        attr="set_input_files",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=primary),
                        ast.Constant(value=step.value),
                    ],
                    keywords=[],
                ))
            return ast.Expr(value=ast.Constant(value=" # upload registrado"))

        elif action == "download":
            if primary:
                return self._build_download(step, primary)
            return ast.Expr(value=ast.Constant(value=" # download registrado"))

        elif action == "assert":
            return self._build_assert(step, primary)

        return None

    def _build_assert(self, step: RecordedStep, selector: str) -> ast.stmt:
        assert_type = step.assert_type or "textual"
        expected = step.expected_value or step.text or ""
        state = step.assert_state or ""

        expect_call = ast.Call(
            func=ast.Name(id="expect", ctx=ast.Load()),
            args=[ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="page", ctx=ast.Load()),
                    attr="locator",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=selector)],
                keywords=[],
            )],
            keywords=[],
        )

        if assert_type == "textual" or assert_type == "automatico":
            method = "to_contain_text"
            args = [ast.Constant(value=expected)]
            keywords = []
        elif assert_type == "estado":
            state_method_map = {
                "checked": "to_be_checked",
                "unchecked": "not_to_be_checked",
                "disabled": "to_be_disabled",
                "enabled": "to_be_enabled",
                "has_value": "to_have_value",
            }
            method = state_method_map.get(state, "to_be_enabled")
            args = [ast.Constant(value=expected)] if method == "to_have_value" else []
            keywords = []
        elif assert_type == "visivel":
            method = "to_be_visible"
            args = []
            keywords = []
        else:
            method = "to_contain_text"
            args = [ast.Constant(value=expected)]
            keywords = []

        return ast.Expr(value=ast.Call(
            func=ast.Attribute(
                value=expect_call,
                attr=method,
                ctx=ast.Load(),
            ),
            args=args,
            keywords=keywords,
        ))

    def _build_download(self, step: RecordedStep, selector: str) -> ast.stmt:
        stmt = ast.With(
            items=[
                ast.withitem(
                    context_expr=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="page", ctx=ast.Load()),
                            attr="expect_download",
                            ctx=ast.Load(),
                        ),
                        args=[],
                        keywords=[],
                    ),
                    optional_vars=ast.Name(id="download_info", ctx=ast.Store()),
                )
            ],
            body=[
                ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="page", ctx=ast.Load()),
                        attr="click",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=selector)],
                    keywords=[],
                )),
            ],
        )
        return stmt

    def build_data_json(self) -> dict:
        steps_data = []
        for step in self.steps:
            if step.action == "navigate":
                steps_data.append({
                    "action": "navigate",
                    "selector": "",
                    "fallbacks": [],
                    "tag_name": "",
                    "text": "",
                    "value": "",
                    "url": step.url,
                    "intention": step.intention or "",
                    "attrs": {},
                })
                continue

            strategies = generate_strategies(
                selector=step.selector_used,
                tag_name=step.tag_name,
                text=step.text,
                value=step.value,
                attrs=step.attrs,
            )
            raw_sel = step.raw_selector or ""
            all_fallbacks = [s.css for s in strategies]
            if raw_sel and raw_sel != step.selector_used:
                all_fallbacks.insert(0, raw_sel)
            entry = {
                "action": step.action,
                "selector": step.selector_used,
                "fallbacks": all_fallbacks[:4],
                "tag_name": step.tag_name,
                "text": step.text,
                "value": step.value,
                "url": step.url,
                "intention": step.intention or "",
                "attrs": step.attrs or {},
            }
            if step.action == "assert":
                entry["assert_type"] = step.assert_type
                entry["assert_state"] = step.assert_state
                entry["expected_value"] = step.expected_value
            steps_data.append(entry)
        return {"steps": steps_data}

    def serialize(self) -> str:
        module = self.build_ast()
        return ast.unparse(module)
