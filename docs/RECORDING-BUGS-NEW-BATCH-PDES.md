# Novos bugs — Gravações PDes (2026-07-07)

**Origem**: `PDes.zip` — 4 recordings de `sistema-des.example.com`.  
**Nova gravação analisada**: `PLATAFORMA DES/Suite TEST/Caso Test 01/Acesso_Plataforma_DES_2` (2026-07-07T20:09).  
**Sanity após Fase 9**: **377 passed, 1 xfailed** (0 regressões nos testes automatizados; bugs abaixo são de comportamento não coberto pela suite).

---

## Prioridade (recalibrada após análise)

Ordem sugerida — critério: (a) severity + blast radius; (b) blocker para gravações confiáveis; (c) esforço.

### P0 — Blockers de gravação (contratos quebrados)

| ID | Bug | Sev | Regressão? |
|----|-----|-----|------------|
| **NB-01** | Overlay clicks vazam para `raw_events` (69/117 events = 59% lixo) | **crit** | **SIM** — `_isOverlayElement` existe mas não filtra `tf-btn-*`/`tf-panel` |
| **NB-02** | Botões `<button>` do overlay disparam `submit` events sem filtro | **crit** | SIM — click handler filtra target mas `_isSubmitTrigger` sobe pra ancestral overlay |
| **NB-03** | Contador de passos zera ao navegar entre subdomínios (`sistema-des.example.com` → `auth-des.example.com`) | **high** | SIM — `sessionStorage` por origem; state cross-origin perdido |
| **NB-04** | Botão pause não atualiza label (`Gravando...` continua igual quando pausado) | **high** | SIM — falta toggle visual em `_toggleMinimizeOverlay`/pause handler |

### P1 — Gravações imprevisíveis (auto-atividade da página)

| ID | Bug | Sev |
|----|-----|-----|
| **NB-05** | Carrossel de notícias no plataforma-des dispara `click` sozinho (auto-play) — captura como step do user | **high** |
| **NB-06** | Assert timeout (usuário desiste sem escolher elemento) contabiliza como step | med |

### P2 — Storage/lifecycle

| ID | Bug | Sev |
|----|-----|-----|
| **NB-07** | Snapshots ax/dom podem chegar a 1GB (largest single DOM: 2.8MB × N events); descartar de `recordings/` se run pós-gravação passar; manter só para failed | **high** |
| **NB-08** | Botão minimizar `_` no overlay é redundante — remover | low |

### P0 — Novos blockers (segunda passada, análise 4 gravações)

| ID | Bug | Sev | Regressão? |
|----|-----|-----|------------|
| **NB-09** | `recordings_failed/` **NESTED** dentro da própria gravação (4/4 recordings) | **crit** | SIM — `_PROJECT_ROOT` detection quebrada em subdirs |
| **NB-10** | `FAILED_MARKER.source_dir` continua com Windows abs path `C:\Users\&lt;USUARIO&gt;\...` (fix RC-26 regride pós-Fase 9) | **crit** | SIM — recording 2026-07-07T20:30 (pós fix) |
| **NB-11** | `raw_events[].dom_snapshot: "dom_snapshots\\evt_N.html"` — backslash literal em JSON (41-320 events/gravação) | high | SIM — RC-26 não cobriu serialização de raw events |
| **NB-12** | `keystroke_buffer.jsonl` não é scanned pelo PII detector + git publisher inclui no repo | **crit** | NÃO — massa mantida (contrato), mas alert + gitignore ausentes |

### P1 — Cascatas e regressões

| ID | Bug | Sev |
|----|-----|-----|
| **NB-13** | Compiler emite `#tf-btn-assert`, `#tf-panel`, `#next` como steps (30/39 falharam em Valida_zeros — cascata NB-01/05) | **crit** |
| **NB-14** | `steps.jsonl[].attrs = {"0":"ref: <Node>","1":"ref: <Node>",...}` — serialização quebrada de HTML attributes | high |
| **NB-15** | `field_snapshots` fingerprint colide para inputs anônimos — 1251 batches com fp `input#[name=]` iguais mas targets diferentes | high |
| **NB-19** | Teste_de_dados_coletados: 297 clicks em `#next.carousel-control-next` (gap 8s±3.76 → auto-play Bootstrap Carousel) | **crit** |
| ~~NB-20~~ | ~~dom_snapshot refs quebradas~~ — **user apagou manualmente antes do zip** (não é bug) | — |

### P2 — Ruído/UX/consistência

| ID | Bug | Sev |
|----|-----|-----|
| **NB-16** | `_pilot_tmp/test_st-*.py` leftover após pilot run (15KB por recording) | med |
| **NB-17** | `intent_completeness_report.json.application=""` e `.base_url=""` (vazios apesar de metadata ter valores) | med |
| **NB-18** | `diagnostic/session.json.feature_path: C:\Users\...` — Windows path leak | med |
| **NB-21** | `screenshots/` dir vazio (0 arquivos) em Acesso_2 apesar de artefato declarado | med |
| **NB-22** | `submission_report.testforge_version: 0.1.0` vs `metadata.fingerprint.testforge_version: 0.1.0` — hardcoded velho | low |
| **NB-23** | Valida_zeros_a_esquerda: 17s gravados → 39 test steps compilados (5.7 steps/s = ruído carousel) | high |
| **NB-24** | Submits duplicados back-to-back < 1s no mesmo target (3 casos em Acesso_2) — dedup ausente para submits | med |

---

## NB-01 — Overlay clicks vazam para raw_events (regressão)

### Onde veio o bug

**Recording**: `Acesso_Plataforma_DES_2` — 117 raw events, dos quais **69 (59%) têm `element_id` começando com `tf-`**:

```
click,tf-panel: 35
submit,tf-btn-assert: 12
submit,tf-btn-pause: 6
submit,tf-btn-minimize: 6
click,tf-restore-badge: 6
click,tf-status: 3
submit,tf-btn-stop: 1
```

### É bug de verdade?

**SIM — regressão crítica**. Evidência direta:

```bash
grep -c '"element_id":"tf-' "$D/raw_events.jsonl"    # 69
```

O código-fonte tem `_isOverlayElement(el)` em `src/testforge/recorder/overlay_inject.js:1207-1228` que checa `id.indexOf('tf-') === 0` e `.closest('[id^="tf-"]')`. O handler de click principal (linha 1254) chama esse filtro. **Mas os eventos continuam vazando** — sinal de que o filtro:
- (a) não é chamado no path de submit (linhas 1278-1290), OU
- (b) o `.closest('button, ...')` na linha 1275 reatribui `el` antes do `_pushEvent`, subindo até um botão overlay que passou pelo filtro inicial via `e.target` filho, OR
- (c) existe outro listener registrando clicks (delegate root em iframes/shadow, linha 2078) sem o mesmo filtro

### Como consertar

1. **Filtrar TUDO por id/class prefix em `_pushEvent` (defense in depth)**:
   ```js
   function _pushEvent(type, el) {
     // Guard: never emit overlay events, no matter how the caller got here.
     if (_isOverlayElement(el)) return;
     ...
   }
   ```
   Isso torna impossível emitir evento de overlay — qualquer bypass em call site é anulado.

2. **Filtrar `_isSubmitTrigger` também**: bloco `if (_isSubmitTrigger(el)) {` na linha 1278 deve verificar `_isOverlayElement(el)` novamente após o `.closest` da linha 1275 (o `el` foi reatribuído).

3. **Listener de delegate root (linha 2082)**: substituir `el.id === "tf-panel" || el.closest("#tf-panel")` por `_isOverlayElement(el)` (usar o helper canônico em vez de check ad-hoc).

### Testar

`tests/unit/recorder/test_overlay_events_when_tf_button_clicked_then_never_pushed.py`:
```python
@pytest.mark.unit
class TestOverlayEventsWhenTfButtonClickedThenNeverPushed:
    def test_push_event_guard_present(self, overlay_source):
        # _pushEvent MUST have _isOverlayElement guard as first statement
        import re
        pattern = re.compile(
            r"function _pushEvent\(type, el\)\s*\{[^}]{0,50}?_isOverlayElement",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "NB-01: _pushEvent must guard against overlay elements as first check."
        )

    def test_submit_trigger_re_checks_overlay(self, overlay_source):
        # After the .closest('button, ...') reassignment, check overlay again
        # before _pushEvent('submit', el).
        pattern = re.compile(
            r"if \(_isSubmitTrigger\(el\)\)\s*\{[^}]{0,200}?_isOverlayElement",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "NB-01: submit path must re-check overlay after ancestor reassignment."
        )

    def test_delegate_root_uses_canonical_helper(self, overlay_source):
        # Line 2082 substitution — use _isOverlayElement not id === "tf-panel"
        assert 'el.id === "tf-panel"' not in overlay_source, (
            "NB-01: delegate root must use _isOverlayElement (canonical helper)."
        )
```

### Impedir regressão

- **Contract test** em `tests/contract/`: rodar o overlay via `page.add_init_script`, disparar cliques nos botões `#tf-btn-*` via `page.click`, verificar que `window.__tfEventQueue` continua vazio.
- Regra em `docs/CLAUDE.md`: "qualquer `_pushEvent` novo DEVE ter `_isOverlayElement` guard como primeira linha".

---

## NB-02 — Botões overlay disparam submit events

### Onde veio o bug

Mesma gravação: 25 events do tipo `submit` com `element_id` = `tf-btn-*` (assert, pause, minimize, stop).

### É bug de verdade?

**SIM**. `<button>` em HTML sem `type` atributo default para `type="submit"`. Overlay declara botões assim:
```html
<button id="tf-btn-pause" style="..." title="Shift+P">||</button>
```
Sem `type="button"`. Se o botão estivesse dentro de `<form>` seria fatal (submitaria form real). Como está dentro de `<div>`, o `_isSubmitTrigger(el)` na linha 1278 ainda retorna `true` (linha 527: `if (tag === 'button' && (!el.type || el.type === 'submit')) return true;`).

### Como consertar

**Duplo fix**:

1. **Adicionar `type="button"` em todos os botões do overlay** (linha 1569-1577 e outros):
   ```js
   '<button id="tf-btn-pause" type="button" ...>||</button>',
   '<button id="tf-btn-stop" type="button" ...>[]</button>',
   '<button id="tf-btn-assert" type="button" ...>Assert</button>',
   '<button id="tf-btn-minimize" type="button" ...>_</button>',
   ```
   Impede que o browser trate como submit trigger.

2. Guard defensivo em `_pushEvent` (já em NB-01) previne mesmo assim.

### Testar

`tests/unit/recorder/test_overlay_buttons_when_declared_then_type_button.py`:
```python
@pytest.mark.unit
class TestOverlayButtonsWhenDeclaredThenTypeButton:
    def test_all_overlay_buttons_have_type_button(self, overlay_source):
        import re
        # find each <button id="tf-btn-*"> and check type="button"
        buttons = re.findall(r'<button id="(tf-btn-[a-z]+)"[^>]*>', overlay_source)
        assert buttons, "No tf-btn-* buttons found in overlay source."
        missing = []
        for match in re.finditer(r'<button id="(tf-btn-[a-z]+)"([^>]*)>', overlay_source):
            btn_id, attrs = match.group(1), match.group(2)
            if 'type="button"' not in attrs:
                missing.append(btn_id)
        assert not missing, f"NB-02: buttons without type='button': {missing}"
```

### Impedir regressão

- Static test acima. Runs em cada CI.

---

## NB-03 — Contador zera ao mudar de origem

### Onde veio o bug

Recording `Acesso_Plataforma_DES_2` navegou entre:
- `https://sistema-des.example.com/` (origem A)
- `https://auth-des.example.com/auth/...` (origem B — subdomain diferente)
- volta pra `sistema-des.example.com/` (origem A)

O contador no overlay text mostrou "Passos: 30" chegando até "Passos: 55" nos 35 clicks em `tf-panel` — mas isso porque estava no mesmo domínio. **A regressão relatada pelo user acontece na transição cross-origin**.

### É bug de verdade?

**SIM** — comportamento por design do browser. `sessionStorage` é isolado por origem. `overlay_inject.js:1535` faz:
```js
initSteps = parseInt(sessionStorage.getItem('__tfStepCount') || 0);
```
Ao navegar de `sistema-des.example.com` para `auth-des.example.com`, o `sessionStorage` do primeiro NÃO está disponível no segundo. Voltando, se sessionStorage foi limpo (SPA fresh boot), zera.

### Como consertar

Duas opções:

**Opção A (canônica)**: guardar o counter em `window.name` (persiste cross-origin no mesmo tab), OU em URL fragment injectado, OU em Playwright storage do lado Python (RecorderController) que reinjeta via `page.evaluate` a cada navegação.

**Opção B (pragmática)**: contar do lado Python (`__tfEventQueue` já é lido pelo controller). Overlay exibe o count vindo do Python via `window.__tfRecordingInfo.stepCount` atualizado em cada `flush_events`.

Recomendo B: elimina a dependência de sessionStorage. `RecorderController` já mantém contagem accurate; passar de volta pro overlay via `page.evaluate("window.__tfExternalStepCount = %d" % count)`.

Em `overlay_inject.js:1535`:
```js
// NB-03: prefer external count from Python (survives cross-origin navigation).
initSteps = (window.__tfExternalStepCount != null)
  ? parseInt(window.__tfExternalStepCount)
  : parseInt(sessionStorage.getItem('__tfStepCount') || 0);
```

Em `RecorderController.flush_events()` (Python), após contar, injetar:
```python
try:
    self._page.evaluate(f"window.__tfExternalStepCount = {step_count}")
except Exception:
    pass
```

### Testar

`tests/unit/recorder/test_step_counter_when_cross_origin_then_survives.py`:
```python
@pytest.mark.unit
class TestStepCounterWhenCrossOriginThenSurvives:
    def test_overlay_reads_external_count(self, overlay_source):
        assert "__tfExternalStepCount" in overlay_source, (
            "NB-03: overlay must prefer external count over sessionStorage."
        )

    def test_recorder_injects_external_count(self):
        # Verifica no recorder_controller.py que window.__tfExternalStepCount é injetado
        from pathlib import Path
        src = Path("src/testforge/recorder/recorder_controller.py").read_text()
        assert "__tfExternalStepCount" in src, (
            "NB-03: RecorderController must inject step count into page."
        )
```

### Impedir regressão

- Teste integração (`tests/integration/recorder/`) com dois `page.goto` para origens diferentes; validar que `window.__tfEventCounter` (contagem Python) continua monotônica.

---

## NB-04 — Pause não atualiza label do overlay

### Onde veio o bug

Todos os 6 `submit` events em `tf-btn-pause` mostram `text: 'R Gravando... | ...'` no target snapshot. Mesmo após clicar pause, o texto continua "Gravando...".

### É bug de verdade?

**SIM**. `overlay_inject.js:1601`:
```js
document.getElementById('tf-btn-pause').onclick = function() { window.__tfCommandQueue.push('TOGGLE_PAUSE'); };
```
Só empilha comando na fila para o Python processar. Não atualiza o label localmente. Do lado Python, o handler de `TOGGLE_PAUSE` altera o estado interno mas parece não notificar o overlay via `page.evaluate` para trocar o status text.

### Como consertar

Em `overlay_inject.js` no handler pause:
```js
document.getElementById('tf-btn-pause').onclick = function() {
  window.__tfCommandQueue.push('TOGGLE_PAUSE');
  window.__tfPausedLocal = !window.__tfPausedLocal;
  var status = document.getElementById('tf-status');
  var dot = document.getElementById('tf-dot');
  if (window.__tfPausedLocal) {
    if (status) status.textContent = 'Pausado';
    if (dot) dot.style.color = '#f59e0b';   // amber
  } else {
    if (status) status.textContent = 'Gravando...';
    if (dot) dot.style.color = '#e94560';   // red
  }
};
```

O Python continua sendo a fonte de verdade; o overlay dá feedback visual imediato. Se pause falhar no lado Python, próximo `page.evaluate` pode sincronizar.

### Testar

`tests/unit/recorder/test_pause_button_when_toggled_then_status_updates.py`:
```python
@pytest.mark.unit
class TestPauseButtonWhenToggledThenStatusUpdates:
    def test_pause_handler_updates_status_text(self, overlay_source):
        import re
        pattern = re.compile(
            r"tf-btn-pause.*?onclick.*?status.*?textContent\s*=\s*['\"]Pausado['\"]",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "NB-04: pause handler must set status text to 'Pausado'."
        )

    def test_resume_reverts_to_recording(self, overlay_source):
        import re
        pattern = re.compile(
            r"tf-btn-pause.*?['\"]Gravando\.\.\.['\"]",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "NB-04: pause handler must revert to 'Gravando...' on second click."
        )
```

### Impedir regressão

- Static test acima. E documentar no `overlay_inject.js` que estado visual deve espelhar `__tfPausedLocal`.

---

## NB-05 — Carrossel de notícias auto-fire clicks

### Onde veio o bug

`Acesso_Plataforma_DES_2` tem 4 clicks em `carousel-control-next` (classes `carousel-control-next`, text "Next") — o carrossel Bootstrap do plataforma-des tem `data-ride="carousel"` que dispara `.next()` a cada 5s.

### É bug de verdade?

**SIM — mas ambíguo**. Bootstrap Carousel dispara `click` sintético via `HTMLElement.dispatchEvent` interno? Não — ele chama `.carousel('next')` que altera DOM sem gerar click. Então esses 4 clicks parecem ser do **próprio usuário** clicando pra ver próxima notícia. Difícil desambiguar sem interação humana.

Verificação: gaps entre os 4 clicks — se forem exatamente 5000ms, é auto-play. Se irregulares (0.8s, 12s, 3s), é usuário.

```python
import json, datetime
D = "PDes/.../Acesso_Plataforma_DES_2"
events = [json.loads(l) for l in open(f'{D}/raw_events.jsonl') if l.strip()]
carousel = [e for e in events if 'carousel-control-next' in ((e.get('target') or {}).get('class_list') or [''])[0]]
ts = [datetime.datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')) for e in carousel]
print([(ts[i+1]-ts[i]).total_seconds() for i in range(len(ts)-1)])
```

### Como consertar

Duas frentes:

1. **Detector heurístico**: se 3+ clicks consecutivos no mesmo `element_id`/`class_list` com gap ≤10s e sem outro evento entre eles, marcar como `auto_activity_suspect=True`.

2. **Blocklist configurável**: `.testforge/blocklist.yaml` — patterns de classes/ids conhecidos por auto-fire (`carousel-control-*`, `swiper-button-next`, `slick-next`, etc). Overlay filtra no click handler.

Blocklist é mais defensiva. Heurística é mais universal. Recomendo **ambas** (blocklist para casos conhecidos + heurística para novos padrões — log warning).

### Testar

`tests/unit/recorder/test_carousel_when_auto_click_then_filtered.py` + fixture com blocklist yaml.

### Impedir regressão

- Blocklist versionada. Adicionar `carousel-control-next/prev` ao default.

---

## NB-06 — Assert timeout como step

### Onde veio o bug

Usuário aperta Shift+A, aparece overlay de assert, mas hesita/desiste. Se timeout dispara, o cancelamento vira step contabilizado.

### É bug de verdade?

**Confirmar via reprodução** — assert events da gravação são todos com target válido. Não vi timeout puro. Precisa reproduzir cenário para catalogar exatamente. Mas o bug é plausível — `_showAssertMenu` na linha 1271 pode ter timeout que emite step no clear.

### Como consertar

Auditar todos os paths em `overlay_inject.js` que atualizam contador em `tf-step-count` — garantir que só rodam em `_pushEvent('click'|'fill'|'submit'|'assert')` completo, nunca em cancelamentos.

### Testar

`tests/unit/recorder/test_assert_timeout_when_no_target_then_no_step.py`.

### Impedir regressão

- Auditoria estática: `grep -n "tf-step-count.*textContent" overlay_inject.js` — todos devem estar após `_pushEvent` bem-sucedido.

---

## NB-07 — Snapshots até 1GB; descartar de gravações OK

### Onde veio o bug

`Acesso_Plataforma_DES_2` tem 1.6MB de dom_snapshots + 540KB ax_snapshots (117 events × ~15KB avg). Em app pesado (SPA Angular), single DOM snapshot pode chegar a 2.8MB. Recordings de sessões longas chegam a 1GB.

**User contract**: manter apenas se `testforge run <recording>` FALHAR pós-gravação (debug útil). Se passar/skipar, deletar.

### É bug de verdade?

**SIM** — decisão de policy. Storage cresce indefinidamente. Git push transfere gigabytes.

### Como consertar

**Pipeline nova**: após gravação, executar pós-check automatizado:

1. `testforge compile <rec>` — se falhar, MANTER snapshots.
2. `testforge run <rec>` (headless smoke) — se todos steps `passed`/`healed`, DELETAR `dom_snapshots/` + `ax_snapshots/` do recording (mas manter `raw_events`, `steps.jsonl`, `recording_metadata.json`, `screenshots` — pequenos).
3. Marker: adicionar `snapshots_pruned: true` ao `recording_metadata.json` para auditoria.

CLI: `testforge prune-snapshots <rec>` — trigger manual.

Novo lifecycle:
```
record → compile OK → run OK → prune-snapshots → git commit small
       → compile FAIL ou run FAIL → keep everything → debug → fix → prune
```

Config em `.testforge/config.yml`:
```yaml
prune:
  auto_prune_on_run_pass: true       # default true
  keep_screenshots: true             # small, useful for reports
  keep_final_state: true             # tiny (single JSON)
  size_threshold_mb: 50              # if recording > 50MB, warn
```

### Testar

`tests/unit/cli/test_prune_snapshots_when_run_passes_then_removes.py`:
```python
@pytest.mark.unit
class TestPruneSnapshotsWhenRunPassesThenRemoves:
    def test_prune_removes_dom_and_ax(self, tmp_path):
        # Setup fake recording with dom_snapshots + ax_snapshots
        # Simulate run pass verdict
        # Call prune helper
        # Assert dom_snapshots/ and ax_snapshots/ removed
        # Assert raw_events.jsonl and metadata preserved
        ...

    def test_prune_kept_when_run_fails(self, tmp_path):
        # Same setup, simulate run FAIL verdict
        # Assert snapshots remain intact
        ...

    def test_metadata_marks_pruned_true(self, tmp_path):
        ...
```

### Impedir regressão

- CI job dedicado que grava recording de teste, executa run pass, chama prune, verifica size < 100KB.
- Documento `docs/STORAGE-POLICY.md` explicando o contrato.

---

## NB-08 — Remover botão minimizar

### Onde veio o bug

Requisito do usuário: overlay tem `tf-btn-minimize` (`_` char) que é redundante. Interface fica poluída.

### É bug de verdade?

**Feature request confirmado**. Overlay já tem `tf-btn-stop` (parar) e drag. Minimize sobrepõe.

### Como consertar

Remover em `overlay_inject.js`:
- Linha 1577: `<button id="tf-btn-minimize" ...>_</button>` — deletar.
- Linha 1604: `document.getElementById('tf-btn-minimize').onclick = ...` — deletar.
- Função `_toggleMinimizeOverlay` — deletar se só usada aqui.
- Elemento `tf-restore-badge` — deletar (só existe para restaurar minimizado).

### Testar

`tests/unit/recorder/test_overlay_when_rendered_then_no_minimize_button.py`:
```python
@pytest.mark.unit
class TestOverlayWhenRenderedThenNoMinimizeButton:
    def test_minimize_button_removed(self, overlay_source):
        assert 'tf-btn-minimize' not in overlay_source, (
            "NB-08: minimize button must be removed from overlay."
        )
        assert 'tf-restore-badge' not in overlay_source, (
            "NB-08: restore badge (companion to minimize) also removed."
        )
```

### Impedir regressão

- Static test acima.

---

## Ordem de commits sugerida

```
1. fix(recorder): NB-08 remove tf-btn-minimize + tf-restore-badge from overlay
2. fix(recorder): NB-02 add type="button" to all overlay <button> elements
3. fix(recorder): NB-01 guard _pushEvent + submit path with _isOverlayElement
4. fix(recorder): NB-01 delegate root uses canonical _isOverlayElement helper
5. fix(recorder): NB-04 pause button toggles local status text (Gravando/Pausado)
6. fix(recorder): NB-03 external step count from Python survives cross-origin nav
7. fix(recorder): NB-06 audit _pushEvent counter update paths (assert timeout no-op)
8. feat(recorder): NB-05 blocklist + heuristic for auto-fire carousel elements
9. feat(cli): NB-07 prune-snapshots command + auto-prune on run pass
```

Ordem por: (a) fixes triviais primeiro (NB-08, NB-02) para reduzir volume de eventos gerados; (b) filtro overlay (NB-01); (c) counter cross-origin (NB-03); (d) UX pause (NB-04); (e) heurística/blocklist (NB-05, NB-06); (f) storage policy (NB-07).

---

## Sanity gates

Antes de cada commit:
```bash
pytest -m "unit or contract or regression" -q
```
Base: **377 passed, 1 xfailed**.

Após todos os fixes NB-01 a NB-08:
```bash
# Regravar Acesso_Plataforma_DES novamente e checar:
python3 -c "
import json
events = [json.loads(l) for l in open('.../Acesso_Plataforma_DES_novo/raw_events.jsonl') if l.strip()]
tf = sum(1 for e in events if (e.get('target') or {}).get('element_id','').startswith('tf-'))
print(f'tf-* leaks: {tf}/{len(events)}')
assert tf == 0, 'NB-01/NB-02 fix incomplete'
"
```

---

## Contratos hard (não quebrar)

- `[[feedback-no-regrave]]` — cross-check com PDes recordings; se possível reprocessar via `compile+run` sem regravar.
- `[[feedback-no-regression]]` — todos os NB-* têm testes estáticos + integração.
- `[[feedback-pii-alert-only]]` — dados de teste NÃO mascarados, mas NB-12 é password (secret) — diferente, precisa masking.

---

## Segunda passada — NB-09 a NB-24 detalhados

### NB-09 — recordings_failed/ NESTED dentro da gravação

**Origem**: TODAS as 4 gravações do PDes.zip têm pasta `recordings_failed/` DENTRO do próprio recording:
```
/Valida_zeros_a_esquerda/recordings_failed/Valida_zeros_a_esquerda_20260706-181614/
/Teste_de_dados_coletados/recordings_failed/Teste_de_dados_coletados_20260707-134939/
/Acesso_Plataforma_DES/recordings_failed/Acesso_Plataforma_DES_20260707-200524/
/Acesso_Plataforma_DES_2/recordings_failed/Acesso_Plataforma_DES_2_20260707-203015/
```

**É bug real?** SIM. `_mark_failed_recording` em `cli/app.py:317` usa `_PROJECT_ROOT / "recordings_failed"`. Se `_PROJECT_ROOT` resolve pro próprio recording dir (mal-detecção do root), a pasta failed vira nested. Confirmação: `Acesso_Plataforma_DES_2_20260707-203015` = data pós-Fase 9 shipada hoje.

**Fix**: audit `_PROJECT_ROOT` initialization. Adicionar guard: `if _PROJECT_ROOT.is_relative_to(recording_dir): raise ValueError`. Ou usar env var explícita `TESTFORGE_PROJECT_ROOT`.

**Teste**: `tests/unit/cli/test_mark_failed_when_project_root_ambiguous_then_raises.py` — simula rec_dir em nested location e verifica que failed_root não é subdir do rec_dir.

**Anti-regressão**: adicionar assertion runtime: `assert not target.is_relative_to(Path(rec_dir))`.

---

### NB-10 — FAILED_MARKER Windows absolute path (regressão RC-26)

**Origem**: 4/4 FAILED_MARKER.json têm:
```json
"source_dir": "C:\\Users\\&lt;USUARIO&gt;\\AP\\AUTOMATA-PRIMUS\\recordings\\..."
```
Fix RC-26 (BUG-REC-89) já foi shipado — código atual em `cli/app.py:329-333`:
```python
try:
    rel_source = str(pathlib.Path(rec_dir).resolve().relative_to(_PROJECT_ROOT.resolve()))
except (ValueError, OSError):
    rel_source = pathlib.Path(rec_dir).name
```

**É bug real?** SIM. `Acesso_Plataforma_DES_2` data 2026-07-07T20:30 — POSTERIOR ao ship do fix (mesmo dia mais cedo). Recording foi feito com binary/versão antiga OR NB-09 é a causa (se `_PROJECT_ROOT` = próprio dir, `relative_to` retorna `.` e vira `pathlib.Path(rec_dir).name` OK — mas se `_PROJECT_ROOT.resolve()` falha antes, ValueError → catch → `.name`. O bug é que ExcpetionsPath falhou mais cedo, ou o binary do user está desatualizado).

**Fix**: mesma raiz do NB-09. Adicionalmente: `rel_source` NUNCA deve começar com letra + `:` (Windows drive). Guard:
```python
if re.match(r'^[A-Z]:', rel_source):
    rel_source = pathlib.Path(rel_source).name
```

**Teste**: `tests/unit/cli/test_failed_marker_when_windows_path_then_stripped.py`.

**Anti-regressão**: contract test que injeta path `C:\fake\path` no `rec_dir` (via mock) e verifica que marker escrito não contém `C:`.

---

### NB-11 — dom_snapshot field com backslash Windows

**Origem**: `raw_events[].dom_snapshot` de todas 4 gravações tem valores:
```json
"dom_snapshot": "dom_snapshots\\evt_00050.html"
"ax_snapshot": "ax_snapshots\\evt_00050.json"
```
41 a 320 events por gravação com esse padrão.

**É bug real?** SIM. RC-26 fix cobriu FAILED_MARKER.source_dir mas NÃO cobriu o serializador de raw_events. O overlay JS emite paths sem separator explícito; recorder_controller.py (Python) usa `os.path.join` que no Windows gera `\`.

**Fix em `src/testforge/recorder/recorder_controller.py`**: sempre serializar via `pathlib.PurePosixPath`:
```python
event["dom_snapshot"] = str(pathlib.PurePosixPath("dom_snapshots") / f"evt_{eid:05d}.html")
```
Ou `.replace('\\', '/')` no ponto de serialização.

**Teste**: `tests/unit/recorder/test_dom_snapshot_field_when_serialized_then_posix_slash.py`.

**Anti-regressão**: static test buscando `\\\\` em qualquer JSON escrito em `recordings/`.

---

### NB-12 — keystroke_buffer não é scanned pelo PII detector [alerta ausente]

**Contrato revisado**: `[[feedback-pii-alert-only]]` — password/PII fazem parte da massa de teste, **NÃO mascarar**. TestForge só ALERTA. O que NÃO pode acontecer é dados sensíveis serem commitados no git.

**Origem**: `keystroke_buffer.jsonl` de Valida_zeros_a_esquerda contém `input#password[name=password]` com &lt;SENHA&gt; tecla por tecla. Value é dado de teste (esperado). Bug real é **duplo**:

1. **`recording_scanner.py` não varre `keystroke_buffer.jsonl`** — só cobre raw_events, steps, value_mutations, field_snapshots, etc. Portanto o alerta PII não dispara para senhas capturadas por keystroke.
2. **Git publisher faz `git add -f`** em `recordings/<id>/` — se `keystroke_buffer.jsonl` for incluído, senha vai pro repo.

**É bug real?** SIM em 2 lados:
- Falta cobertura no scanner (senha real digitada não gera alerta).
- Falta git-guard: publisher deveria excluir `keystroke_buffer.jsonl` do subset publicado (mesmo sendo dado de teste, senhas não devem ir pro repo compartilhado).

**Fix em `src/testforge/security/recording_scanner.py`**: adicionar handler:
```python
# NB-12: cobrir keystroke_buffer.jsonl — reconstruir valor por fingerprint
# e passar pelo detector normal. Password field (fingerprint contendo 'password')
# recebe severidade CRITICAL automaticamente.
def _handle_keystroke(entry: dict, report: ScanReport, line_num: int) -> None:
    fp = entry.get("fingerprint", "")
    key = entry.get("key", "")
    kind = entry.get("kind", "")
    if kind != "char" or len(key) != 1:
        return
    md = {"fingerprint": fp, "type": "password" if "password" in fp.lower() else "text"}
    hits = detect(key, source=f"keystroke_buffer:{fp}", metadata=md)
    for h in hits:
        report.hits_by_source.setdefault(f"keystroke_buffer:{fp}", []).append(h)

_scan_jsonl_lines(
    rec_path / "keystroke_buffer.jsonl",
    report,
    source_prefix="keystroke_buffer",
    handler=_handle_keystroke,
)
```

**Fix em `src/testforge/publisher/git_publisher.py`** (`_copy_artifacts`): adicionar `keystroke_buffer.jsonl` a blocklist de arquivos NÃO copiados para git-tracked snapshot:
```python
# NB-12: keystroke_buffer.jsonl contém teclas por teclas incluindo senhas em
# plaintext. Value semântico já está em raw_events/value_mutations. Não replicar
# para o repo compartilhado — mantém local para debug apenas.
_NEVER_PUBLISH = {"keystroke_buffer.jsonl"}
```
No loop de cópia, `if filename in _NEVER_PUBLISH: continue`.

**Fix em `.gitignore` (root)**: adicionar:
```
# NB-12: keystroke buffer nunca vai pro repo (contém secrets em plaintext)
**/keystroke_buffer.jsonl
```

**Teste 1** — scanner cobre keystroke:
```python
tests/unit/security/test_scanner_when_keystroke_buffer_password_then_alerts.py
```

**Teste 2** — publisher não copia keystroke_buffer:
```python
tests/unit/publisher/test_publisher_when_keystroke_buffer_present_then_excluded.py
```

**Anti-regressão**:
- `.gitignore` static test — verificar linha `**/keystroke_buffer.jsonl` presente.
- Pre-commit hook opcional: `git diff --cached --name-only | grep keystroke_buffer && exit 1`.
- Documentar em `docs/SECURITY.md` (criar) o contrato: massa mantida, keystroke NUNCA no repo.

---

### NB-13 — Compiler emite `#tf-btn-*` e `#next` como test steps

**Origem**: `execution_report.json` de Valida_zeros_a_esquerda mostra:
```
step_num=11 action=click err=Elemento '#tf-btn-assert' nao encontrado
step_num=13 action=click err=Elemento '#next' nao encontrado
step_num=14 action=click err=Elemento '#tf-btn-assert' nao encontrado
```
30/39 steps failed/skipped.

**É bug real?** SIM — cascata direta de NB-01 (overlay leak) + NB-05 (carousel auto-fire). O compiler processa TODOS os raw_events sem filtro overlay/blocklist.

**Fix em `src/testforge/semantic/recording_normalizer.py`**: adicionar predicate no `_convert_event`:
```python
def _is_noise_event(event) -> bool:
    """NB-13: skip overlay + known auto-fire elements in normalizer."""
    target = event.get("target") or {}
    eid = (target.get("element_id") or "").strip()
    classes = " ".join(target.get("class_list") or [])
    if eid.startswith("tf-") or eid == "__tf":
        return True
    # Bootstrap Carousel + common auto-play patterns
    AUTO_FIRE_CLASSES = ["carousel-control-next", "carousel-control-prev",
                        "swiper-button-next", "swiper-button-prev",
                        "slick-next", "slick-prev"]
    if any(c in classes for c in AUTO_FIRE_CLASSES):
        return True
    return False
```

**Teste**: `tests/unit/normalizer/test_normalizer_when_overlay_or_carousel_event_then_skipped.py`.

**Anti-regressão**: rodar compiler sobre `Acesso_Plataforma_DES_2/raw_events.jsonl` e assertar que `#tf-*` e `#next` NÃO aparecem em `semantic_steps.jsonl`.

---

### NB-14 — steps.jsonl.attrs serialização quebrada

**Origem**: `steps.jsonl` em Valida_zeros:
```json
{"step_id": "step_0001", "attrs": {"0": "ref: <Node>", "1": "ref: <Node>", "2": "ref: <Node>", "3": "ref: <Node>"}}
```
`attrs` deveria conter atributos HTML (`{"id": "...", "class": "..."}`). Recebeu **enumeração de childNodes serializados como string `"ref: <Node>"`**.

**É bug real?** SIM. Overlay JS ou recorder_controller está fazendo `Object.entries(el.attributes)` errado — pegando NodeList/HTMLCollection cujos itens não têm `toJSON`. `JSON.stringify` converte para `"ref: <Node>"` (browser quirk).

**Fix em `src/testforge/recorder/overlay_inject.js`**: no _addStep para asserts, extrair attrs corretamente:
```js
var attrs = {};
if (el.attributes) {
  for (var i = 0; i < el.attributes.length; i++) {
    attrs[el.attributes[i].name] = el.attributes[i].value;
  }
}
```
(Já usado em `_extractTarget` linhas 363-368 — replicar padrão em callers de `_addStep`.)

**Teste**: `tests/unit/recorder/test_step_attrs_when_serialized_then_no_ref_node.py`.

**Anti-regressão**: static test com assert em `steps.jsonl`: `"ref: <Node>"` nunca deve aparecer.

---

### NB-15 — field_snapshots fingerprint colide inputs anônimos

**Origem**: Teste_de_dados_coletados tem `input#[name=]` (fingerprint vazio) aparecendo **1251 vezes** em 1260 batches. Diff-only (RC-16) não detectou porque:
- Input A anônimo mudou de "" → "abc"
- Input B anônimo mudou de "" → "xyz"
- Ambos fingerprint `input#[name=]`
- `__tfLastFieldSnapshotValues["input#[name=]"] = "abc"` overwrite pelo B

**É bug real?** SIM. RC-16 diff-only assume fingerprint único. Inputs anônimos violam essa premissa.

**Fix em `src/testforge/recorder/overlay_inject.js` `_snapshotFields`**: gerar fingerprint mais rico quando id/name vazios:
```js
function _fpForField(el, tag) {
  var id = el.id || '';
  var name = el.name || '';
  if (id || name) return tag + '#' + id + '[name=' + name + ']';
  // NB-15: fall back to css path + position for anonymous inputs
  var css = _tfFinder(el, {seedMinLength: 3}) || '';
  return tag + '@' + css.substring(0, 100);
}
```

**Teste**: `tests/unit/recorder/test_field_snapshot_when_anonymous_inputs_then_distinct_fingerprint.py`.

**Anti-regressão**: contract test com 3 inputs anônimos, mudar valor em cada, verificar 3 snapshots distintos.

---

### NB-16 — _pilot_tmp/ leftover

**Origem**: Todas 4 gravações têm `_pilot_tmp/test_st-*.py` (15KB) sobrado. Nunca limpo.

**É bug real?** SIM. `IncrementalRunner` gera script temporário em `_pilot_tmp/` para pilot smoke run e não limpa.

**Fix em `src/testforge/runner/incremental_runner.py`** (ou onde `_pilot_tmp` é criado): usar `tempfile.TemporaryDirectory` context manager, OU adicionar `shutil.rmtree(pilot_tmp, ignore_errors=True)` em `finally`.

**Teste**: `tests/unit/runner/test_pilot_tmp_when_run_finishes_then_cleaned.py`.

**Anti-regressão**: post-run assertion — `_pilot_tmp/` não existe após finalize.

---

### NB-19 — Bootstrap Carousel auto-fire (evidência massiva)

**Origem**: Teste_de_dados_coletados: **297 clicks em `#next.carousel-control-next`** com **median gap 8.0s ± 3.76s** ao longo de 41 minutos. 
- Bootstrap Carousel default `data-interval="8000"` (8s) — MATCH exato.

**É bug real?** SIM confirmado. Amplia escopo do NB-05.

**Fix**: NB-05 blocklist + heurística cobre isso. Prioridade agora **crit**, não high — 297 events lixo em 1 recording é bloqueador.

**Teste extra**: `tests/integration/recorder/test_carousel_when_auto_fire_then_no_capture.py` — page com Bootstrap Carousel real, gravação, verifica 0 clicks em `.carousel-control-*`.

---

### NB-20 — [REJEITADO] user apagou snapshots manualmente

Usuário deletou snapshots antes de compactar `PDes.zip` (tamanhos ficaram enormes). Não é bug de gravação — é lixo intencional descartado.

**Retirar da lista de trabalho.** Substituir por NB-07 (auto-prune policy) que já cobre o caso.

---

### NB-21 — screenshots/ dir vazio

**Origem**: Acesso_Plataforma_DES_2/screenshots/ tem 0 arquivos. Feature declarada, sem output.

**É bug real?** Provavelmente sim, ou feature ainda não implementada. Investigar `recorder_controller.py` para ver se screenshot capture está ativo.

**Fix**: se feature não implementada, remover dir do lifecycle. Se implementada, debugar o writer.

**Baixa prioridade** — não bloqueia.

---

### NB-22 — testforge_version inconsistente

**Origem**: 
- `recording_metadata.fingerprint.testforge_version: "0.1.0"` (correto)
- `submission_report.testforge_version: "0.1.0"` (hardcoded velho)

**Fix**: encontrar hardcoded `"0.1.0"` em `publisher/` e substituir por leitura de `VERSION` file ou `importlib.metadata.version("testforge")`.

**Baixa prioridade** — cosmético.

---

### NB-23 — Recording de 17s gera 39 test steps

**Origem**: Valida_zeros_a_esquerda:
- `started_at: 2026-07-06T18:11:33.855264`
- `finished_at: 2026-07-06T18:14:06.549540` → ~2min30s gravação
- Steps assertados pelo user: 6 (via `steps.jsonl`)
- Test compilado: 39 steps (via `execution_report.json`)
- 39 / 6 = **6.5x amplificação** do ruído carousel

**É bug real?** SIM. Cascata NB-05/NB-13. Após fix desses dois, ratio deve cair para <2x.

**Métrica de validação**: em recordings pós-fix, `compiled_steps / user_asserts` deve ficar <3.

---

### NB-24 — Submits duplicados back-to-back

**Origem**: Acesso_Plataforma_DES_2 tem 3 pares de submit events consecutivos < 1s no mesmo target (ex.: `tf-btn-pause` × 6 em 3s). Dedup ausente para submits.

**É bug real?** Sim mas baixo impacto. User clicou rápido no botão pause múltiplas vezes.

**Fix**: em `_pushEvent('submit', ...)`, aplicar dedup por (target_id, tag, url) com janela 500ms.

**Baixa prioridade** — só valuable após fixes NB-01/02.

---

## Ordem revisada de commits

Prioridade re-ordenada considerando NB-09..24:

```
1. fix(security): NB-12 password plaintext no keystroke_buffer — INCIDENTE
2. fix(recorder): NB-01 + NB-13 unified — _pushEvent guard + normalizer skip
3. fix(recorder): NB-02 type="button" nos <button> overlay
4. fix(recorder): NB-08 remover tf-btn-minimize + tf-restore-badge
5. fix(recorder): NB-05 + NB-19 blocklist carousel + heurística auto-fire
6. fix(cli): NB-09 + NB-10 _PROJECT_ROOT nested + Windows path guard
7. fix(recorder): NB-11 dom_snapshot field posix slash (PurePosixPath)
8. fix(recorder): NB-04 pause button toggle visual local
9. fix(recorder): NB-03 external step count from Python
10. fix(recorder): NB-14 attrs serialization proper HTML attrs
11. fix(recorder): NB-15 fingerprint anonymous inputs via css_path
12. fix(recorder): NB-20 dom_snapshot field only when file written
13. fix(runner): NB-16 _pilot_tmp cleanup on finalize
14. fix(compiler): NB-17 completeness reads metadata correctly
15. feat(cli): NB-07 prune-snapshots command + auto-prune on run pass
16. fix(recorder): NB-06 assert timeout no-op counter path
17. fix(recorder): NB-24 dedup rapid-fire submits
18. fix(publisher): NB-22 testforge_version dynamic
19. fix(recorder): NB-18 diagnostic feature_path posix
20. investigate: NB-21 screenshots empty dir
```

**Blockers CRÍTICOS que impedem gravações confiáveis**: 1 (segurança), 2, 5, 6.  
**Regressão de fix anterior**: 6, 7 (RC-26 não completo).  
**Cosméticos**: 18, 19, 20.
