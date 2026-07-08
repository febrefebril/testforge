# BUG: Mat-Icon Accessible Name Contamination

## Symptom
Angular Material buttons with `<mat-icon>` produce contaminated `accessible_name`:
- Expected: `"Carregar"`
- Actual: `"file_upload Carregar"` (icon ligature leaks in)

This causes Playwright locators using `role=button[name="file_upload Carregar"]` to fail or be brittle.

## Cause
`_build_target()` in `recording_normalizer.py` line 345 used `accessible_name` raw without `_clean_text()`:
```python
name = target_data.get("accessible_name") or _clean_text(...)
```
`_clean_text()` existed and correctly filtered `_MATERIAL_ICONS` from the `text` field, but was never applied to `accessible_name`.

## Reproduction
1. Page: `bug_lab/pages/bug-mat-icon-name/index.html`
2. Test: `pytest bug_lab/tests/test_bug_mat_icon_name.py -v`

## Fix
Applied `_clean_text()` to `accessible_name`:
```python
name = _clean_text(target_data.get("accessible_name") or "") or _clean_text(target_data.get("text") or "")
```

## Validation
```bash
pytest bug_lab/tests/test_bug_mat_icon_name.py tests/ -v
```
