# TestForge — Angular/Component Handler Plan

**How to resume:** Read this file. Check `## Sprint Status`. Find first sprint not ✅. Execute it.
**Commit after each sprint.** Update status here before committing.

---

## Architecture

```
src/testforge/handlers/
  __init__.py              # Registry + detect_handler()
  component_handler.py     # Abstract base class
  cdk_overlay.py           # Shared CDK overlay utilities
  angular_material.py      # AngularMaterialHandler (mat-select, mat-autocomplete, mat-datepicker, mat-dialog, mat-tab-group, mat-slide-toggle)

Future (same interface, no refactor needed):
  primeFaces.py
  react_mui.py
```

### ComponentHandler interface
```python
class ComponentHandler:
    def detect(self, candidates: list, element_id: str, tag: str, attrs: dict) -> bool
    def component_type(self) -> str
    def normalize(self, steps: list) -> None   # dedup/collapse in-place
    def execute(self, page, step) -> str        # returns selector used
    def heal(self, evidence, error) -> LLMHealingProposal | None
```

### CDKOverlayHandler
```python
class CDKOverlayHandler:
    OVERLAY_SEL = ".cdk-overlay-pane"
    BACKDROP_SEL = ".cdk-overlay-backdrop"
    OPTION_SEL = "mat-option, [role='option']"
    
    wait_for_open(page, timeout=3000) -> bool
    wait_for_close(page, timeout=3000) -> bool
    find_option(page, text) -> Locator | None
    find_option_by_value(page, value) -> Locator | None
```

### Registry
```python
HANDLERS: list[ComponentHandler] = [AngularMaterialHandler()]

def detect_handler(step) -> ComponentHandler | None:
    candidates = [c.selector for c in step.target.candidates] if step.target else []
    element_id = getattr(step.target, 'element_id', '') or ''
    tag = getattr(step.target, 'tag', '') or ''
    attrs = getattr(step.target, 'attrs', {}) or {}
    for h in HANDLERS:
        if h.detect(candidates, element_id, tag, attrs):
            return h
    return None
```

---

## Sprint Status

- [x] Sprint 1 — Foundation + mat-select
- [ ] Sprint 2 — mat-autocomplete + keypress→fill collapse
- [ ] Sprint 3 — mat-dialog + mat-tab-group + mat-slide-toggle
- [ ] Sprint 4 — Normalizer migration (replace _dedup_datepicker_sequences)
- [ ] Sprint 5 — PrimeFaces handler skeleton
- [ ] Sprint 6 — React MUI handler skeleton

---

## Sprint 1 — Foundation + mat-select

**Goal:** ComponentHandler interface works end-to-end for mat-select. LAB-11 passes without healing.

### Files to create/modify

1. **CREATE** `src/testforge/handlers/__init__.py`
   ```python
   from .component_handler import ComponentHandler
   from .cdk_overlay import CDKOverlayHandler
   from .angular_material import AngularMaterialHandler
   
   HANDLERS: list[ComponentHandler] = [AngularMaterialHandler()]
   
   def detect_handler(step) -> 'ComponentHandler | None':
       candidates = [c.selector for c in step.target.candidates if c.selector] if step.target and step.target.candidates else []
       element_id = getattr(step.target, 'element_id', '') or ''
       tag = getattr(step.target, 'tag', '') or ''
       for h in HANDLERS:
           if h.detect(candidates, element_id, tag):
               return h
       return None
   ```

2. **CREATE** `src/testforge/handlers/component_handler.py`
   - Abstract base class with 4 methods: detect, normalize, execute, heal
   - All raise NotImplementedError

3. **CREATE** `src/testforge/handlers/cdk_overlay.py`
   - CDKOverlayHandler static class
   - wait_for_open, wait_for_close, find_option, find_option_by_value

4. **CREATE** `src/testforge/handlers/angular_material.py`
   - AngularMaterialHandler
   - detect(): checks for mat-select, mat-option, formcontrolname + role=combobox
   - execute(): mat-select → click → wait overlay → find option → click → wait close
   - execute() handles [multiple]: detect aria-multiselectable, use Control modifier
   - normalize(): stubs for mat-select (mark open/close clicks as overlay_nav_noise)
   - heal(): if mat-option not found, re-open and scroll

5. **CREATE** `tests/intent_lab/pages/lab-11-mat-select.html`
   - Simulate Angular Material mat-select with CDK overlay
   - Include: single select, multiple select, disabled option, grouped options
   - No Angular runtime needed — pure HTML/JS simulation of DOM structure:
     - `<mat-select role="combobox">` trigger
     - Fake CDK overlay pane with mat-option items
     - JS: click trigger → show overlay, click option → set value, close overlay

6. **CREATE** `tests/intent_lab/test_lab11_mat_select.py`
   - 8 tests: single select, value captured, multiple select, disabled option,
     overlay closes after select, selector stable across re-render,
     healing if overlay already open, wrong option text fallback

7. **MODIFY** `src/testforge/runner/step_executor.py`
   - In execute() before action routing: check detect_handler(step)
   - If handler found and action == 'click' on combobox: delegate to handler.execute()

### Done criteria
- [ ] `pytest tests/intent_lab/test_lab11_mat_select.py` all pass
- [ ] `pytest tests/test_step_executor.py` still all pass
- [ ] `pytest tests/ -k "normalizer" --ignore=tests/test_browser.py` still all pass
- [ ] mat-select detected: `detect_handler(step)` returns AngularMaterialHandler for mat-select step

---

## Sprint 2 — mat-autocomplete + keypress→fill collapse

**Goal:** Typing "São Paulo" (20 keypress events) becomes 1 fill step. Autocomplete option click collapses into fill+select intent.

### Files to create/modify

1. **MODIFY** `src/testforge/semantic/recording_normalizer.py`
   - Add `_compact_keypress_sequences(steps)` called BEFORE existing `_compact_fill_events`
   - Logic: consecutive `keypress` actions on same target → concatenate values → convert to single `fill`
   - Handle: backspace (remove last char), Enter (stop sequence), Tab (stop sequence)

2. **MODIFY** `src/testforge/handlers/angular_material.py`
   - Add mat-autocomplete detection: `aria-autocomplete="list"` or `aria-owns` containing `mat-autocomplete`
   - Add execute_mat_autocomplete(): fill input → wait for mat-option → click best match
   - normalize(): collapse keypress+fill+option_click into fill+autocomplete_select semantic

3. **CREATE** `tests/intent_lab/pages/lab-12-mat-autocomplete.html`
   - Input with autocomplete dropdown simulation
   - JS: on input → show filtered options, click option → fill input with value, close dropdown

4. **CREATE** `tests/intent_lab/test_lab12_mat_autocomplete.py`
   - 8 tests: type → options appear, select option, value captured, no match fallback,
     partial text → closest match, clear and retype, keypress collapse, Tab closes

### Done criteria
- [ ] `pytest tests/intent_lab/test_lab12_mat_autocomplete.py` all pass
- [ ] "São Paulo" recorded as 20 keypresses → normalized to 1 fill step
- [ ] All prior tests still pass

---

## Sprint 3 — mat-dialog + mat-tab-group + mat-slide-toggle

**Goal:** Fields inside dialogs work. Tab navigation works. Toggle state is captured.

### mat-dialog

**MODIFY** `src/testforge/handlers/angular_material.py`
- detect(): element is inside `.mat-dialog-container` or `.cdk-overlay-container`
- execute(): prefix selectors with `mat-dialog-container >> ` to scope within dialog
- normalize(): mark dialog-open trigger separately from dialog-content steps

**LAB-13:** Dialog with form fields inside. Click button → dialog opens → fill fields → click OK.

### mat-tab-group

**MODIFY** `src/testforge/handlers/angular_material.py`
- detect(): `[role="tab"]` or `mat-tab-header` in candidates
- execute(): `page.click('[role="tab"]:has-text("...")')` → wait for tab panel active
- normalize(): tab clicks are navigation, not form input — mark context

**LAB-14:** 3-tab form. Click each tab, verify content changes.

### mat-slide-toggle

**MODIFY** `src/testforge/handlers/angular_material.py`
- detect(): `mat-slide-toggle` or `[role="switch"]` in candidates
- execute(): click → read aria-checked → store target_state in step context
- normalize(): if click on toggle and aria-checked already matches target → skip (idempotent)

### Done criteria
- [ ] `pytest tests/intent_lab/test_lab13_mat_dialog.py` all pass
- [ ] `pytest tests/intent_lab/test_lab14_mat_tabs.py` all pass
- [ ] LAB slide-toggle tests pass
- [ ] All prior tests still pass

---

## Sprint 4 — Normalizer migration

**Goal:** Remove `_dedup_datepicker_sequences` heuristic. Replace with `AngularMaterialHandler.normalize()`.

### Steps

1. Move `_dedup_datepicker_sequences` logic into `AngularMaterialHandler.normalize()`
2. In `RecordingNormalizer._normalize()`:
   ```python
   # Before (remove):
   self._dedup_datepicker_sequences(stc.steps)
   
   # After:
   for handler in HANDLERS:
       handler.normalize(stc.steps)
   ```
3. Delete `_dedup_datepicker_sequences` method
4. Run all normalizer tests + compile fluxo-errado2 to verify output unchanged

### Done criteria
- [ ] `_dedup_datepicker_sequences` deleted
- [ ] `testforge compile fluxo-errado2` produces same step count as before
- [ ] All normalizer tests pass

---

## Sprint 5 — PrimeFaces handler skeleton

**Goal:** `ComponentHandler` interface proven extensible. PrimeFaces handler registered, does not break anything.

### Steps

1. **CREATE** `src/testforge/handlers/primeFaces.py`
   - PrimeFacesHandler(ComponentHandler)
   - detect(): checks for `p-dropdown`, `ui-selectonemenu`, `ui-datepicker`, PrimeFaces class patterns
   - execute(): stub (raises NotImplementedError with clear message)
   - normalize(): no-op stub
   - heal(): None stub

2. **MODIFY** `src/testforge/handlers/__init__.py`
   - Add PrimeFacesHandler to HANDLERS list
   - Order matters: more specific first

3. **CREATE** `tests/intent_lab/pages/lab-15-primeFaces-select.html`
   - Simulate PrimeFaces SelectOneMenu DOM structure
   - `<div class="ui-selectonemenu">` + dropdown panel

### Done criteria
- [ ] PrimeFacesHandler registered but does nothing yet
- [ ] No existing tests broken
- [ ] detect() returns True for PrimeFaces DOM, False for Angular DOM

---

## Sprint 6 — React MUI handler skeleton

**Goal:** Same pattern as Sprint 5 for React MUI (Material-UI).

### React MUI patterns
- Select: `[role="combobox"]` + `[class*="MuiSelect"]`
- Autocomplete: `[class*="MuiAutocomplete"]` + `[role="option"]`
- Overlay: `[role="listbox"]` (not CDK — MUI uses Popper.js)

### Steps

1. **CREATE** `src/testforge/handlers/react_mui.py`
   - ReactMUIHandler(ComponentHandler)
   - detect(): `MuiSelect`, `MuiAutocomplete`, `[class*="Mui"]` patterns
   - Uses own MuiOverlayHandler (not CDK) or adapts CDKOverlayHandler with different selectors

2. **CREATE** `tests/intent_lab/pages/lab-16-react-mui-select.html`
   - Already have LAB-03 (react-mui page). Extend or add specific select test.

3. Register in HANDLERS

### Done criteria
- [ ] ReactMUIHandler registered
- [ ] detect() correctly identifies React MUI vs Angular Material DOM
- [ ] LAB-03 still passes

---

## Resuming instructions (for next context window)

1. Read `.planning/ANGULAR_COMPONENT_PLAN.md`
2. Find first sprint where status is `[ ]` (not `[x]`)
3. Read sprint's "Files to create/modify" section
4. Implement exactly what's listed
5. Run "Done criteria" tests
6. Update sprint status to `[x]` in this file
7. Commit: `feat(handlers): Sprint N — <sprint name>`
8. Continue to next sprint

**Current state after writing this plan:**
- Sprints 1-6: all pending
- Baseline tests: 16 normalizer pass, 5 step_executor pass
- Handler infrastructure: does not exist yet
