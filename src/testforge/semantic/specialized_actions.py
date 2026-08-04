
"""Integração de ações especializadas do gravador de intenção.

Este módulo é deliberadamente independente do RecorderController. Ele transforma
os sinais brutos já capturados em um contrato estável e fornece emissão/runtime
para frame, popup/nova página, upload, download e redirecionamento.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional


class SpecializedActionError(RuntimeError):
    """Erro explícito; ações desconhecidas nunca viram click silenciosamente."""


class SpecializedActionType(str, Enum):
    FRAME = "frame_context"
    FRAME_CROSS_ORIGIN = "frame_cross_origin"
    NEW_PAGE = "new_page"
    POPUP = "popup"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    NAVIGATION_REDIRECT = "navigation_redirect"
    AUTHENTICATION_REDIRECT = "authentication_redirect"


_ALIASES = {
    "frame": SpecializedActionType.FRAME,
    "frame_locator": SpecializedActionType.FRAME,
    "frame_same_origin": SpecializedActionType.FRAME,
    "iframe": SpecializedActionType.FRAME,
    "iframe_context": SpecializedActionType.FRAME,
    "iframe_cross_origin": SpecializedActionType.FRAME_CROSS_ORIGIN,
    "cross_origin_frame": SpecializedActionType.FRAME_CROSS_ORIGIN,
    "page": SpecializedActionType.NEW_PAGE,
    "page_opened": SpecializedActionType.NEW_PAGE,
    "new_tab": SpecializedActionType.NEW_PAGE,
    "window_open": SpecializedActionType.POPUP,
    "upload": SpecializedActionType.FILE_UPLOAD,
    "download": SpecializedActionType.FILE_DOWNLOAD,
    "redirect": SpecializedActionType.NAVIGATION_REDIRECT,
    "auth_redirect": SpecializedActionType.AUTHENTICATION_REDIRECT,
    "sso_redirect": SpecializedActionType.AUTHENTICATION_REDIRECT,
}


@dataclass(frozen=True)
class SpecializedAction:
    kind: SpecializedActionType
    event_id: str = ""
    page_id: str = ""
    frame_id: str = ""
    parent_frame_id: str = ""
    selector: str = ""
    url: str = ""
    value: Any = None
    payload: dict[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpecializedAction":
        if not isinstance(data, Mapping):
            raise SpecializedActionError("specialized_action deve ser um mapping")
        raw_kind = str(data.get("kind") or "")
        kind = _normalize_kind(raw_kind)
        if kind is None:
            raise SpecializedActionError(f"Tipo especializado desconhecido: {raw_kind!r}")
        return cls(
            kind=kind,
            event_id=str(data.get("event_id") or ""),
            page_id=str(data.get("page_id") or ""),
            frame_id=str(data.get("frame_id") or ""),
            parent_frame_id=str(data.get("parent_frame_id") or ""),
            selector=str(data.get("selector") or ""),
            url=str(data.get("url") or ""),
            value=data.get("value"),
            payload=dict(data.get("payload") or {}),
            limitations=tuple(data.get("limitations") or ()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "event_id": self.event_id,
            "page_id": self.page_id,
            "frame_id": self.frame_id,
            "parent_frame_id": self.parent_frame_id,
            "selector": self.selector,
            "url": self.url,
            "value": self.value,
            "payload": dict(self.payload),
            "limitations": list(self.limitations),
        }


def _get(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _target_selector(event: Any) -> str:
    target = _get(event, "target") or {}
    candidates = _get(target, "candidates", []) or []
    for candidate in candidates:
        selector = _get(candidate, "selector", "")
        if selector:
            return str(selector)
    for name in ("selector", "css_path", "element_id"):
        value = _get(target, name, "")
        if value:
            return f"#{value}" if name == "element_id" else str(value)
    return ""


def _normalize_kind(raw: str) -> Optional[SpecializedActionType]:
    value = (raw or "").strip().lower().replace("-", "_")
    try:
        return SpecializedActionType(value)
    except ValueError:
        return _ALIASES.get(value)


def normalize_specialized_event(event: Any) -> Optional[SpecializedAction]:
    """Converte dict, RawRecordedEvent ou objeto equivalente.

    Retorna None para eventos comuns; lança somente quando o evento declara que é
    especializado mas não possui dados mínimos para execução segura.
    """
    raw_type = str(_get(event, "event_type", _get(event, "type", "")) or "")
    kind = _normalize_kind(raw_type)

    file_upload = _get(event, "file_upload")
    if file_upload and kind is None:
        kind = SpecializedActionType.FILE_UPLOAD

    context = dict(_get(event, "context", {}) or {})
    payload = dict(_get(event, "payload", {}) or {})
    if file_upload:
        payload.setdefault("files", file_upload)

    if kind is None:
        return None

    selector = str(_get(event, "selector", "") or _target_selector(event))
    url = str(_get(event, "url", "") or payload.get("url", ""))
    limitations: list[str] = []

    if kind is SpecializedActionType.FRAME_CROSS_ORIGIN:
        limitations.append("cross-origin iframe DOM is not directly accessible")
    if kind is SpecializedActionType.FILE_UPLOAD and not selector:
        selector = "input[type=file]"

    return SpecializedAction(
        kind=kind,
        event_id=str(_get(event, "event_id", "") or ""),
        page_id=str(context.get("page_id") or _get(event, "page_id", "") or ""),
        frame_id=str(context.get("frame_id") or _get(event, "frame_id", "") or ""),
        parent_frame_id=str(context.get("parent_frame_id") or ""),
        selector=selector,
        url=url,
        value=_get(event, "value"),
        payload=payload,
        limitations=tuple(limitations),
    )


def _py(value: Any) -> str:
    return repr(value)


def _file_values(action: SpecializedAction) -> list[str]:
    raw = action.payload.get("paths") or action.payload.get("files") or action.value or []
    if isinstance(raw, (str, os.PathLike)):
        raw = [str(raw)]
    values: list[str] = []
    for item in raw:
        if isinstance(item, Mapping):
            value = item.get("path") or item.get("name")
        else:
            value = item
        if value:
            values.append(str(value))
    return values


def emit_specialized_python(action: SpecializedAction, *, page_var: str = "page", indent: str = "") -> list[str]:
    """Emite linhas Playwright síncronas, sem selecionar locator no gravador."""
    k = action.kind
    lines: list[str]
    if k is SpecializedActionType.FRAME:
        if not action.selector:
            raise SpecializedActionError("frame_context sem selector")
        lines = [f"frame = {page_var}.frame_locator({_py(action.selector)})"]
    elif k is SpecializedActionType.FRAME_CROSS_ORIGIN:
        lines = [f"# LIMITATION: cross-origin iframe; frame={_py(action.selector or action.url)}"]
    elif k in (SpecializedActionType.POPUP, SpecializedActionType.NEW_PAGE):
        trigger = str(action.payload.get("trigger_python") or "")
        if not trigger:
            raise SpecializedActionError(f"{k.value} sem payload.trigger_python")
        lines = [
            f"with {page_var}.expect_popup() as popup_info:",
            f"    {trigger}",
            "page = popup_info.value",
            "page.wait_for_load_state('domcontentloaded')",
        ]
    elif k is SpecializedActionType.FILE_UPLOAD:
        if not action.selector:
            raise SpecializedActionError("file_upload sem selector")
        files = _file_values(action)
        if not files:
            raise SpecializedActionError("file_upload sem arquivo parametrizado")
        lines = [f"{page_var}.set_input_files({_py(action.selector)}, {_py(files if len(files) > 1 else files[0])})"]
    elif k is SpecializedActionType.FILE_DOWNLOAD:
        trigger = str(action.payload.get("trigger_python") or "")
        if not trigger:
            raise SpecializedActionError("file_download sem payload.trigger_python")
        destination = str(action.payload.get("destination") or "downloads")
        lines = [
            f"with {page_var}.expect_download() as download_info:",
            f"    {trigger}",
            "download = download_info.value",
            f"download.save_as(os.path.join({_py(destination)}, download.suggested_filename))",
        ]
    elif k in (SpecializedActionType.NAVIGATION_REDIRECT, SpecializedActionType.AUTHENTICATION_REDIRECT):
        pattern = action.payload.get("url_pattern") or action.url
        if not pattern:
            raise SpecializedActionError(f"{k.value} sem URL/padrão")
        lines = [f"{page_var}.wait_for_url({_py(pattern)})", f"{page_var}.wait_for_load_state('domcontentloaded')"]
    else:
        raise SpecializedActionError(f"Tipo especializado sem emissor: {k.value}")
    return [indent + line if line else line for line in lines]


class SpecializedActionRegistry:
    """Registry explícito para runtime; duplicidade e tipo ausente falham cedo."""

    def __init__(self) -> None:
        self._handlers: dict[SpecializedActionType, Callable[..., Any]] = {}

    def register(self, kind: SpecializedActionType, handler: Callable[..., Any]) -> None:
        if kind in self._handlers:
            raise SpecializedActionError(f"Handler duplicado: {kind.value}")
        self._handlers[kind] = handler

    def execute(self, action: SpecializedAction, *, page: Any, state: Optional[MutableMapping[str, Any]] = None) -> Any:
        handler = self._handlers.get(action.kind)
        if handler is None:
            raise SpecializedActionError(f"Tipo especializado sem handler: {action.kind.value}")
        return handler(action=action, page=page, state=state if state is not None else {})


def _runtime_frame(*, action: SpecializedAction, page: Any, state: MutableMapping[str, Any]) -> Any:
    if action.kind is SpecializedActionType.FRAME_CROSS_ORIGIN:
        state.setdefault("limitations", []).extend(action.limitations)
        return None
    if not action.selector:
        raise SpecializedActionError("frame_context sem selector")
    frame = page.frame_locator(action.selector)
    state["frame"] = frame
    state["frame_id"] = action.frame_id
    return frame


def _runtime_popup(*, action: SpecializedAction, page: Any, state: MutableMapping[str, Any]) -> Any:
    trigger = action.payload.get("trigger")
    if not callable(trigger):
        raise SpecializedActionError(f"{action.kind.value} requer payload.trigger callable no runtime")
    with page.expect_popup() as info:
        trigger()
    new_page = info.value
    new_page.wait_for_load_state("domcontentloaded")
    state.setdefault("page_stack", []).append(page)
    state["page"] = new_page
    return new_page


def _runtime_upload(*, action: SpecializedAction, page: Any, state: MutableMapping[str, Any]) -> list[str]:
    files = _file_values(action)
    if not files:
        raise SpecializedActionError("file_upload sem arquivo parametrizado")
    missing = [path for path in files if not Path(path).is_file()]
    if missing:
        raise SpecializedActionError("Arquivo(s) inexistente(s): " + ", ".join(missing))
    page.set_input_files(action.selector or "input[type=file]", files if len(files) > 1 else files[0])
    state["last_upload_count"] = len(files)
    return files


def _runtime_download(*, action: SpecializedAction, page: Any, state: MutableMapping[str, Any]) -> str:
    trigger = action.payload.get("trigger")
    if not callable(trigger):
        raise SpecializedActionError("file_download requer payload.trigger callable no runtime")
    with page.expect_download() as info:
        trigger()
    download = info.value
    destination = Path(str(action.payload.get("destination") or "downloads"))
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / download.suggested_filename
    download.save_as(str(output))
    state["last_download"] = str(output)
    return str(output)


def _runtime_redirect(*, action: SpecializedAction, page: Any, state: MutableMapping[str, Any]) -> str:
    pattern = action.payload.get("url_pattern") or action.url
    if not pattern:
        raise SpecializedActionError(f"{action.kind.value} sem URL/padrão")
    page.wait_for_url(pattern)
    page.wait_for_load_state("domcontentloaded")
    state["url"] = page.url
    return page.url


def default_specialized_registry() -> SpecializedActionRegistry:
    registry = SpecializedActionRegistry()
    registry.register(SpecializedActionType.FRAME, _runtime_frame)
    registry.register(SpecializedActionType.FRAME_CROSS_ORIGIN, _runtime_frame)
    registry.register(SpecializedActionType.NEW_PAGE, _runtime_popup)
    registry.register(SpecializedActionType.POPUP, _runtime_popup)
    registry.register(SpecializedActionType.FILE_UPLOAD, _runtime_upload)
    registry.register(SpecializedActionType.FILE_DOWNLOAD, _runtime_download)
    registry.register(SpecializedActionType.NAVIGATION_REDIRECT, _runtime_redirect)
    registry.register(SpecializedActionType.AUTHENTICATION_REDIRECT, _runtime_redirect)
    return registry


def write_trace(path: str | os.PathLike[str], action: SpecializedAction, *, decision: str, result: Any = None) -> None:
    """JSONL de rastreabilidade; payload sensível não é serializado."""
    record = {
        "event_id": action.event_id,
        "specialized_type": action.kind.value,
        "page_id": action.page_id,
        "frame_id": action.frame_id,
        "decision": decision,
        "result": result,
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

