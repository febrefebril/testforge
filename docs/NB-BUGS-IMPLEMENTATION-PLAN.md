# NB Bugs — Plano de Implementação (23 bugs)

**Escopo**: NB-01 a NB-24 (menos NB-20 retirado — user apagou snapshots).  
**Origem**: análise 4 gravações `PDes.zip` em `docs/RECORDING-BUGS-NEW-BATCH-PDES.md`.  
**Branch**: `feature/inline-overlay-prompt` (branch ativa — NÃO criar nova).  
**Sanity baseline**: **377 passed, 1 xfailed** com `pytest -m "unit or contract or regression" -q`.

---

## Contratos hard (nunca quebrar)

1. **`[[feedback-pii-alert-only]]`** — dados sensíveis fazem parte da massa de teste. NUNCA mascarar values. TestForge só detecta + alerta. Tarefa da LLM: garantir que `keystroke_buffer.jsonl` (e qualquer outro artefato com secrets) fique **fora do repo git** mas presente no filesystem local do gravador.
2. **`[[feedback-no-regrave]]`** — nunca regravar para testar. Iterar `compile + run` sobre gravações existentes em `PDes.zip` (`/tmp/pdes_extract/`).
3. **`[[feedback-no-regression]]`** — sanity gate `pytest -m "unit or contract or regression" -q` deve continuar verde após cada commit.

Se algum fix violar um contrato, PAUSAR e pedir clarificação. Não improvisar.

---

## Contexto obrigatório antes de começar

Leia nesta ordem:
1. `docs/RECORDING-BUGS-NEW-BATCH-PDES.md` — catálogo completo com origem/evidência de cada bug.
2. `docs/FASE-9-IMPLEMENTATION-PLAN.md` — modelo do estilo esperado (fizemos Fase 9 assim).
3. `docs/CLAUDE.md` — arquitetura do projeto.
4. `src/testforge/recorder/overlay_inject.js` — 2100+ linhas, ler seções relevantes por bug.
5. `src/testforge/cli/app.py` — CLI + `_mark_failed_recording`, `_sanitize_name`.
6. `src/testforge/security/recording_scanner.py` + `src/testforge/security/pii_detector.py`.
7. `src/testforge/publisher/git_publisher.py`.
8. Amostras: `/tmp/pdes_extract/PLATAFORMA DES/` (extrair `PDes.zip` no root do projeto se não estiver).

---

## Ordem de trabalho e commits

23 commits, agrupados em 4 "waves". Cada wave é auto-contida. Rodar sanity ao final de cada commit.

### Wave 1 — Alertas + segurança (2 commits, NB-12)

Ordem: **NB-12 é o primeiro** — sem isso senha real do usuário vaza no git.

### Wave 2 — Overlay fixes (5 commits, NB-08, NB-02, NB-01, NB-13, NB-04)

Corrige overlay pollution. NB-13 (compiler) tem que vir junto com NB-01 (recorder) porque as gravações antigas já contêm lixo — normalizer precisa filtrar.

### Wave 3 — Blockers de gravação (6 commits, NB-05+19, NB-09, NB-10, NB-11, NB-03, NB-14)

Auto-fire + storage + cross-origin + attrs serialization.

### Wave 4 — Ruído/UX/consistência (10 commits, NB-15, NB-16, NB-17, NB-06, NB-24, NB-07, NB-22, NB-18, NB-21, NB-23)

Bugs de qualidade menor. NB-23 é métrica de validação final.

---

## Convenções

**Naming de testes**: `test_<component>_when_<condition>_then_<expected>.py`.  
**Commits**: `<type>(<scope>): NB-XX <descrição curta>`. Formato exato dos commits da Fase 9 (ver `git log --oneline 22a8cb0^..3c954ed`).  
**Nunca use `--no-verify` no commit.**

**Testes de overlay JS**: static tests que leem `overlay_inject.js` como texto e usam regex. Padrão em `tests/unit/recorder/test_value_mutation_dedup.py`. NÃO tentar rodar JS no pytest.

**Testes com filesystem**: `tmp_path` fixture. NUNCA tocar diretórios reais do projeto exceto sob controle explícito.

---

# NB-12 — keystroke_buffer no scanner + fora do repo [WAVE 1]

## Origem

Arquivo `/tmp/pdes_extract/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda/keystroke_buffer.jsonl` contém:
```json
{"fingerprint": "input#password[name=password]", "key": "L", "kind": "char", ...}
{"fingerprint": "input#password[name=password]", "key": "a", "kind": "char", ...}
...
```
Reconstrução: `"&lt;SENHA&gt;"`.

## Confirmar antes de implementar

```bash
python3 -c "
import json
lines = [json.loads(l) for l in open('/tmp/pdes_extract/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda/keystroke_buffer.jsonl') if l.strip()]
pwd = [l for l in lines if 'password' in l.get('fingerprint','')]
print(f'password keystrokes: {len(pwd)}')
print('reconstruído:', ''.join(k.get('key','?') for k in pwd if k.get('kind')=='char'))
"
# Esperado: 8 keystrokes, "&lt;SENHA&gt;" (ou similar).
```

## Fix

### 12A — recording_scanner varre keystroke_buffer

`src/testforge/security/recording_scanner.py` — após a chamada de `_scan_jsonl_lines` para `field_snapshots.jsonl` (linhas ~130), adicionar:

```python
# NB-12: cobrir keystroke_buffer.jsonl. Cada entrada é uma tecla; alerta é
# por FINGERPRINT (aggregation) — value fica preservado (contrato alert-only).
def _handle_keystroke(entry: dict, report: ScanReport, line_num: int) -> None:
    fp = (entry.get("fingerprint") or "").strip()
    key = entry.get("key", "")
    kind = entry.get("kind", "")
    if kind != "char" or not fp:
        return
    md: dict = {"fingerprint": fp}
    if "password" in fp.lower():
        md["type"] = "password"
    hits = detect(key, source=f"keystroke_buffer:{fp}", metadata=md)
    if hits:
        report.hits_by_source.setdefault(f"keystroke_buffer:{fp}", []).extend(hits)

_scan_jsonl_lines(
    rec_path / "keystroke_buffer.jsonl",
    report,
    source_prefix="keystroke_buffer",
    handler=_handle_keystroke,
)
```

### 12B — publisher exclui keystroke_buffer do git-tracked snapshot

`src/testforge/publisher/git_publisher.py` — perto do topo do módulo (linhas ~20-30):

```python
# NB-12: arquivos que nunca vão pro repo git compartilhado (contêm secrets
# em plaintext OR são reconstrução tecla por tecla). Continuam existindo
# localmente em recordings/<id>/ para debug e healing.
_NEVER_PUBLISH_FILENAMES = frozenset({
    "keystroke_buffer.jsonl",
})
```

No método `_copy_artifacts` (ou onde os arquivos do recording são copiados para `dest_dir`):

```python
# Skip files that must never enter the tracked repo.
if filename in _NEVER_PUBLISH_FILENAMES:
    continue
```

Se `_copy_artifacts` usa `shutil.copytree`, trocar por versão manual que itera arquivos e aplica o filtro. Existe algum `copytree` com `ignore` callback:

```python
def _ignore_never_publish(_src, names):
    return [n for n in names if n in _NEVER_PUBLISH_FILENAMES]

shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_ignore_never_publish)
```

### 12C — .gitignore raiz

Adicionar ao final de `.gitignore` (raiz do projeto):

```
# NB-12: keystroke buffer nunca vai pro repo — contém teclas por tecla incluindo
# campos password. Massa de teste é preservada localmente (contrato feedback-pii-alert-only)
# mas nunca commitada. Sem este ignore, gravações ficaram vulneráveis a leak.
**/keystroke_buffer.jsonl
```

### 12D — Alert de compile/publish quando keystroke_buffer tem senha

`src/testforge/cli/app.py` — antes de `_local_publish` (ou onde publisher é chamado):

```python
# NB-12: quando keystroke_buffer indicar password field, emitir alerta
# não bloqueante avisando que arquivo será mantido local e NÃO enviado ao repo.
try:
    from testforge.security.recording_scanner import scan_recording
    report = scan_recording(rec_dir)
    kb_pwd_sources = [
        s for s in report.hits_by_source
        if s.startswith("keystroke_buffer:") and "password" in s.lower()
    ]
    if kb_pwd_sources:
        print(f"[TestForge] [ALERTA] {len(kb_pwd_sources)} campo(s) password"
              f" detectado(s) em keystroke_buffer.jsonl.")
        print(f"  Arquivo será PRESERVADO localmente para debug (contrato:"
              f" massa de teste mantida).")
        print(f"  Arquivo NÃO será enviado ao repositório git (.gitignore + publisher exclude).")
except Exception:
    pass
```

## Teste

### tests/unit/security/test_scanner_when_keystroke_buffer_password_then_alerts.py

```python
"""NB-12: recording_scanner varre keystroke_buffer.jsonl e alerta senha."""
import json
import pytest


@pytest.mark.unit
class TestScannerWhenKeystrokeBufferPasswordThenAlerts:
    def test_password_keystrokes_generate_hits(self, tmp_path):
        from testforge.security.recording_scanner import scan_recording

        rec = tmp_path / "test_rec"
        rec.mkdir()
        (rec / "recording_metadata.json").write_text(
            json.dumps({"base_url": "https://tqs.example.com/", "recording_id": "test_rec"})
        )
        (rec / "keystroke_buffer.jsonl").write_text("\n".join(json.dumps({
            "fingerprint": "input#password[name=password]",
            "key": k, "kind": "char",
        }) for k in "&lt;SENHA&gt;"))
        (rec / "raw_events.jsonl").write_text("")

        report = scan_recording(str(rec))
        sources_with_pwd = [s for s in report.hits_by_source if "password" in s.lower()]
        assert sources_with_pwd, (
            "NB-12: scanner must emit at least one hit source with 'password' "
            "when keystroke_buffer contains password field keystrokes."
        )

    def test_non_password_field_not_flagged_as_password(self, tmp_path):
        from testforge.security.recording_scanner import scan_recording

        rec = tmp_path / "test_rec"
        rec.mkdir()
        (rec / "recording_metadata.json").write_text(json.dumps({"base_url": "https://tqs.x/"}))
        (rec / "keystroke_buffer.jsonl").write_text(json.dumps({
            "fingerprint": "input#username[name=username]",
            "key": "a", "kind": "char",
        }))
        (rec / "raw_events.jsonl").write_text("")

        report = scan_recording(str(rec))
        pwd_sources = [s for s in report.hits_by_source if "password" in s.lower()]
        assert not pwd_sources, "NB-12: username field must not be classified as password."
```

### tests/unit/publisher/test_publisher_when_keystroke_buffer_present_then_excluded.py

```python
"""NB-12: git_publisher exclui keystroke_buffer.jsonl do snapshot copiado."""
import pytest


@pytest.mark.unit
class TestPublisherWhenKeystrokeBufferPresentThenExcluded:
    def test_never_publish_list_contains_keystroke_buffer(self):
        from testforge.publisher.git_publisher import _NEVER_PUBLISH_FILENAMES
        assert "keystroke_buffer.jsonl" in _NEVER_PUBLISH_FILENAMES, (
            "NB-12: _NEVER_PUBLISH_FILENAMES must include keystroke_buffer.jsonl."
        )
```

### tests/unit/security/test_gitignore_when_read_then_blocks_keystroke_buffer.py

```python
"""NB-12: .gitignore no root bloqueia keystroke_buffer.jsonl em qualquer subpath."""
import pathlib
import pytest


@pytest.mark.unit
class TestGitignoreWhenReadThenBlocksKeystrokeBuffer:
    def test_gitignore_lists_keystroke_buffer(self):
        gi = pathlib.Path(__file__).resolve().parents[3] / ".gitignore"
        content = gi.read_text(encoding="utf-8")
        assert "**/keystroke_buffer.jsonl" in content, (
            "NB-12: .gitignore must include **/keystroke_buffer.jsonl."
        )
```

## Anti-regressão

- Static test acima em `.gitignore` roda em todo CI.
- Adicionar linha em `docs/CLAUDE.md` (se existir seção sobre publisher) — regra: qualquer novo arquivo com secrets deve entrar em `_NEVER_PUBLISH_FILENAMES` + `.gitignore`.
- Sanity após commit: `pytest -m "unit or contract" -k "scanner or publisher or gitignore" -v`.

## Commit

```
fix(security): NB-12 scanner varre keystroke_buffer + publisher exclui do repo

- recording_scanner.py: novo handler _handle_keystroke que alerta por fingerprint
- git_publisher.py: _NEVER_PUBLISH_FILENAMES bloqueia keystroke_buffer.jsonl
- .gitignore: **/keystroke_buffer.jsonl
- cli/app.py: alerta pré-publish quando campo password detectado

Contrato: massa de teste (incluindo senhas reais) preservada localmente.
Arquivo keystroke_buffer.jsonl nunca vai pro repo compartilhado.
```

---

# NB-08 — Remover botão minimizar [WAVE 2]

## Origem

Requisito UX: overlay tem `tf-btn-minimize` (`_` char) + `tf-restore-badge` redundantes com `tf-btn-stop` + drag.

## Confirmar

```bash
grep -n "tf-btn-minimize\|tf-restore-badge\|_toggleMinimizeOverlay" src/testforge/recorder/overlay_inject.js
```

## Fix

`src/testforge/recorder/overlay_inject.js`:

1. Remover linha ~1577 (declaração do botão minimize):
   ```
   '<button id="tf-btn-minimize" ...>_</button>',
   ```

2. Remover linha ~1604 (handler):
   ```
   document.getElementById('tf-btn-minimize').onclick = function() { _toggleMinimizeOverlay(); };
   ```

3. Remover função `_toggleMinimizeOverlay` inteira (grep para achar).

4. Remover qualquer criação/uso de `tf-restore-badge` (badge que aparece quando minimizado).

## Teste

`tests/unit/recorder/test_overlay_when_rendered_then_no_minimize_button.py`:

```python
import pathlib, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestOverlayWhenRenderedThenNoMinimizeButton:
    def test_minimize_button_removed(self, overlay_source):
        assert 'tf-btn-minimize' not in overlay_source, "NB-08: tf-btn-minimize must be removed."

    def test_restore_badge_removed(self, overlay_source):
        assert 'tf-restore-badge' not in overlay_source, "NB-08: tf-restore-badge must be removed."

    def test_toggle_minimize_function_removed(self, overlay_source):
        assert '_toggleMinimizeOverlay' not in overlay_source, "NB-08: _toggleMinimizeOverlay function must be removed."
```

## Anti-regressão

Static tests acima.

## Commit

```
fix(recorder): NB-08 remove tf-btn-minimize + tf-restore-badge + _toggleMinimizeOverlay
```

---

# NB-02 — <button> overlay sem type="button" [WAVE 2]

## Origem

`<button>` sem `type` HTML default para `type="submit"`. Overlay tem 4 botões (`tf-btn-pause`, `tf-btn-stop`, `tf-btn-assert`, `tf-btn-minimize` — este último removido no NB-08).

## Confirmar

```bash
grep -n '<button id="tf-btn' src/testforge/recorder/overlay_inject.js
```
Verificar que NENHUM tem `type="button"`.

## Fix

`src/testforge/recorder/overlay_inject.js`:

Para cada `<button id="tf-btn-*">` (linhas ~1569-1577), adicionar `type="button"`:

```js
'<button id="tf-btn-pause" type="button" style="..." title="Shift+P">||</button>',
'<button id="tf-btn-stop" type="button" style="..." title="Shift+S">[]</button>',
'<button id="tf-btn-assert" type="button" style="..." title="Shift+A">Assert</button>',
```

Também qualquer OUTRO `<button>` sem `type` no overlay JS (buscar todos).

## Teste

`tests/unit/recorder/test_overlay_buttons_when_declared_then_type_button.py`:

```python
import pathlib, re, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestOverlayButtonsWhenDeclaredThenTypeButton:
    def test_all_tf_btn_have_type_button(self, overlay_source):
        matches = list(re.finditer(r'<button id="(tf-btn-[a-z]+)"([^>]*)>', overlay_source))
        assert matches, "NB-02: no tf-btn-* buttons found in overlay source."
        missing = [m.group(1) for m in matches if 'type="button"' not in m.group(2)]
        assert not missing, f"NB-02: overlay buttons without type='button': {missing}"
```

## Anti-regressão

Static test acima roda em cada CI.

## Commit

```
fix(recorder): NB-02 add type="button" a todos <button> do overlay
```

---

# NB-01 — _pushEvent guard contra overlay elements [WAVE 2]

## Origem

69/117 events em `Acesso_Plataforma_DES_2/raw_events.jsonl` têm `element_id` começando com `tf-`. Filtro `_isOverlayElement` existe (linha 1207) mas não é aplicado consistentemente. Especificamente:

1. Handler de click (linha 1251) tem check inicial, mas **reatribui `el` via `.closest('button, ...')`** (linha 1275) sem re-check.
2. Handler de submit path (linha 1278) usa o `el` reatribuído sem re-check.
3. Delegate root listener (linha 2082) usa `el.id === "tf-panel"` em vez de `_isOverlayElement(el)` — falta filtrar `tf-btn-*`, `tf-status`, etc.

## Confirmar

```bash
python3 -c "
import json
events = [json.loads(l) for l in open('/tmp/pdes_extract/PLATAFORMA DES/Suite TEST/Caso Test 01/Acesso_Plataforma_DES_2/raw_events.jsonl') if l.strip()]
tf = sum(1 for e in events if ((e.get('target') or {}).get('element_id') or '').startswith('tf-'))
print(f'tf-* events: {tf}/{len(events)} ({100*tf/len(events):.0f}%)')
"
# Esperado: 69/117 (59%)
```

## Fix

`src/testforge/recorder/overlay_inject.js`:

### 1A — guard em `_pushEvent` (defense in depth)

Adicionar como PRIMEIRA linha da função (linha 541):

```js
function _pushEvent(type, el) {
  // NB-01: guard universal — nenhum caller pode emitir evento de overlay,
  // não importa por onde chegou aqui. Blocklist única para tf-* e __tf-*.
  if (_isOverlayElement(el)) return;
  // ... resto do código existente
```

### 1B — re-check no submit path

Após o `el = interactive;` (linha 1276), antes de `_isSubmitTrigger(el)` (linha 1278):

```js
if (el && el.closest) {
  var interactive = el.closest('button, a, input, ...');
  if (interactive) el = interactive;
}
// NB-01: el foi reatribuído — se agora é overlay button, abortar
if (_isOverlayElement(el)) return;
if (_isSubmitTrigger(el)) {
  // ...
```

### 1C — delegate root usa helper canônico

Linha 2082, trocar:
```js
if (el.id === "tf-panel" || (el.closest && el.closest("#tf-panel"))) return;
```
por:
```js
if (_isOverlayElement(el)) return;
```

## Teste

`tests/unit/recorder/test_overlay_events_when_tf_element_then_never_pushed.py`:

```python
import pathlib, re, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestOverlayEventsWhenTfElementThenNeverPushed:
    def test_push_event_first_line_guards_overlay(self, overlay_source):
        # _pushEvent's first non-comment line must check _isOverlayElement
        pattern = re.compile(
            r"function _pushEvent\(type, el\)\s*\{[\s\S]{0,300}?_isOverlayElement\(el\)",
        )
        assert pattern.search(overlay_source), (
            "NB-01: _pushEvent must guard _isOverlayElement(el) near function start."
        )

    def test_submit_trigger_rechecks_after_closest(self, overlay_source):
        # Between `interactive = el.closest(...)` and `_isSubmitTrigger(el)`,
        # there must be an _isOverlayElement re-check.
        pattern = re.compile(
            r"if \(interactive\) el = interactive;[\s\S]{0,150}?_isOverlayElement\(el\)[\s\S]{0,100}?_isSubmitTrigger",
        )
        assert pattern.search(overlay_source), (
            "NB-01: after reassigning el via closest(), must re-check overlay before _isSubmitTrigger."
        )

    def test_delegate_root_uses_canonical_helper(self, overlay_source):
        # Line 2082 substitution — must use _isOverlayElement not ad-hoc check
        assert 'el.id === "tf-panel"' not in overlay_source, (
            "NB-01: delegate root must use _isOverlayElement (canonical), not id === 'tf-panel' check."
        )
```

## Anti-regressão

- Static tests acima.
- **Regressão contract test** (adicionar em `tests/regression/recording/`):
  ```python
  # test_no_tf_leak_in_pdes_recordings.py
  # Reprocessa as 4 gravações PDes com o normalizer e assert zero tf-* em raw stream considered.
  ```
- Regra em `docs/CLAUDE.md`: qualquer novo `_pushEvent` deve ter `_isOverlayElement` guard como primeira linha.

## Commit

```
fix(recorder): NB-01 _pushEvent guard + submit path re-check + delegate root canonical
```

---

# NB-13 — Normalizer filtra overlay + carousel [WAVE 2]

## Origem

`execution_report.json` de Valida_zeros_a_esquerda mostra steps `#tf-btn-assert` e `#next` como test steps que falharam. Compiler propaga lixo do recorder.

## Confirmar

```bash
python3 -c "
import json
r = json.load(open('/tmp/pdes_extract/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda/_pilot_runs/Valida_zeros_a_esquerda/20260706-181613/execution_report.json'))
bad = [s for s in r.get('steps', []) if 'tf-btn' in str(s.get('selected_locator','')) or '#next' in str(s.get('selected_locator',''))]
print(f'steps referencing tf-btn or #next: {len(bad)}')
"
```

## Fix

`src/testforge/semantic/recording_normalizer.py`:

Localizar `_convert_event` (ou `_build_semantic_action`, `_process_raw_event`). Antes de converter em `SemanticAction`, adicionar filtro:

```python
# NB-13: skip overlay elements + known auto-fire (carousel etc). Estas amostras
# vazam quando handler de click do overlay não filtra ou quando página tem
# auto-play. Normalizer é a última linha de defesa antes do compiler.
_OVERLAY_ID_PREFIXES = ("tf-", "__tf-")
_AUTO_FIRE_CLASSES = frozenset({
    "carousel-control-next", "carousel-control-prev",
    "swiper-button-next", "swiper-button-prev",
    "slick-next", "slick-prev",
})

def _is_noise_event(event: dict) -> bool:
    target = event.get("target") or {}
    eid = (target.get("element_id") or "").strip()
    if any(eid.startswith(p) for p in _OVERLAY_ID_PREFIXES):
        return True
    class_list = target.get("class_list") or []
    if any(c in _AUTO_FIRE_CLASSES for c in class_list):
        return True
    return False
```

No loop principal do normalizer, filtrar:
```python
for event in raw_events:
    if _is_noise_event(event):
        continue  # NB-13
    # ... resto
```

## Teste

`tests/unit/normalizer/test_normalizer_when_overlay_or_carousel_then_skipped.py`:

```python
import pytest
from testforge.semantic.recording_normalizer import _is_noise_event


@pytest.mark.unit
class TestNormalizerWhenOverlayOrCarouselThenSkipped:
    def test_tf_btn_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "tf-btn-pause"}}
        assert _is_noise_event(event) is True

    def test_tf_panel_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "tf-panel"}}
        assert _is_noise_event(event) is True

    def test_double_underscore_tf_class_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "__tf-toast"}}
        assert _is_noise_event(event) is True

    def test_carousel_next_class_is_noise(self):
        event = {"type": "click", "target": {"element_id": "next", "class_list": ["carousel-control-next"]}}
        assert _is_noise_event(event) is True

    def test_swiper_next_is_noise(self):
        event = {"type": "click", "target": {"class_list": ["swiper-button-next"]}}
        assert _is_noise_event(event) is True

    def test_regular_button_is_not_noise(self):
        event = {"type": "click", "target": {"element_id": "submit-btn", "class_list": ["btn", "btn-primary"]}}
        assert _is_noise_event(event) is False
```

## Anti-regressão

Regression test que rodar normalize sobre `Acesso_Plataforma_DES_2/raw_events.jsonl` e verifica que `semantic_steps.jsonl` tem 0 events com `element_id` começando com `tf-` ou `carousel-control-*`.

## Commit

```
fix(normalizer): NB-13 skip overlay + carousel auto-fire events pré-compile
```

---

# NB-04 — Pause toggle visual [WAVE 2]

## Origem

6 events submit `tf-btn-pause` em `Acesso_Plataforma_DES_2` — todos com texto do overlay `'R Gravando... | ...'` no target snapshot. Label não muda quando pausado.

## Fix

`src/testforge/recorder/overlay_inject.js` linha 1601 (`onclick` do pause):

Trocar:
```js
document.getElementById('tf-btn-pause').onclick = function() {
  window.__tfCommandQueue.push('TOGGLE_PAUSE');
};
```

por:
```js
document.getElementById('tf-btn-pause').onclick = function() {
  window.__tfCommandQueue.push('TOGGLE_PAUSE');
  window.__tfPausedLocal = !window.__tfPausedLocal;
  var status = document.getElementById('tf-status');
  var dot = document.getElementById('tf-dot');
  if (window.__tfPausedLocal) {
    if (status) status.textContent = 'Pausado';
    if (dot) dot.style.color = '#f59e0b';
  } else {
    if (status) status.textContent = 'Gravando...';
    if (dot) dot.style.color = '#e94560';
  }
};
```

Inicializar `window.__tfPausedLocal = false` no bloco de state init (linhas 157-192).

## Teste

`tests/unit/recorder/test_pause_button_when_toggled_then_status_updates.py`:

```python
import pathlib, re, pytest

OVERLAY_JS = pathlib.Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "overlay_inject.js"

@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")

@pytest.mark.unit
class TestPauseButtonWhenToggledThenStatusUpdates:
    def test_pause_handler_sets_paused_text(self, overlay_source):
        pattern = re.compile(
            r"tf-btn-pause[\s\S]{0,400}?['\"]Pausado['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause handler must set 'Pausado' text."

    def test_pause_handler_reverts_gravando(self, overlay_source):
        pattern = re.compile(
            r"tf-btn-pause[\s\S]{0,600}?['\"]Gravando\.\.\.['\"]",
        )
        assert pattern.search(overlay_source), "NB-04: pause handler must revert to 'Gravando...' on toggle."

    def test_paused_local_state_initialized(self, overlay_source):
        assert "__tfPausedLocal" in overlay_source, "NB-04: __tfPausedLocal state var must be declared."
```

## Commit

```
fix(recorder): NB-04 pause button toggles visual status (Gravando/Pausado)
```

---

# NB-05 + NB-19 — Blocklist + heurística auto-fire carousel [WAVE 3]

## Origem

297 clicks em `#next.carousel-control-next` em `Teste_de_dados_coletados` — median gap 8.0s ± 3.76s = Bootstrap Carousel auto-play `data-interval="8000"`.

## Confirmar

```bash
python3 -c "
import json, datetime
events = [json.loads(l) for l in open('/tmp/pdes_extract/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda - 01/Teste_de_dados_coletados/raw_events.jsonl') if l.strip()]
next_clicks = [e for e in events if (e.get('target') or {}).get('element_id') == 'next']
ts = [datetime.datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')) for e in next_clicks]
gaps = [(ts[i+1]-ts[i]).total_seconds() for i in range(len(ts)-1)]
print(f'#next clicks: {len(next_clicks)}, median gap: {sorted(gaps)[len(gaps)//2]:.1f}s')
"
# Esperado: 297 clicks, median ~8s
```

## Fix

Duas frentes: blocklist estática + heurística runtime.

### 5A — Blocklist estática no recorder

`src/testforge/recorder/overlay_inject.js` — antes do handler de click (linha 1251), definir:

```js
// NB-05: elementos com auto-play conhecido (Bootstrap Carousel, Swiper, Slick etc).
// Se click vier de um destes, ignorar. Blocklist estática — heurística fica para NB-05B.
var _tfAutoFireBlocklist = {
  classPrefixes: ['carousel-control-', 'swiper-button-', 'slick-'],
  classExact: ['owl-next', 'owl-prev'],
};
function _isAutoFireElement(el) {
  if (!el || !el.classList) return false;
  for (var i = 0; i < el.classList.length; i++) {
    var c = el.classList[i];
    if (_tfAutoFireBlocklist.classExact.indexOf(c) !== -1) return true;
    for (var j = 0; j < _tfAutoFireBlocklist.classPrefixes.length; j++) {
      if (c.indexOf(_tfAutoFireBlocklist.classPrefixes[j]) === 0) return true;
    }
  }
  return false;
}
```

No handler de click, ANTES do `_isSubmitTrigger`:
```js
if (_isAutoFireElement(el)) return;
```

### 5B — Heurística runtime opcional

`src/testforge/semantic/recording_normalizer.py` — pós-conversion, rodar detector:

```python
def _detect_auto_fire_clusters(events: list[dict]) -> set[int]:
    """NB-05: detecta clusters de clicks no mesmo target com gap regular < 12s.
    Retorna set de índices a marcar como noise."""
    from datetime import datetime
    noise = set()
    # Agrupa por (element_id, css_path)
    from collections import defaultdict
    groups = defaultdict(list)
    for i, e in enumerate(events):
        if e.get("type") != "click":
            continue
        t = e.get("target") or {}
        key = (t.get("element_id",""), t.get("css_path",""))
        groups[key].append((i, e))
    for key, items in groups.items():
        if len(items) < 4:
            continue
        # gaps
        ts = [datetime.fromisoformat(e["timestamp"].replace("Z","+00:00")) for _, e in items]
        gaps = [(ts[i+1]-ts[i]).total_seconds() for i in range(len(ts)-1)]
        if not gaps:
            continue
        median = sorted(gaps)[len(gaps)//2]
        if 3.0 < median < 12.0:
            # Auto-play-like — mark all as noise
            for i, _ in items:
                noise.add(i)
    return noise
```

Aplicar antes de `_convert_event` loop.

## Teste

`tests/unit/normalizer/test_auto_fire_detector_when_regular_gaps_then_marked_noise.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.unit
class TestAutoFireDetectorWhenRegularGapsThenMarkedNoise:
    def _make_click(self, i, seconds_offset, eid, css=""):
        base = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
        ts = (base + timedelta(seconds=seconds_offset)).isoformat().replace("+00:00", "Z")
        return {"type": "click", "timestamp": ts, "target": {"element_id": eid, "css_path": css}}

    def test_5_clicks_8s_apart_marked_as_noise(self):
        from testforge.semantic.recording_normalizer import _detect_auto_fire_clusters
        events = [self._make_click(i, i*8, "next", "#next") for i in range(5)]
        noise = _detect_auto_fire_clusters(events)
        assert noise == {0, 1, 2, 3, 4}

    def test_3_clicks_1s_apart_not_marked(self):
        from testforge.semantic.recording_normalizer import _detect_auto_fire_clusters
        events = [self._make_click(i, i*1, "btn", "#btn") for i in range(3)]
        noise = _detect_auto_fire_clusters(events)
        assert not noise, "Human clicks should not be marked noise."

    def test_carousel_by_class_blocklist(self):
        # Sanity: 5B usa gap heurístico; blocklist estática (5A) é no JS/overlay
        pass
```

Static test para JS blocklist:

`tests/unit/recorder/test_overlay_when_carousel_click_then_blocked.py`:

```python
@pytest.mark.unit
class TestOverlayWhenCarouselClickThenBlocked:
    def test_autofire_blocklist_declared(self, overlay_source):
        assert "carousel-control-" in overlay_source, "NB-05: blocklist must include carousel-control-*"
        assert "_isAutoFireElement" in overlay_source, "NB-05: helper _isAutoFireElement must exist"

    def test_click_handler_calls_isAutoFire(self, overlay_source):
        import re
        pattern = re.compile(
            r"window\.addEventListener\(['\"]click['\"][\s\S]{0,300}?_isAutoFireElement",
        )
        assert pattern.search(overlay_source), "NB-05: click handler must call _isAutoFireElement"
```

## Anti-regressão

- Static tests + heuristic unit tests acima.
- Regression: rodar normalize em `Teste_de_dados_coletados/raw_events.jsonl` e assertar que `semantic_steps` tem 0 events em `#next.carousel-control-next`.

## Commit

```
feat(recorder): NB-05 blocklist auto-fire (carousel/swiper/slick/owl)
fix(normalizer): NB-05 heurística cluster clicks gap regular
```

---

# NB-09 + NB-10 — recordings_failed nested + Windows path guard [WAVE 3]

## Origem

**NB-09**: 4/4 gravações têm `recordings_failed/` DENTRO do próprio recording. Exemplo real:
```
/Valida_zeros_a_esquerda/recordings_failed/Valida_zeros_a_esquerda_20260706-181614/
```

**NB-10**: Todos 4 `FAILED_MARKER.json` têm `source_dir: "C:\\Users\\&lt;USUARIO&gt;\\AP\\..."`.  Fix RC-26 (BUG-REC-89) na Fase 9 já shipado mas gravação `Acesso_Plataforma_DES_2_20260707-203015` (POSTERIOR) ainda mostra o bug. Combinação com NB-09 é a causa: quando `_PROJECT_ROOT` mal-detectado, `relative_to` falha e retorna path original.

## Confirmar

```bash
find /tmp/pdes_extract -name "FAILED_MARKER.json" -exec python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(sys.argv[1].split('/')[-2], '→', d.get('source_dir'))
" {} \;
```

## Fix

`src/testforge/cli/app.py` — função `_mark_failed_recording` (linhas 317-343):

Adicionar guards:

```python
def _mark_failed_recording(rec_dir: str, rid: str, reason: str = "validation_failed") -> None:
    """Marca gravacao como falha em um diretorio dedicado sem mover artefatos originais."""
    try:
        # NB-09: guard contra _PROJECT_ROOT mal-detectado. Se rec_dir estiver
        # em ancestral de _PROJECT_ROOT, o failed_root vira nested inside rec_dir.
        project_root = _PROJECT_ROOT.resolve()
        rec_dir_resolved = pathlib.Path(rec_dir).resolve()
        if project_root == rec_dir_resolved or project_root in rec_dir_resolved.parents:
            # Case OK: project_root é ancestral ou igual a rec_dir
            pass
        else:
            # rec_dir NÃO está dentro do project_root — abortar com mensagem
            print(f"[TestForge] [ERRO] rec_dir '{rec_dir}' fora de _PROJECT_ROOT '{project_root}'."
                  f" Failed marker NÃO criado para evitar nested recordings_failed/.")
            return

        failed_root = project_root / "recordings_failed"
        # NB-09: bloqueio adicional — failed_root nunca pode ser subdir de rec_dir
        try:
            if failed_root.resolve().is_relative_to(rec_dir_resolved):
                print(f"[TestForge] [ERRO] recordings_failed/ resultaria nested dentro de {rec_dir}."
                      f" Abortando.")
                return
        except AttributeError:
            # is_relative_to é Python 3.9+; fallback
            try:
                failed_root.resolve().relative_to(rec_dir_resolved)
                print(f"[TestForge] [ERRO] recordings_failed/ nested em {rec_dir}. Abortando.")
                return
            except ValueError:
                pass  # OK — não é subdir

        failed_root.mkdir(parents=True, exist_ok=True)

        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = failed_root / f"{rid}_{stamp}"
        # ... existing copytree logic

        # NB-10: source_dir relativo E defense-in-depth contra Windows path
        try:
            rel_source = str(pathlib.Path(rec_dir).resolve().relative_to(project_root))
        except (ValueError, OSError):
            rel_source = pathlib.Path(rec_dir).name

        # NB-10: se ainda tiver Windows drive letter, forçar basename
        import re as _re_mod
        if _re_mod.match(r'^[A-Za-z]:', rel_source):
            rel_source = pathlib.Path(rel_source).name

        # NB-10: normalizar separador para POSIX (cross-platform)
        rel_source = rel_source.replace("\\", "/")

        marker = {
            "recording_id": rid,
            "reason": reason,
            "source_dir": rel_source,
            "failed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "superseded_by": None,
        }
        # ... rest
```

## Teste

`tests/unit/cli/test_mark_failed_when_rec_dir_outside_project_root_then_aborts.py`:

```python
import json, pathlib, pytest


@pytest.mark.unit
class TestMarkFailedWhenRecDirOutsideProjectRootThenAborts:
    def test_aborts_when_rec_dir_outside_project(self, tmp_path, monkeypatch, capsys):
        from testforge.cli import app
        pr = tmp_path / "project"
        pr.mkdir()
        rec_outside = tmp_path / "elsewhere" / "rec"
        rec_outside.mkdir(parents=True)
        monkeypatch.setattr(app, "_PROJECT_ROOT", pr)
        app._mark_failed_recording(str(rec_outside), "rec")
        assert not (pr / "recordings_failed").exists() or not any((pr / "recordings_failed").iterdir())
        out = capsys.readouterr().out
        assert "ERRO" in out or "fora de" in out.lower()


@pytest.mark.unit
class TestFailedMarkerWhenPathHasWindowsDriveThenStripped:
    def test_source_dir_without_windows_drive(self, tmp_path, monkeypatch):
        from testforge.cli import app
        pr = tmp_path / "project"
        pr.mkdir()
        rec = pr / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        monkeypatch.setattr(app, "_PROJECT_ROOT", pr)
        app._mark_failed_recording(str(rec), "my_rec")
        failed = list((pr / "recordings_failed").glob("my_rec_*"))
        assert failed, "Failed dir not created"
        marker = json.loads((failed[0] / "FAILED_MARKER.json").read_text())
        assert "C:" not in marker["source_dir"], f"Windows drive leaked: {marker['source_dir']}"
        assert "\\" not in marker["source_dir"], f"Backslash leaked: {marker['source_dir']}"


@pytest.mark.unit
class TestFailedMarkerWhenWouldNestThenAborts:
    def test_aborts_when_project_root_equals_rec_dir(self, tmp_path, monkeypatch, capsys):
        from testforge.cli import app
        rec = tmp_path / "rec"
        rec.mkdir()
        # _PROJECT_ROOT set to rec_dir → would create recordings_failed inside rec
        monkeypatch.setattr(app, "_PROJECT_ROOT", rec)
        (rec / "recording_metadata.json").write_text(json.dumps({}))
        (rec / "raw_events.jsonl").write_text("")
        app._mark_failed_recording(str(rec), "rec")
        # Se veio nested, teste falha — mas guard NB-09 deveria evitar
        nested = rec / "recordings_failed" / "rec"
        # Nested seria bug — assert que não veio
        # (implementação: guard aborta antes de criar)
        assert not any((rec / "recordings_failed").rglob("FAILED_MARKER.json")) or \
               any("ERRO" in l for l in capsys.readouterr().out.split("\n"))
```

## Anti-regressão

- Static/runtime tests acima.
- Adicionar regra em `docs/CLAUDE.md`: `_PROJECT_ROOT` NUNCA deve ser resolved dentro de recording_dir. Documentar detecção.

## Commit

```
fix(cli): NB-09 guard _mark_failed_recording contra nested recordings_failed
fix(cli): NB-10 strip Windows drive + backslash em FAILED_MARKER.source_dir
```

---

# NB-11 — dom_snapshot field posix slash [WAVE 3]

## Origem

`raw_events[].dom_snapshot: "dom_snapshots\\evt_00050.html"` — 41-320 events por gravação.

## Fix

`src/testforge/recorder/recorder_controller.py` — onde `dom_snapshot`/`ax_snapshot` field é populado no evento:

Buscar por atribuição do tipo `event["dom_snapshot"] = ...` ou `event.dom_snapshot = ...`. Trocar por:

```python
from pathlib import PurePosixPath
# ...
event["dom_snapshot"] = str(PurePosixPath("dom_snapshots") / f"evt_{eid:05d}.html")
event["ax_snapshot"] = str(PurePosixPath("ax_snapshots") / f"evt_{eid:05d}.json")
```

Alternativa: se overlay JS já popula esse field (em `_pushEvent`), fazer replace no writer:

```python
if "dom_snapshot" in event and event["dom_snapshot"]:
    event["dom_snapshot"] = event["dom_snapshot"].replace("\\", "/")
if "ax_snapshot" in event and event["ax_snapshot"]:
    event["ax_snapshot"] = event["ax_snapshot"].replace("\\", "/")
```

Verificar OS DOIS lados (Python + JS) para garantir consistência.

## Teste

`tests/unit/recorder/test_dom_snapshot_field_when_written_then_posix_slash.py`:

```python
import json, pathlib, pytest


@pytest.mark.unit
class TestDomSnapshotFieldWhenWrittenThenPosixSlash:
    def test_no_backslash_in_dom_snapshot_field(self, tmp_path):
        # Fabricar evento simulado como recorder_controller escreveria
        from testforge.recorder.recorder_controller import _serialize_event  # ou equivalente
        event = {"type": "click", "event_id": "evt_00001", "target": {}}
        # Chamar helper que popula dom_snapshot
        # ...
        # Assert
        assert "\\" not in event.get("dom_snapshot", "")
```

Adicionalmente: **static scan** dos raw_events das gravações PDes:
```python
def test_pdes_recordings_have_no_backslash_in_snapshot_fields(self):
    import glob
    for p in glob.glob("/tmp/pdes_extract/**/raw_events.jsonl", recursive=True):
        for line in open(p):
            if line.strip():
                e = json.loads(line)
                assert "\\" not in (e.get("dom_snapshot") or ""), f"Backslash in {p}"
```

## Commit

```
fix(recorder): NB-11 dom_snapshot/ax_snapshot posix slash em raw_events
```

---

# NB-03 — Step counter cross-origin [WAVE 3]

## Origem

`sessionStorage` isolado por origem. Nav de `sistema-des.example.com` → `auth-des.example.com` reseta counter no overlay.

## Fix

### 3A — overlay lê counter externo

`src/testforge/recorder/overlay_inject.js` linha 1535:

```js
initSteps = (window.__tfExternalStepCount != null)
  ? parseInt(window.__tfExternalStepCount)
  : parseInt(sessionStorage.getItem('__tfStepCount') || 0);
```

### 3B — Python injeta counter

`src/testforge/recorder/recorder_controller.py` — no método que faz `flush_events` (ou similar), após computar total:

```python
try:
    self._page.evaluate(f"window.__tfExternalStepCount = {step_count}")
except Exception:
    pass
```

## Teste

`tests/unit/recorder/test_step_counter_when_external_provided_then_prefers_it.py`:

```python
@pytest.mark.unit
class TestStepCounterWhenExternalProvidedThenPrefersIt:
    def test_overlay_reads_external_step_count(self, overlay_source):
        assert "__tfExternalStepCount" in overlay_source, "NB-03: overlay must reference __tfExternalStepCount"

    def test_recorder_injects_external_step_count(self):
        from pathlib import Path
        src = Path(__file__).resolve().parents[3] / "src" / "testforge" / "recorder" / "recorder_controller.py"
        content = src.read_text()
        assert "__tfExternalStepCount" in content, "NB-03: recorder must inject __tfExternalStepCount"
```

## Commit

```
fix(recorder): NB-03 external step count cross-origin (Python injeta, overlay lê)
```

---

# NB-14 — steps.jsonl.attrs proper serialization [WAVE 3]

## Origem

`steps.jsonl` de Valida_zeros_a_esquerda:
```json
{"step_id": "step_0001", "attrs": {"0": "ref: <Node>", "1": "ref: <Node>", ...}}
```
`attrs` deveria ter chaves como `id`, `class`, etc.

## Fix

`src/testforge/recorder/overlay_inject.js` — buscar por `_addStep` e onde `attrs` é populado (Shift+A flow). Provavelmente algo como:

```js
step.attrs = el.attributes;  // ❌ HTMLCollection não serializa direito
```

Trocar por:
```js
step.attrs = {};
if (el.attributes) {
  for (var _ai = 0; _ai < el.attributes.length; _ai++) {
    step.attrs[el.attributes[_ai].name] = el.attributes[_ai].value;
  }
}
```

Padrão usado em `_extractTarget` linhas ~363-368. Replicar.

## Teste

`tests/unit/recorder/test_step_attrs_when_extracted_then_key_value_pairs.py`:

```python
@pytest.mark.unit
class TestStepAttrsWhenExtractedThenKeyValuePairs:
    def test_ref_node_string_not_present_in_source(self, overlay_source):
        # Fonte não deve ter atribuição bruta el.attributes → step.attrs
        assert "step.attrs = el.attributes" not in overlay_source
        assert 'attrs = el.attributes;' not in overlay_source

    def test_attrs_populated_via_loop(self, overlay_source):
        import re
        pattern = re.compile(r"attrs\[.*attributes\[.*\]\.name\]\s*=\s*.*attributes\[.*\]\.value")
        assert pattern.search(overlay_source), "NB-14: attrs must be populated via .name/.value loop"
```

## Commit

```
fix(recorder): NB-14 step.attrs proper key/value serialization (not ref: <Node>)
```

---

# NB-15 — field_snapshots fingerprint anonymous inputs [WAVE 4]

## Origem

Teste_de_dados_coletados: 1251 batches com fp `input#[name=]` (inputs sem id/name). Diff-only (RC-16) deduped como se fossem o mesmo campo.

## Fix

`src/testforge/recorder/overlay_inject.js` — buscar `_snapshotFields` (linha ~539). Adicionar helper para fingerprint mais rico quando id/name vazios:

```js
function _fpForField(el, tag) {
  var id = el.id || '';
  var name = el.name || '';
  if (id || name) return tag + '#' + id + '[name=' + name + ']';
  // NB-15: fallback com css path posicional
  var css = '';
  try { css = _tfFinder(el, {seedMinLength: 3}) || ''; } catch(_e) {}
  return tag + '@' + css.substring(0, 100);
}
```

Substituir todo lugar em `_snapshotFields` que faz `tag + '#' + (el.id||'') + '[name=' + (el.name||'') + ']'` por `_fpForField(el, tag)`.

## Teste

`tests/unit/recorder/test_field_snapshot_when_anonymous_inputs_then_distinct_fp.py`:

```python
@pytest.mark.unit
class TestFieldSnapshotWhenAnonymousInputsThenDistinctFp:
    def test_helper_uses_css_path_fallback(self, overlay_source):
        assert "_fpForField" in overlay_source, "NB-15: helper _fpForField must exist"

    def test_anonymous_fingerprint_uses_at_delimiter(self, overlay_source):
        import re
        pattern = re.compile(r"tag\s*\+\s*['\"]@['\"]")
        assert pattern.search(overlay_source), "NB-15: anonymous fp uses '@' delimiter"
```

## Commit

```
fix(recorder): NB-15 fingerprint anonymous inputs via css_path fallback
```

---

# NB-16 — _pilot_tmp cleanup [WAVE 4]

## Origem

`_pilot_tmp/test_st-*.py` (15KB) sobra em todas gravações após pilot run.

## Fix

Buscar quem cria `_pilot_tmp/`:
```bash
grep -rn "_pilot_tmp" src/testforge/
```

Provavelmente em `src/testforge/runner/incremental_runner.py` ou `runner/pilot.py`. Envolver criação num try/finally:

```python
import tempfile, shutil
# ...
pilot_tmp_dir = os.path.join(rec_dir, "_pilot_tmp")
os.makedirs(pilot_tmp_dir, exist_ok=True)
try:
    # ... write and run test_st-*.py
finally:
    # NB-16: sempre limpar tmp de pilot para evitar bloat.
    shutil.rmtree(pilot_tmp_dir, ignore_errors=True)
```

## Teste

`tests/unit/runner/test_pilot_tmp_when_run_finishes_then_cleaned.py`:

```python
@pytest.mark.unit
class TestPilotTmpWhenRunFinishesThenCleaned:
    def test_pilot_tmp_removed_after_finalize(self, tmp_path):
        # Setup fake recording
        # Chamar helper que executa pilot smoke
        # Verificar que _pilot_tmp/ não existe
        ...
```

## Commit

```
fix(runner): NB-16 _pilot_tmp cleanup on finalize
```

---

# NB-17 — completeness lê metadata correto [WAVE 4]

## Origem

`intent_completeness_report.json.application: ""` e `base_url: ""` vazios. `recording_metadata.json` tem valores.

## Fix

Buscar quem escreve `intent_completeness_report.json`:
```bash
grep -rn "intent_completeness_report" src/testforge/
```

Verificar que ao gerar o report, o metadata é lido do path correto:
```python
meta_path = os.path.join(rec_dir, "recording_metadata.json")
with open(meta_path) as f:
    meta = json.load(f)
report["application"] = meta.get("application", "")
report["base_url"] = meta.get("base_url", "")
```

## Commit

```
fix(compiler): NB-17 completeness report reads metadata for app + base_url
```

---

# NB-06 — Assert timeout não conta como step [WAVE 4]

## Origem

Evento #48 em Acesso_Plataforma_DES_2: `type=assert target_id=None text='' value='visible'` — assert vazio, provavelmente cancelamento.

## Fix

`src/testforge/recorder/overlay_inject.js` — auditar todos os paths que atualizam `tf-step-count.textContent`. Cada atualização deve ocorrer APÓS `_pushEvent` bem-sucedido. Cancel/timeout do assert (Esc key, close menu) NÃO deve chamar `_pushEvent` nem incrementar counter.

Buscar:
```bash
grep -n "tf-step-count\|_showAssertMenu\|assertWaiting.*false" src/testforge/recorder/overlay_inject.js
```

Verificar caminhos de Esc, timeout de menu, close de menu — todos devem apenas resetar `__tfAssertWaiting = false` sem tocar counter.

## Teste

`tests/unit/recorder/test_assert_when_cancelled_then_no_step_increment.py`:

```python
@pytest.mark.unit
class TestAssertWhenCancelledThenNoStepIncrement:
    def test_esc_key_does_not_increment_counter(self, overlay_source):
        # No handler de Esc, não deve haver tf-step-count.textContent = ...
        import re
        # find Esc handler block
        esc_match = re.search(r"if\s*\(\s*e\.key\s*===\s*['\"]Escape['\"]\s*\)[\s\S]{0,500}", overlay_source)
        if esc_match:
            assert "tf-step-count.textContent" not in esc_match.group(0), \
                "NB-06: Esc handler must not increment step counter"
```

## Commit

```
fix(recorder): NB-06 assert cancel/timeout não incrementa step counter
```

---

# NB-24 — Dedup submits rapid-fire [WAVE 4]

## Origem

3 pares de submit events consecutivos < 1s no mesmo target em Acesso_Plataforma_DES_2.

## Fix

`src/testforge/recorder/overlay_inject.js` — no `_pushEvent` ou submit path, adicionar dedup window 500ms:

```js
window.__tfLastSubmitByKey = window.__tfLastSubmitByKey || {};
// dentro do submit path, antes de _pushEvent('submit', el):
var key = (el.id||'') + '|' + (el.tagName||'');
var now = Date.now();
if (window.__tfLastSubmitByKey[key] && (now - window.__tfLastSubmitByKey[key]) < 500) {
  return;  // NB-24: dedup rapid-fire submits
}
window.__tfLastSubmitByKey[key] = now;
```

## Teste

`tests/unit/recorder/test_submit_when_rapid_fire_then_deduplicated.py`:

```python
@pytest.mark.unit
class TestSubmitWhenRapidFireThenDeduplicated:
    def test_dedup_state_declared(self, overlay_source):
        assert "__tfLastSubmitByKey" in overlay_source, "NB-24: dedup state must be declared"

    def test_dedup_window_500ms(self, overlay_source):
        assert "500" in overlay_source, "NB-24: 500ms window used somewhere"
```

## Commit

```
fix(recorder): NB-24 dedup submit events rapid-fire (< 500ms same target)
```

---

# NB-07 — Auto-prune snapshots after passing run [WAVE 4]

## Origem

Snapshots ax/dom podem chegar a 1GB. Contrato: manter apenas quando run pós-gravação falhar.

## Fix

`src/testforge/cli/app.py` — adicionar novo CLI + hook post-run.

### 7A — CLI manual

```python
def _cmd_prune_snapshots(args) -> None:
    """NB-07: remove dom_snapshots/, ax_snapshots/ de uma gravação."""
    import shutil
    rec = pathlib.Path(args.recording_id)
    if not rec.is_absolute():
        rec = _PROJECT_ROOT / "recordings" / args.recording_id
    if not rec.exists():
        print(f"[TestForge] Recording not found: {rec}")
        return
    pruned = 0
    for name in ("dom_snapshots", "ax_snapshots"):
        d = rec / name
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            pruned += 1
    # Marker para auditoria
    meta_path = rec / "recording_metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["snapshots_pruned"] = True
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[TestForge] Pruned {pruned} snapshot dirs from {rec.name}")
```

Registrar: `sub.add_parser("prune-snapshots").add_argument("recording_id")`.

### 7B — Auto-prune após run pass

Onde run reporta verdict (buscar `verdict == "pass"` no CLI ou runner):

```python
# NB-07: se run passou, prune automaticamente (config-gated)
if verdict == "pass" and _load_config_defaults().get("prune", {}).get("auto_prune_on_run_pass", True):
    _cmd_prune_snapshots(argparse.Namespace(recording_id=rid))
```

## Teste

`tests/unit/cli/test_prune_snapshots_when_called_then_removes_dirs.py`:

```python
@pytest.mark.unit
class TestPruneSnapshotsWhenCalledThenRemovesDirs:
    def test_removes_dom_and_ax(self, tmp_path, monkeypatch):
        import argparse
        from testforge.cli import app
        monkeypatch.setattr(app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text("{}")
        (rec / "dom_snapshots").mkdir()
        (rec / "dom_snapshots" / "x.html").write_text("<html/>")
        (rec / "ax_snapshots").mkdir()
        app._cmd_prune_snapshots(argparse.Namespace(recording_id="my_rec"))
        assert not (rec / "dom_snapshots").exists()
        assert not (rec / "ax_snapshots").exists()

    def test_marker_added_to_metadata(self, tmp_path, monkeypatch):
        import argparse, json
        from testforge.cli import app
        monkeypatch.setattr(app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text("{}")
        app._cmd_prune_snapshots(argparse.Namespace(recording_id="my_rec"))
        meta = json.loads((rec / "recording_metadata.json").read_text())
        assert meta.get("snapshots_pruned") is True
```

## Commit

```
feat(cli): NB-07 prune-snapshots CLI + auto-prune on run pass
```

---

# NB-22, NB-18, NB-21 — Cosméticos [WAVE 4]

## NB-22 — testforge_version dinâmico

Buscar `"0.1.0"` hardcoded em publisher:
```bash
grep -rn '"0\.1\.0"\|0\.1\.0' src/testforge/publisher/
```

Substituir por leitura de `VERSION` file ou `importlib.metadata.version("testforge")`.

Teste: `tests/unit/publisher/test_submission_report_when_version_read_then_matches_metadata.py`.

## NB-18 — feature_path posix slash

`src/testforge/diagnostic/session.py` — onde `feature_path` é populado, usar `PurePosixPath` ou `.replace("\\", "/")`.

Teste: static que verifica que feature_path não contém `\\`.

## NB-21 — screenshots empty investigate

Investigar `recorder_controller.py` — feature de screenshot está ativa? Documentar. Se não implementada, remover dir do lifecycle.

Este é investigativo — pode virar bug separado depois. Baixa prioridade.

## Commits

```
fix(publisher): NB-22 testforge_version lido dinamicamente
fix(diagnostic): NB-18 feature_path posix slash
docs(recorder): NB-21 documentar/remover screenshots dir empty
```

---

# NB-23 — Métrica de validação final [WAVE 4]

## Origem

Valida_zeros_a_esquerda: 17s gravados → 39 test steps compilados. Ratio 6.5x = ruído.

## Fix

`src/testforge/validation/readiness_gate.py` — adicionar métrica ao report:

```python
def _compute_step_ratio(user_asserts: int, compiled_steps: int) -> tuple[float, str]:
    if user_asserts == 0:
        return (0.0, "no_asserts")
    ratio = compiled_steps / user_asserts
    if ratio > 3.0:
        return (ratio, "high_noise")
    return (ratio, "ok")
```

Adicionar warning ao readiness report quando ratio > 3.

## Teste

`tests/unit/validation/test_step_ratio_when_high_then_warns.py`.

## Commit

```
feat(validation): NB-23 ratio compiled_steps/user_asserts como métrica ruído
```

---

# Sanity gates finais

Após TODOS os 23 commits:

```bash
# 1. Sanity total
pytest -m "unit or contract or regression" -q
# Esperado: 400+ passed, 1 xfailed

# 2. Reprocess de PDes recordings
python3 -c "
import json, glob, subprocess
for rec in glob.glob('/tmp/pdes_extract/PLATAFORMA DES/**/raw_events.jsonl', recursive=True):
    d = '/'.join(rec.split('/')[:-1])
    events = [json.loads(l) for l in open(rec) if l.strip()]
    tf = sum(1 for e in events if ((e.get('target') or {}).get('element_id') or '').startswith('tf-'))
    # Depois de rodar compile atualizado, verificar semantic_steps.jsonl
    # tem 0 tf-* e 0 carousel-control-*
    print(d.split('/')[-1], 'tf-in-raw:', tf)
"

# 3. Verificar que keystroke_buffer não vaza
git check-ignore -v -- 'recordings/foo/keystroke_buffer.jsonl'
# Esperado: linha do .gitignore que ignora

# 4. Contract test das gravações PDes reprocessadas
pytest tests/regression/recording/ -v -k "pdes or nb"
```

---

## Handoff final

Após completar tudo:

1. Atualizar `docs/HANDOFF-NEXT-LLM.md` com resumo da wave.
2. Atualizar `docs/RECORDING-BUGS-NEW-BATCH-PDES.md` marcando cada NB como shipped.
3. Commit final: `docs(handoff): NB-01..24 shipados (23 commits, +N testes)`.

## Se algo bloquear

- **Contrato ambíguo**: pare e pergunte. Não improvise em contratos hard.
- **Fix quebra outro fix**: reverter último, replanejar.
- **Sanity gate quebra**: NÃO faça `--no-verify`. Investigue e corrija.
- **Fase 9 regride**: incidente. Reverter e reportar.
