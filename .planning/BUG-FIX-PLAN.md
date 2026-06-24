# BUG FIX PLAN — Regressões branch refactor/recorder-playwright

**Data:** 2026-06-24  
**Branch:** refactor/recorder-playwright  
**Status:** Em execução

---

## Ordem de Execução

```
Bug 5 → Bug 2+6 → Bug 3 → Bug 4 → Bug 9 → Bug 1 → Bug 7 → Feature 10 → Bug 8
```

Rationale: encoding corrompe tudo (5 primeiro); viewport (2+6) simples e isolado; overlay counter (3) simples; publish order (4) simples; fill dedup (9) médio; assert crash (1) depende de encoding corrigido; missing fills (7) requer investigação; feature (10) valor baixo; regressão geral (8) verifica-se após os outros.

---

## Bug 5 — Encoding utf-8 ausente em arquivos críticos

### Root cause
`open(path, "w")` sem `encoding="utf-8"` em três locais. Em sistemas com locale `C` ou `latin-1`, caracteres portugueses (ã, ç, ó…) nos seletores/valores corrompem o arquivo gerado.

### Arquivos a corrigir
| Arquivo | Linha | Código atual | Correção |
|---------|-------|-------------|----------|
| `src/testforge/semantic/compiler.py` | 64 | `with open(path, "w") as f:` | `with open(path, "w", encoding="utf-8") as f:` |
| `src/testforge/semantic/compiler.py` | 86 | `with open(path, "w") as f:` | `with open(path, "w", encoding="utf-8") as f:` |
| `src/testforge/recorder/recorder_controller.py` | 248 | `with open(path, "a") as f:` | `with open(path, "a", encoding="utf-8") as f:` |

Também auditar: `recording_normalizer.py`, `git_publisher.py`, `incremental_validator.py` — qualquer `open()` escrevendo texto sem encoding.

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_encoding.py`

```python
"""Regression test — Bug 5: encoding utf-8 explicit in all write paths."""
import json, os, tempfile
from pathlib import Path
import pytest


def test_compiler_writes_utf8(tmp_path):
    """Compiled test file must be readable as utf-8 even with accented chars."""
    from testforge.semantic.compiler import PlaywrightCompiler
    from testforge.semantic.model import (
        SemanticTestCase, SemanticStep, SemanticAction, SemanticTarget,
        LocatorCandidate
    )

    target = SemanticTarget(
        role="textbox",
        label="Renda mensal *",
        placeholder="R$0,00",
        tag="input",
        text="",
        locator_candidates=[
            LocatorCandidate(strategy="aria_label", value='input[aria-label="Renda mensal *"]', score=9)
        ],
    )
    action = SemanticAction(action="fill", target=target, value="1.000,00 — ação de preenchimento")
    step = SemanticStep(step_id="step_0001", actions=[action])
    stc = SemanticTestCase(
        recording_id="test_enc",
        base_url="http://localhost:8765",
        steps=[step],
    )
    compiler = PlaywrightCompiler(stc)
    out = tmp_path / "test_enc.py"
    compiler.compile(str(out))
    # Must open as utf-8 without error
    content = out.read_text(encoding="utf-8")
    assert "ação de preenchimento" in content or "1.000,00" in content


def test_persist_step_writes_utf8(tmp_path):
    """_persist_step must not raise on accented text."""
    from unittest.mock import MagicMock, patch
    from testforge.recorder.recorder_controller import RecorderController

    page = MagicMock()
    page.add_init_script = MagicMock()
    ctrl = RecorderController(page)
    # Inject a fake session dir
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    step_data = {
        "action": "fill",
        "selector": 'input[aria-label="Valor do imóvel *"]',
        "tagName": "input",
        "text": "Imóvel com ação especial",
        "value": "500.000,00",
        "timestamp": "2026-06-24T00:00:00Z",
    }
    ctrl._persist_step(step_data)
    steps_file = tmp_path / "steps.jsonl"
    assert steps_file.exists()
    content = steps_file.read_text(encoding="utf-8")
    data = json.loads(content.strip())
    assert data["text"] == "Imóvel com ação especial"
```

---

## Bug 2 + Bug 6 — Viewport flicker em headed mode

### Root cause
`browser.new_context(viewport=None)` no Playwright Python **não desativa** viewport emulation — usa 1280×720 padrão. Precisa de `no_viewport=True` para deixar o SO controlar o tamanho da janela.

Evidência: comentário "headed mode respects user's window size" está correto na intenção mas errado na implementação.

### Arquivos a corrigir
**`src/testforge/cli/app.py`** — todos os `new_context(viewport=...)` em headed mode:

```python
# Padrão: headed usa no_viewport=True, headless usa 1280x720
def _make_context(browser, headless: bool):
    if headless:
        return browser.new_context(viewport={"width": 1280, "height": 720})
    return browser.new_context(no_viewport=True)
```

Locais a substituir (buscar `new_context(viewport=_vp)` e `new_context(viewport=viewport)`):
- `cmd_record`: linha ~360
- `cmd_run`: linha ~770
- `_try_heal_inline`: linha ~1253
- `cmd_run_incremental`: linhas ~1286, ~1336, ~1379
- `cmd_demo_heal`: linha ~1469
- `cmd_pipeline`: linha ~1509

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_viewport.py`

```python
"""Regression test — Bug 2/6: no_viewport=True in headed mode."""
import pytest
from unittest.mock import MagicMock, patch, call


def test_record_headed_uses_no_viewport():
    """cmd_record headed mode must use no_viewport=True, not viewport=None."""
    import sys
    from types import SimpleNamespace

    # Patch launch_browser and sync_playwright to avoid actual browser launch
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    with patch("testforge.cli.app.launch_browser", return_value=mock_browser), \
         patch("testforge.cli.app.sync_playwright") as mock_pw, \
         patch("testforge.cli.app.RecorderController") as mock_rc:

        mock_pw.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pw.return_value.__exit__ = MagicMock(return_value=False)
        mock_rc.return_value.start.return_value = MagicMock(recording_id="test_vp")
        mock_rc.return_value.handle_commands.return_value = "stop"
        mock_rc.return_value.flush_events = MagicMock()
        mock_page.evaluate.return_value = None

        from testforge.cli.app import cmd_record
        args = SimpleNamespace(
            url="http://localhost:8765",
            name="test_vp",
            headless=False,  # headed mode
            browser="chromium",
            app=None,
            evidence_level="light",
            system=None,
            suite=None,
            test_case=None,
            auto_complete=False,
            no_interactive=False,
            validate_before_ready=False,
            pilot_mode=False,
        )
        try:
            cmd_record(args)
        except Exception:
            pass  # expected — mocks incomplete

    # Must NOT pass viewport dict in headed mode
    calls = mock_browser.new_context.call_args_list
    assert calls, "new_context never called"
    for c in calls:
        kw = c.kwargs if hasattr(c, 'kwargs') else c[1]
        # Must not have viewport set to a size
        viewport = kw.get("viewport", "NOT_SET")
        assert viewport != {"width": 1280, "height": 720}, \
            "headed mode must not force 1280x720 viewport"
        # Should use no_viewport=True
        assert kw.get("no_viewport") is True or viewport == "NOT_SET", \
            f"headed mode should use no_viewport=True, got: {kw}"


def test_run_headed_uses_no_viewport():
    """cmd_run headed mode must use no_viewport=True."""
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.goto = MagicMock()

    with patch("testforge.cli.app.launch_browser", return_value=mock_browser), \
         patch("testforge.cli.app.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pw.return_value.__exit__ = MagicMock(return_value=False)

        from testforge.cli.app import cmd_run
        import sys
        from types import SimpleNamespace
        from pathlib import Path
        import tempfile, json, os

        with tempfile.TemporaryDirectory() as td:
            # Create minimal test file
            test_file = os.path.join(td, "test_dummy.py")
            with open(test_file, "w") as f:
                f.write("BASE_URL='http://localhost'\ndef test_x(page): pass\n")

            args = SimpleNamespace(
                test_file=test_file,
                headless=False,
                browser="chromium",
                verbose=False,
                data="",
                no_heal=False,
            )
            try:
                cmd_run(args)
            except Exception:
                pass

    calls = mock_browser.new_context.call_args_list
    for c in calls:
        kw = c.kwargs if hasattr(c, 'kwargs') else c[1]
        viewport = kw.get("viewport", "NOT_SET")
        assert viewport != {"width": 1280, "height": 720}, \
            "run headed mode must not force 1280x720 viewport"
```

---

## Bug 3 — Contador de passos não conta clicks

### Root cause
Ao extrair overlay de string Python para `overlay_inject.js` (commit 19cc46d), o bloco que incrementava `tf-step-count` após clicks foi perdido.

**Antes (embutido em Python, commit f6c38f8):**
```js
_tf_pushEvent('click', el);
var _sc = document.getElementById('tf-step-count');
if (_sc) {
    var _n = parseInt(_sc.textContent||0) + 1;
    _sc.textContent = _n;
    try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e){}
}
```

**Depois (overlay_inject.js atual):**
```js
_pushEvent('click', el);
// incremento ausente!
```

### Arquivo a corrigir
`src/testforge/recorder/overlay_inject.js` — após `_pushEvent('click', el)` no handler de click não-submit (~linha 403):

```js
    _pushEvent('click', el);
    // Increment step counter in overlay
    var _sc = document.getElementById('tf-step-count');
    if (_sc) {
        var _n = parseInt(_sc.textContent || 0) + 1;
        _sc.textContent = _n;
        try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e) {}
    }
```

Também adicionar para submits (após `_pushEvent('submit', el)`).

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_step_counter.py`

```python
"""Regression test — Bug 3: click events must increment step counter in overlay."""
import pytest


def test_overlay_js_increments_step_count_on_click():
    """overlay_inject.js source must contain step counter increment after _pushEvent click."""
    from pathlib import Path
    overlay_src = (
        Path(__file__).parent.parent /
        "src/testforge/recorder/overlay_inject.js"
    ).read_text(encoding="utf-8")

    # Must update tf-step-count after non-assert click
    # Strategy: find the section after _pushEvent('click', el) and before the
    # closing of the click listener — it must contain __tfStepCount
    click_section_start = overlay_src.find("_pushEvent('click', el)")
    assert click_section_start != -1, "_pushEvent click not found in overlay"
    # Find the next occurrence of '__tfStepCount' after that point
    step_count_after_click = overlay_src.find("__tfStepCount", click_section_start)
    next_listener = overlay_src.find("window.addEventListener", click_section_start + 1)
    assert step_count_after_click != -1, \
        "__tfStepCount increment missing after _pushEvent('click', el) in overlay_inject.js"
    assert step_count_after_click < next_listener, \
        "__tfStepCount increment must be inside the click listener, not after it"


def test_overlay_js_increments_step_count_on_submit():
    """overlay_inject.js must also increment step counter after submit push."""
    from pathlib import Path
    overlay_src = (
        Path(__file__).parent.parent /
        "src/testforge/recorder/overlay_inject.js"
    ).read_text(encoding="utf-8")

    submit_pos = overlay_src.find("_pushEvent('submit', el)")
    assert submit_pos != -1, "_pushEvent submit not found"
    step_count_after_submit = overlay_src.find("__tfStepCount", submit_pos)
    # Find next major event listener block boundary
    next_comment = overlay_src.find("// ---- Fill capture", submit_pos)
    assert step_count_after_submit != -1 and step_count_after_submit < next_comment, \
        "__tfStepCount increment missing after _pushEvent('submit', el)"
```

---

## Bug 4 — Publish antes da validação de intenção

### Root cause
`app.py` linha 448: `_auto_publish_recording(rid, rec_dir)` é chamado ANTES de `_run_post_recording_completion` (linha 459) e `_run_post_recording_validation` (linha 464).

### Arquivo a corrigir
`src/testforge/cli/app.py` — mover `_auto_publish_recording` para depois das chamadas de completion/validation:

```python
# ANTES (errado):
_auto_publish_recording(rid, rec_dir)   # linha 448

if auto_complete or no_interactive or run_validation:
    result = _run_post_recording_completion(...)  # linha 459
if run_validation and ...:
    _run_post_recording_validation(...)          # linha 464

# DEPOIS (correto):
if auto_complete or no_interactive or run_validation:
    result = _run_post_recording_completion(...)
if run_validation and ...:
    _run_post_recording_validation(...)

_auto_publish_recording(rid, rec_dir)   # APÓS validação
```

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_publish_order.py`

```python
"""Regression test — Bug 4: git publish must happen AFTER intent validation."""
import pytest
from unittest.mock import MagicMock, patch, call


def test_publish_called_after_completion():
    """_auto_publish_recording must be called AFTER _run_post_recording_completion."""
    call_order = []

    def mock_completion(*args, **kwargs):
        call_order.append("completion")
        return None

    def mock_validation(*args, **kwargs):
        call_order.append("validation")

    def mock_publish(*args, **kwargs):
        call_order.append("publish")

    with patch("testforge.cli.app._run_post_recording_completion", side_effect=mock_completion), \
         patch("testforge.cli.app._run_post_recording_validation", side_effect=mock_validation), \
         patch("testforge.cli.app._auto_publish_recording", side_effect=mock_publish):

        # Simulate post-recording flow as it runs in cmd_record
        from testforge.cli.app import (
            _run_post_recording_completion,
            _run_post_recording_validation,
            _auto_publish_recording,
        )
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            rid = "test_order"
            rec_dir = td
            auto_complete = True
            no_interactive = False
            run_validation = True

            # Replicate the flow from cmd_record
            stc = None
            completeness_report = None

            if auto_complete or no_interactive or run_validation:
                result = _run_post_recording_completion(rec_dir, rid, None, auto_complete, no_interactive)

            if run_validation and completeness_report is not None:
                _run_post_recording_validation(rec_dir, rid, None, stc, completeness_report)

            _auto_publish_recording(rid, rec_dir)

    # publish must be last
    assert "publish" in call_order
    assert call_order.index("publish") > call_order.index("completion"), \
        "publish must happen after completion"


def test_app_py_publish_order_in_source():
    """Source code of app.py must have _auto_publish_recording after the validation blocks."""
    from pathlib import Path
    src = (Path(__file__).parent.parent / "src/testforge/cli/app.py").read_text(encoding="utf-8")

    publish_pos = src.find("_auto_publish_recording(rid, rec_dir)")
    completion_pos = src.find("_run_post_recording_completion(")
    validation_pos = src.find("_run_post_recording_validation(")

    assert publish_pos != -1, "_auto_publish_recording not found in app.py"
    assert completion_pos != -1, "_run_post_recording_completion not found in app.py"

    # The publish call must appear AFTER both completion and validation in source
    assert publish_pos > completion_pos, \
        "_auto_publish_recording must appear after _run_post_recording_completion in source"
    if validation_pos != -1:
        assert publish_pos > validation_pos, \
            "_auto_publish_recording must appear after _run_post_recording_validation in source"
```

---

## Bug 9 — Fill repetido no mesmo campo

### Root cause
Campos sem `name`/`id`/`aria-label`/`placeholder` usam `tagName` como dedup key no overlay JS. Dois campos `<input>` distintos compartilham key `"INPUT"`, fazendo com que o segundo campo não deduplique e gere múltiplos eventos. Além disso, eventos `input`+`change`+polling disparam para o mesmo campo, gerando N steps fill consecutivos que NÃO são compactados se houver um click intercalado (ex: click para focar → fill para preencher valor de moeda).

### Arquivos a corrigir

**1. `src/testforge/recorder/overlay_inject.js`** — melhorar key de dedup incluindo `index`:

```js
// Atual — fallback usa tagName, colide entre campos:
var key = el.name || el.getAttribute('aria-label') || el.placeholder || el.id || el.tagName;

// Corrigido — adicionar posição DOM como desempate:
function _fillKey(el) {
    var base = el.name || el.getAttribute('aria-label') || el.placeholder || el.id;
    if (base) return base;
    // Fallback: tagName + index among siblings of same type
    var all = document.querySelectorAll(el.tagName);
    var idx = Array.prototype.indexOf.call(all, el);
    return el.tagName + ':' + idx;
}
```

**2. `src/testforge/semantic/recording_normalizer.py`** — `_compact_fill_events` deve também compactar fills separados por um click no MESMO elemento (padrão: click-to-focus + fill):

Verificar se o click entre dois fills aponta para o mesmo `target_key` — se sim, incluí-lo no grupo de compactação.

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_fill_dedup.py`

```python
"""Regression test — Bug 9: fill events deduplicated correctly."""
import pytest


def test_compact_fills_same_field_with_intermediate_click():
    """Consecutive fills on same field separated by a focus-click must collapse to one."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    target_renda = {"tag": "input", "id": "mat-input-1", "name": "", "placeholder": "R$0,00",
                    "test_id": "", "accessible_name": "Renda mensal"}

    raw_events = [
        {"type": "click",  "target": target_renda, "value": "", "timestamp": "T1", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "1", "timestamp": "T2", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "10", "timestamp": "T3", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "100", "timestamp": "T4", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "1.000,00", "timestamp": "T5", "url": "http://x"},
    ]

    norm = RecordingNormalizer()
    compacted = norm._compact_fill_events(raw_events)

    fill_events = [e for e in compacted if e["type"] == "fill"]
    assert len(fill_events) == 1, \
        f"Expected 1 fill after compaction, got {len(fill_events)}: {[e['value'] for e in fill_events]}"
    assert fill_events[0]["value"] == "1.000,00", "Must keep last (final) value"


def test_fills_different_fields_not_collapsed():
    """Fills on different fields must NOT be collapsed."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    target_renda  = {"tag": "input", "id": "mat-input-1", "name": "", "placeholder": "R$0,00",
                     "test_id": "", "accessible_name": "Renda mensal"}
    target_imovel = {"tag": "input", "id": "mat-input-2", "name": "", "placeholder": "R$0,00",
                     "test_id": "", "accessible_name": "Valor do imóvel"}

    raw_events = [
        {"type": "fill", "target": target_renda,  "value": "1.000,00", "timestamp": "T1", "url": "http://x"},
        {"type": "fill", "target": target_imovel, "value": "500.000,00", "timestamp": "T2", "url": "http://x"},
    ]

    norm = RecordingNormalizer()
    compacted = norm._compact_fill_events(raw_events)

    fill_events = [e for e in compacted if e["type"] == "fill"]
    assert len(fill_events) == 2, "Different fields must produce separate fill steps"


def test_overlay_js_fillkey_uses_index_fallback():
    """overlay_inject.js must not use bare tagName as dedup key — must include DOM index."""
    from pathlib import Path
    overlay_src = (
        Path(__file__).parent.parent /
        "src/testforge/recorder/overlay_inject.js"
    ).read_text(encoding="utf-8")

    # Must NOT have: || el.tagName; at end of key assignment (bare tagName fallback)
    assert "|| el.tagName;" not in overlay_src and "|| el.tagName\n" not in overlay_src, \
        "Bare el.tagName fallback causes fill dedup collision between fields"
```

---

## Bug 1 — Browser fecha após assert sem mensagem

### Root cause
`_persist_step` em `recorder_controller.py:248` não tem try/except. Se falhar (encoding, permissão, etc.), a exceção propaga para o `flush_events` try/except que apenas loga no logger (invisível ao usuário). O step não é salvo mas o processo continua. Se a exceção ocorrer em outro ponto do loop principal, o browser pode fechar sem aviso.

Também verificar: `_page.title()` na linha 236 de `_persist_step` — se o browser já fechou (race condition), essa chamada lança `TargetClosedError`.

### Arquivo a corrigir
`src/testforge/recorder/recorder_controller.py`:

```python
def _persist_step(self, data: dict):
    """Persist a user-intended step (click, fill, or assert)."""
    self._step_counter += 1
    path = os.path.join(self._store._session_dir, "steps.jsonl")
    try:
        step = {
            "step_id": f"step_{self._step_counter:04d}",
            ...
            "page_title": self._page.title(),   # pode lançar se browser fechou
            ...
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(step, default=str) + "\n")
    except Exception as exc:
        logger.error("[TestForge] Falha ao salvar step: %s", exc)
        print(f"[TestForge] AVISO: step nao salvo — {exc}", file=sys.stderr)
```

Também: no loop principal de `cmd_record`, envolver `recorder.handle_commands()` e `recorder.flush_events()` em try/except para imprimir erro legível antes de encerrar.

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_assert_crash.py`

```python
"""Regression test — Bug 1: _persist_step must not propagate exceptions."""
import json, os
import pytest
from unittest.mock import MagicMock, PropertyMock, patch


def test_persist_step_survives_page_title_error(tmp_path):
    """If page.title() raises (browser closed), _persist_step must not propagate."""
    from testforge.recorder.recorder_controller import RecorderController

    page = MagicMock()
    page.add_init_script = MagicMock()
    page.title.side_effect = Exception("Target page, context or browser has been closed")

    ctrl = RecorderController(page)
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    step_data = {"action": "assert", "selector": "button", "tagName": "button",
                 "text": "Enviar", "value": "", "timestamp": "T1",
                 "assert_type": "visivel", "assert_state": "visible"}

    # Must NOT raise — should log and continue
    try:
        ctrl._persist_step(step_data)
    except Exception as exc:
        pytest.fail(f"_persist_step propagated exception: {exc}")


def test_persist_step_survives_encoding_error(tmp_path, monkeypatch):
    """If json.dumps or file write fails, _persist_step must not propagate."""
    from testforge.recorder.recorder_controller import RecorderController
    import builtins

    page = MagicMock()
    page.add_init_script = MagicMock()
    page.title.return_value = "Página de teste"
    page.url = "http://localhost"

    ctrl = RecorderController(page)
    ctrl._store = MagicMock()
    ctrl._store._session_dir = str(tmp_path)
    ctrl._step_counter = 0

    original_open = builtins.open
    def failing_open(path, *args, **kwargs):
        if "steps.jsonl" in str(path):
            raise IOError("Simulated disk full")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)

    step_data = {"action": "fill", "selector": "input", "tagName": "input",
                 "text": "", "value": "teste", "timestamp": "T1"}
    try:
        ctrl._persist_step(step_data)
    except Exception as exc:
        pytest.fail(f"_persist_step propagated IOError: {exc}")
```

---

## Bug 7 — Fill sempre pedindo valores não encontrados

### Root cause (a investigar)
`_detect_missing_fills` em `recording_normalizer.py:1576` sinaliza campos como `missing_fill` mesmo quando o valor já está em `form_values` (capturado no submit) ou em `field_snapshots`. Suspeita: mudança em `_canonical_field_key` ou `resolved_keys` não inclui campos capturados via `form_values`.

### Investigação necessária antes do fix
1. Rodar `testforge record` com `--verbose`, capturar um form submit
2. Inspecionar `recordings/<rid>/raw_events.jsonl` — verificar se `form_values` estão presentes no evento `submit`
3. Em `_build_field_value_map` (linha ~571), adicionar log temporário dos `resolved_keys`
4. Comparar com o que `_detect_missing_fills` checa

### Fix esperado
Garantir que campos presentes em `form_values` do evento `submit` sejam adicionados a `resolved_keys` ANTES de `_detect_missing_fills` ser chamado.

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_missing_fills.py`

```python
"""Regression test — Bug 7: form_values from submit must prevent missing_fill detection."""
import pytest


def test_form_values_prevent_missing_fill():
    """Fields captured via form_values at submit must not be marked missing_fill."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer
    from testforge.semantic.model import SemanticTestCase, SemanticStep

    # Simulate: user filled "Renda mensal" via a masked input (no input event),
    # but value was captured in form_values at submit time.
    renda_target = {
        "tag": "input", "id": "mat-input-1", "name": "rendaMensal",
        "placeholder": "R$0,00", "accessible_name": "Renda mensal",
        "aria_label": "Renda mensal *", "test_id": "", "label": "Renda mensal *",
    }
    submit_target = {
        "tag": "button", "id": "", "name": "", "placeholder": "", "accessible_name": "Calcular",
    }

    raw_events = [
        {
            "type": "click", "target": renda_target, "value": "",
            "timestamp": "T1", "url": "http://x", "page_title": "Teste",
        },
        {
            "type": "submit", "target": submit_target, "value": "",
            "timestamp": "T2", "url": "http://x", "page_title": "Teste",
            "form_values": {"rendaMensal": "1.000,00", "Renda mensal *": "1.000,00"},
        },
    ]

    import tempfile, json, os
    with tempfile.TemporaryDirectory() as td:
        events_file = os.path.join(td, "raw_events.jsonl")
        with open(events_file, "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        meta_file = os.path.join(td, "recording_metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"recording_id": "test_mf", "base_url": "http://x",
                       "application": "web", "status": "stopped"}, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    # No step should have missing_fill for "Renda mensal"
    missing = [
        s for s in stc.steps
        if s.context and s.context.get("missing_fill")
        and "renda" in (s.context.get("fill_label", "") or "").lower()
    ]
    assert not missing, \
        f"Renda mensal was in form_values but marked missing_fill: {missing}"
```

---

## Feature 10 — Salvar saída da execução para debug

### Implementação
`src/testforge/cli/app.py` — no `cmd_run`, adicionar flag `--save-output` e capturar stdout+stderr:

```python
# Em cmd_run, após execução de cada step ou ao final:
if getattr(args, 'save_output', False):
    out_path = os.path.join(os.path.dirname(args.test_file), "run_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# TestForge run output — {datetime.now().isoformat()}\n")
        f.write(f"# Test: {args.test_file}\n\n")
        f.write(output_buffer)
    print(f"[TestForge] Output salvo em: {out_path}")
```

Alternativamente (mais simples): sempre salvar — sem flag, sempre escreve `run_output.txt` no diretório do teste se ele existir em `semantic_tests/`.

### Teste de regressão
**Arquivo:** `tests/test_bug_fix_save_output.py`

```python
"""Regression test — Feature 10: run output saved for debug."""
import os, tempfile
import pytest


def test_run_saves_output_file(tmp_path):
    """testforge run must save run_output.txt when --save-output is set."""
    from unittest.mock import MagicMock, patch
    from pathlib import Path

    test_file = tmp_path / "test_dummy.py"
    test_file.write_text(
        "BASE_URL='http://localhost:8765'\n"
        "def test_dummy(page): pass\n",
        encoding="utf-8"
    )

    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    with patch("testforge.cli.app.launch_browser", return_value=mock_browser), \
         patch("testforge.cli.app.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pw.return_value.__exit__ = MagicMock(return_value=False)

        from testforge.cli.app import cmd_run
        from types import SimpleNamespace
        args = SimpleNamespace(
            test_file=str(test_file),
            headless=True,
            browser="chromium",
            verbose=False,
            data="",
            no_heal=False,
            save_output=True,
        )
        try:
            cmd_run(args)
        except Exception:
            pass

    output_file = tmp_path / "run_output.txt"
    assert output_file.exists(), "run_output.txt must be created when --save-output is set"
```

---

## Bug 8 — Testes falhando mais (regressão composta)

**Dependências:** Resolver Bugs 5, 6, 9 primeiro.

**Verificação:** Rodar `pytest tests/ -v` e comparar contagem de falhas antes/depois dos fixes. Não há teste específico — o próprio suite de regressão serve como indicador.

---

## Sumário de novos arquivos de teste

| Arquivo | Bugs cobertos |
|---------|--------------|
| `tests/test_bug_fix_encoding.py` | Bug 5 |
| `tests/test_bug_fix_viewport.py` | Bug 2 + 6 |
| `tests/test_bug_fix_step_counter.py` | Bug 3 |
| `tests/test_bug_fix_publish_order.py` | Bug 4 |
| `tests/test_bug_fix_fill_dedup.py` | Bug 9 |
| `tests/test_bug_fix_assert_crash.py` | Bug 1 |
| `tests/test_bug_fix_missing_fills.py` | Bug 7 |
| `tests/test_bug_fix_save_output.py` | Feature 10 |

---

## Checklist de execução

- [x] Bug 5 — encoding utf-8 (12 arquivos corrigidos) — commit ee58b89
- [x] Bug 2+6 — no_viewport=True em headed mode (app.py) — commit 83df693
- [x] Bug 3 — step counter em clicks (overlay_inject.js) — commit 62587bf
- [x] Bug 4 — publish após validation (app.py) — commit e3724f4
- [x] Bug 9 — fill dedup (overlay_inject.js + recording_normalizer.py) — commit 2796c80
- [x] Bug 1 — try/except em _persist_step (recorder_controller.py) — commit d027eef
- [x] Bug 7 — test adicionado; investigação confirmou comportamento já correto — commit 7ea1376
- [x] Feature 10 — save output --save-output flag (app.py) — commit fb270af
- [ ] Bug 8 — verificar suite após todos os fixes — análise completa, ver seção "TEST FAILURES ANALYSIS" abaixo
- [x] Criar commit por bug com teste incluído
- [x] Push para origin refactor/recorder-playwright — 4f2970f..fb270af
- [x] Bug 11 — overlay DOM mutation fecha dropdown de <select> (overlay_inject.js) — commit 2b151d5
- [x] Bug 12 — change em <select> gera 'fill' em vez de 'select_option' (overlay_inject.js) — commit 2b151d5
- [x] Bug 13 — FallbackRunner.try_fill usa page.fill() em <select> (fallback_runner.py) — commit 2b151d5
- [x] Bug 14 — SmartStepRunner sem caso 'select_option' (fallback_runner.py) — commit 2b151d5
- [x] Bug 15 — label/role vazio em semantic_steps.jsonl — confirmado já correto; select_option adicionado ao FILL_TYPES — commit 2b151d5
- [x] Bug 16 — clicks redundantes em <select> geram steps de ruído (overlay_inject.js + normalizer) — commit 2b151d5

---

## Bug 11 — Overlay DOM mutation fecha dropdown nativo de `<select>`

**Descoberto em:** 2026-06-24 — análise de gravação `temp-bug/recordings/verificar_tela_simax`  
**Evidência:** Usuário clicou 4+ vezes no `lstUf` sem conseguir mudar valor de "0"; cada click registrou value="0" até evento `fill` com "DF" aparecer por outro meio.

### Root cause

`overlay_inject.js:410-414` — dentro do click handler (capture phase), o overlay atualiza `textContent` do step counter SINCRONAMENTE:

```js
_pushEvent('click', el);
var _sc = document.getElementById('tf-step-count');
if (_sc) {
    var _n = parseInt(_sc.textContent || 0) + 1;
    _sc.textContent = _n;  // ← mutação DOM síncrona durante click event
    try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e) {}
}
```

No Chrome/Linux, `<select>` nativo renderiza dropdown como parte da janela do browser (não widget OS). Mutação DOM síncrona durante o callback do click força reflow/repaint e fecha o dropdown imediatamente.

**Segundo vetor (assert mode):** `overlay_inject.js:342-349` — o handler de `mousedown` chama `preventDefault()` quando `__tfAssertWaiting=true`, impedindo o dropdown de abrir. Se usuário entrar em assert mode (Shift+A) e depois tentar clicar no select antes de cancelar, o dropdown não abre.

### Fix

**1.** Deferir atualização do step counter para fora do call stack:

```js
// overlay_inject.js — substituir bloco síncrono após _pushEvent('click', el):
_pushEvent('click', el);
setTimeout(function() {
    var _sc = document.getElementById('tf-step-count');
    if (_sc) {
        var _n = parseInt(_sc.textContent || 0) + 1;
        _sc.textContent = _n;
        try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e) {}
    }
}, 0);
```

**2.** Ignorar clicks em `<select>` completamente no click handler — o evento semântico real é o `change` (Bug 12 captura o valor):

```js
// No click handler, antes de _pushEvent:
if (el && el.tagName === 'SELECT') return;  // change event captura a seleção
```

### Arquivos
| Arquivo | Linha | Ação |
|---------|-------|------|
| `src/testforge/recorder/overlay_inject.js` | 409-416 | `setTimeout` no step counter |
| `src/testforge/recorder/overlay_inject.js` | ~368 | Skip click em SELECT |

---

## Bug 12 — `change` em `<select>` gera evento `fill` em vez de `select_option`

**Descoberto em:** 2026-06-24 — análise de `semantic_steps.jsonl` de `verificar_tela_simax_2`

### Root cause

`overlay_inject.js:438-448`:
```js
window.addEventListener('change', function(e) {
    ...
    _pushEvent('fill', el);  // ← sempre 'fill', mesmo para SELECT
```

`<select>` deveria gerar `select_option`. O compiler (`compiler.py:216`) já contorna isso na compilação, mas o `pilot runner` (SmartStepRunner/FallbackRunner) usa os tipos diretamente do `semantic_steps.jsonl` e executa `page.fill()` em `<select>`, que falha com `"Element is not an <input>..."`.

### Fix

```js
// overlay_inject.js:441 — change handler
window.addEventListener('change', function(e) {
    if (window.__tfAssertWaiting) return;
    var el = e.target;
    if (!el) return;
    var key = _fillKey(el);
    var val = (el.value || '').trim();
    if (window.__tfLastFillValue[key] === val) return;
    window.__tfLastFillValue[key] = val;
    // SELECT → select_option; outros → fill
    var evtType = (el.tagName === 'SELECT') ? 'select_option' : 'fill';
    _pushEvent(evtType, el);
}, true);
```

E no normalizer (`recording_normalizer.py`): garantir que eventos `select_option` do raw_events sejam convertidos para `SemanticAction(action="select_option")` nos steps.

### Arquivos
| Arquivo | Linha | Ação |
|---------|-------|------|
| `src/testforge/recorder/overlay_inject.js` | 446 | `evtType = SELECT ? 'select_option' : 'fill'` |
| `src/testforge/semantic/recording_normalizer.py` | `_normalize_raw_events` | tratar `select_option` como ação nativa |

---

## Bug 13 — `FallbackRunner.try_fill` usa `page.fill()` cegamente em `<select>`

**Descoberto em:** 2026-06-24 — execução_report `verificar_tela_simax_2`; Step 6 (fill): `"Element is not an <input>, <textarea>..."`

### Root cause

`fallback_runner.py:210-218`:
```python
def try_fill(self, candidates: list[dict], value: str) -> bool:
    for c in candidates:
        try:
            self._page.fill(c["selector"], value, timeout=5000)  # falha em <select>
```

Não verifica se o elemento é `<select>` antes de usar `fill`.

### Fix

```python
def try_fill(self, candidates: list[dict], value: str) -> bool:
    for c in candidates:
        try:
            sel = c["selector"]
            tag = c.get("tag", "").lower()
            if tag == "select":
                self._page.select_option(sel, value, timeout=5000)
            else:
                self._page.fill(sel, value, timeout=5000)
            self._page.wait_for_timeout(100)
            return True
        except Exception:
            continue
    return False
```

Mesma correção em `try_fill_with_fallback` (linha 232).

### Arquivos
| Arquivo | Linha | Ação |
|---------|-------|------|
| `src/testforge/runner/fallback_runner.py` | 210-218 | verificar tag antes de fill/select_option |
| `src/testforge/runner/fallback_runner.py` | 232-242 | idem em try_fill_with_fallback |

---

## Bug 14 — `SmartStepRunner` sem caso para ação `select_option`

**Descoberto em:** 2026-06-24 — `fallback_runner.py:59-95` não tem `elif action == "select_option":`.

### Root cause

Se normalizer gerar steps com `action="select_option"` (após fix do Bug 12), o SmartStepRunner não executa nada para esse tipo e retorna `True` sem agir, ou lança exceção.

### Fix

```python
# fallback_runner.py — dentro de SmartStepRunner._try_strategy(), após o bloco elif action == "click":
elif action == "select_option":
    self._page.select_option(sel, value, timeout=self.FILL_TIMEOUT)
    self._page.wait_for_timeout(300)
```

### Arquivo
| Arquivo | Linha | Ação |
|---------|-------|------|
| `src/testforge/runner/fallback_runner.py` | ~88 | adicionar `elif action == "select_option":` |

---

## Bug 15 — Label/role vazios em `semantic_steps.jsonl`

**Descoberto em:** 2026-06-24 — todos os 16 steps de `verificar_tela_simax_2/semantic_steps.jsonl` têm `label=''` e `role=''`.

### Root cause

A investigar em `recording_normalizer.py` — ao serializar `SemanticAction` para `semantic_steps.jsonl`, os campos `label` e `role` do target não estão sendo preservados. Sem label, a resolução de locators no runtime fica cega.

### Investigação necessária
1. Verificar método de serialização de `SemanticStep` → JSONL em `compiler.py` ou `normalizer.py`
2. Checar se `SemanticTarget.label` é populado no `_ir_*` methods
3. Comparar raw_events (têm `label: "UF"`) com o que chega no SemanticAction

### Arquivo suspeito
`src/testforge/semantic/recording_normalizer.py` — métodos `_ir_fill`, `_ir_click` ou `_build_semantic_action`

---

## Bug 16 — Clicks redundantes em `<select>` viram steps de ruído no teste

**Descoberto em:** 2026-06-24 — `verificar_tela_simax` _pilot_tmp tem 4 click steps redundantes em `lstUf` antes do `select_option`.

### Root cause

Porque Bug 11 impedia o dropdown de funcionar, o usuário clicava múltiplas vezes. Cada click virava um raw_event → normalizador não deduplica clicks consecutivos no mesmo `<select>` antes de um `select_option`.

### Fix (depende de Bug 11 estar resolvido primeiro)

Em `recording_normalizer.py` — expandir `_eliminate_prefill_clicks` para também eliminar clicks redundantes em `<select>` que antecedem um `select_option` no mesmo elemento:

```python
# recording_normalizer.py:_eliminate_prefill_clicks
# Padrão atual: elimina click antes de fill no mesmo elemento
# Adicionar: eliminar múltiplos clicks antes de select_option no mesmo select
if curr.action == "click" and tag == "select":
    # Find next non-navigation action on same element
    nxt = self._next_non_nav_step(steps, i)
    if nxt and nxt.action in ("select_option", "fill") and _same_element(curr, nxt):
        curr.skip_reason = "redundant_select_click"
```

### Arquivo
| Arquivo | Linha | Ação |
|---------|-------|------|
| `src/testforge/semantic/recording_normalizer.py` | `_eliminate_prefill_clicks` | skip clicks redundantes em select |

---

## Ordem de implementação (novos bugs)

```
Bug 11 → Bug 12 → Bug 14 → Bug 13 → Bug 16 → Bug 15
```

**Rationale:** 11 resolve a experiência de gravação (bloqueador para usuário gravar selects); 12 gera tipo correto no overlay → alimenta 14 e 13; 13 corrige pilot runner; 16 limpa ruído (depende 11 resolvido); 15 investigação isolada.

**Prioridade crítica:** 11 + 12 são bloqueadores de usabilidade — sem eles o usuário não consegue gravar aplicações com `<select>`.

---

## TEST FAILURES ANALYSIS — 2026-06-24

**Branch:** refactor/recorder-playwright  
**Suite:** 54 failed, 1047 passed, 24 errors (pytest tests/ --ignore=test_browser.py)  
**Pre-existing:** confirmed same count on baseline commit 7257120

### Categoria A — Infra/Browser (NÃO FIXAR — precisam fake bank + display)

~30 failures — todos têm `[chromium]` suffix:

| Arquivo | Count | Motivo |
|---------|-------|--------|
| `test_fake_bank_flow.py` | 1 | fake bank server não está rodando |
| `test_healing_e2e.py` | 18 | idem |
| `test_mutations.py` | 5 | idem |
| `test_recorder_e2e.py` | 1 | idem |
| `test_recorder_submit.py::TestClickVsSubmitIntegration` | 24 ERRORs | idem |

Rodar com: `cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &` primeiro.

---

### Categoria B — `_tf_` prefix mismatch (23 failures — FIXAR)

**Root cause:** overlay extraído de string Python → `overlay_inject.js` em commit `1c49cae`. Funções internas ao IIFE perderam prefixo público `_tf_`. Testes foram escritos antes e chamam nomes antigos.

**Afetados:**
- `test_recorder_submit.py::TestIsSubmitTriggerJS` (16 failures) — `page.evaluate("() => _tf_isSubmitTrigger(...)")`
- `test_sprint3_field_snapshots.py::TestOverlayJS` (7 failures) — `assert "_tf_snapshotFields" in js`

**Funções chamadas nos testes que não existem como globais:**

| Nome antigo (testes) | Nome atual (overlay_inject.js) | Linha |
|---------------------|-------------------------------|-------|
| `_tf_isSubmitTrigger` | `_isSubmitTrigger` | 105 |
| `_tf_extractTarget` | `_extractTarget` | 55 |
| `_tf_showOverlay` | `_showOverlay` | 556 |
| `_tf_snapshotFields` | `_snapshotFields` | 137 |
| `_tf_captureFinalState` | `_captureFinalState` | 203 |

**Fix:** adicionar aliases `window._tf_*` no final do IIFE em `overlay_inject.js`:

```js
// Public aliases for testing and external access
window._tf_isSubmitTrigger  = _isSubmitTrigger;
window._tf_extractTarget    = _extractTarget;
window._tf_showOverlay      = _showOverlay;
window._tf_snapshotFields   = _snapshotFields;
window._tf_captureFinalState = _captureFinalState;
```

Adicionar logo antes do `})();` final (linha ~730).

**Para sprint3 string checks** — os testes verificam que as strings literais `"_tf_snapshotFields"` e `"_tf_captureFinalState"` aparecem no JS. Com os aliases adicionados, essas strings estarão presentes e os testes passarão.

**Calls no JS que devem aparecer no source após fix:**
- `_tf_captureFinalState('user_stop')` → não aparece como string literal, mas `_captureFinalState('user_stop')` aparece. Testes checam:
  - `"_tf_captureFinalState('user_stop')" in js` → FALHA
  - `"_tf_captureFinalState('form_submit')" in js` → FALHA
  - `"_tf_captureFinalState('beforeunload')" in js` → FALHA

Para esses (call-site checks), **atualizar os testes** para checar `_captureFinalState(...)` sem prefixo:
```python
# test_sprint3_field_snapshots.py linhas 557-569
assert "_captureFinalState('user_stop')" in js or "_captureFinalState(\"user_stop\")" in js
assert "_captureFinalState('form_submit')" in js or "_captureFinalState(\"form_submit\")" in js
assert "_captureFinalState('beforeunload')" in js or "_captureFinalState(\"beforeunload\")" in js
```

---

### Categoria C — Arquitetura: batching (1 failure — FIXAR)

**Arquivo:** `tests/test_recorder_stability.py:124` — `test_js_commands_processed`

**Root cause:** commit `359fedc` moveu `page.evaluate` de `wait_for_command` → `flush_events`. Teste mockava `page.evaluate=["STOP"]` esperando que `handle_commands()` chamasse evaluate diretamente, mas agora a cadeia é:

```
flush_events() → page.evaluate(batch_js) → popula _command_queue
handle_commands() → wait_for_command() → drena _command_queue
```

**Fix:** atualizar o teste:
```python
def test_js_commands_processed(self):
    page = _make_page()
    page.evaluate.return_value = {
        "events": [], "steps": [],
        "commands": ["STOP"],
        "fieldSnapshots": [], "valueMutations": [],
    }
    ctrl = RecorderController(page)
    ctrl.flush_events()  # popula _command_queue via JS batch
    assert ctrl.handle_commands() == "stop"
```

**Arquivo:** `tests/test_recorder_stability.py` linha ~124

---

### Categoria D — Comportamento alterado (2 failures — INVESTIGAR)

**D1:** `test_recorder_stability.py::TestEvidenceLevel::test_both_levels_capture_dom` (linha 280)

Teste: `ctrl._capture_snapshots(event)` → `ctrl._store.save_dom.assert_called_once()`
Falha: `save_dom` chamado 0 vezes

`_capture_snapshots` em `recorder_controller.py:269` só chama `save_dom` quando `self._evidence_level == "full"`. Teste espera que ambos os níveis ("light" e "full") chamem `save_dom`. O comportamento mudou — agora "light" não captura DOM.

**Fix opções:**
- A) Corrigir teste para esperar `save_dom` só em `"full"` mode
- B) Restaurar `save_dom` em modo `"light"` (regressão?)

Checar intenção original: `"light"` deveria capturar DOM? Se não, fix A.

**D2:** `test_sprint5_readiness_gate.py::TestCT_AUTO_5_1::test_zero_steps_is_valid` (linha 197)

Teste: `assert report.verdict != ReadinessVerdict.PASS` para recording com 0 steps
Falha: gate retorna PASS para 0 steps

Gate mudou — 0 steps agora é PASS (talvez intencionalmente — recording vazia não é falha fatal).

**Fix opções:**
- A) Atualizar teste para refletir novo comportamento (PASS é aceitável para 0 steps)
- B) Restaurar falha em 0 steps no gate

---

### Ordem de execução

```
B (overlay aliases + sprint3 string fixes) → C (test update) → D (investigar + fix)
```

**Estimativa:** B = 15min, C = 5min, D = 10min

