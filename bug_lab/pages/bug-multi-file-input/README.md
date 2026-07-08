# BUG: Multi File Input — Selector Ambiguity

## Symptom
Page has 2+ `<input type="file">` elements. Recorder/normalizer generates identical or ambiguous selectors (e.g., `input[type=file]`), causing Playwright strict mode violation: "strict mode violation: locator resolved to N elements".

## Cause
1. **No `type`-aware selector generation**: `RecordingNormalizer._build_target()` never reads `target.attributes.type`. The `type="file"` attribute is captured by the recorder but discarded during selector candidate construction.
2. **InputAgent healing fallback is generic**: When healing a file upload failure, `InputAgent` returns a static `input[type=file]` selector — this matches ALL file inputs on the page.
3. **Differentiation relies solely on generic chain**: Two file inputs are distinguished only by `data-testid` → `id` → `name` → `label` → `placeholder` → `text` → CSS classes. If two inputs share a label text (e.g., both "Upload"), they get identical `label:has-text(...)` selectors.

## Reproduction
1. Open `bug_lab/pages/bug-multi-file-input/index.html`
2. Page contains 4 file inputs, each with different identification strategies:
   - `#resume-upload` — visible `<label>` element
   - `#photo-upload` — `aria-label` only, no visible label
   - `#cert-upload` — `data-testid` attribute
   - `#doc-upload` — `id` + `name` only, no label/aria/testid
3. Try selecting each with `page.locator("input[type=file]")` → resolves to 4 elements (strict mode violation)
4. Try InputAgent healing → returns single `input[type=file]` → fails for any page with >1 file input

## Validation
```bash
pytest bug_lab/tests/test_bug_multi_file_input.py -v
```

## Fix
1. **Normalizer**: Add `input[type=file]` + disambiguating attribute to candidate chain when `target.attributes.type == "file"`
2. **InputAgent**: When healing file input failures, use more specific selector than bare `input[type=file]` — incorporate `name`, `id`, `label`, or positional context
3. **Document**: Catalog `SEL-009` (multiple elements found) as known pattern for multi-file-input pages

## Related
- BUG: File Input — `set_input_files` vs `fill(fakepath)` (`bug_lab/pages/bug-file-input/`)
- FAM-07 taxonomy (`FILE-001`)
- SEL-009 taxonomy (`selectors_must_be_unique`)
