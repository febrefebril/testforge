
from __future__ import annotations

from pathlib import Path

import pytest

from testforge.semantic.specialized_actions import (
    SpecializedAction,
    SpecializedActionError,
    SpecializedActionRegistry,
    SpecializedActionType,
    emit_specialized_python,
    normalize_specialized_event,
)


def test_file_upload_from_existing_raw_contract():
    action = normalize_specialized_event({
        "event_id": "evt-1",
        "type": "fill",
        "target": {"element_id": "arquivo"},
        "file_upload": [{"name": "massa.csv", "size": 12, "type": "text/csv"}],
    })
    assert action is not None
    assert action.kind is SpecializedActionType.FILE_UPLOAD
    assert action.selector == "#arquivo"
    assert action.payload["files"][0]["name"] == "massa.csv"


def test_frame_same_origin_emits_frame_locator():
    action = SpecializedAction(SpecializedActionType.FRAME, selector="iframe[name=main]")
    assert emit_specialized_python(action) == ["frame = page.frame_locator('iframe[name=main]')"]


def test_cross_origin_is_explicit_limitation():
    action = normalize_specialized_event({"type": "iframe_cross_origin", "url": "https://idp.example/"})
    assert action is not None
    assert action.limitations
    assert "LIMITATION" in emit_specialized_python(action)[0]


def test_popup_requires_explicit_trigger():
    action = SpecializedAction(SpecializedActionType.POPUP)
    with pytest.raises(SpecializedActionError, match="trigger_python"):
        emit_specialized_python(action)


def test_upload_never_emits_fakepath():
    action = SpecializedAction(
        SpecializedActionType.FILE_UPLOAD,
        selector="input[type=file]",
        payload={"paths": ["fixtures/documento.pdf"]},
    )
    source = "\n".join(emit_specialized_python(action))
    assert "set_input_files" in source
    assert "fakepath" not in source.lower()


def test_download_emits_expect_download():
    action = SpecializedAction(
        SpecializedActionType.FILE_DOWNLOAD,
        payload={"trigger_python": "page.get_by_role('button', name='Baixar').click()"},
    )
    source = "\n".join(emit_specialized_python(action))
    assert "expect_download" in source
    assert "suggested_filename" in source


def test_redirect_requires_pattern():
    action = SpecializedAction(SpecializedActionType.AUTHENTICATION_REDIRECT)
    with pytest.raises(SpecializedActionError, match="URL/padrão"):
        emit_specialized_python(action)


def test_registry_rejects_duplicate():
    registry = SpecializedActionRegistry()
    registry.register(SpecializedActionType.FRAME, lambda **_: None)
    with pytest.raises(SpecializedActionError, match="duplicado"):
        registry.register(SpecializedActionType.FRAME, lambda **_: None)


def test_regular_event_is_not_claimed():
    assert normalize_specialized_event({"type": "click", "event_id": "evt-2"}) is None

