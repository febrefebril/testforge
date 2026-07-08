# BUG: UTF-8 Encoding — Special Characters Lost in Recording

## Symptom
When Playwright records interactions with a page containing UTF-8 special characters
(ç, ñ, é, ü, ã, ô, €, —, …, etc.), the recorded output may mangle or corrupt
these characters if encoding is not preserved properly.

Affected characters include:
- Portuguese: ç, ã, õ, ô, ê, á, à
- Spanish: ñ, ¡, ¿, é, í
- German: ü, ö, ß, ä
- French: è, é, ê, ë, œ
- Symbols: €, ¥, £, ©, ®, ™, — (em-dash), … (ellipsis)

The recording engine must properly:
1. Read page content with correct charset (UTF-8)
2. Preserve special characters in selectors (text-based locators, data-testid)
3. Preserve special characters in recorded step descriptions
4. Not mangle Unicode code points (no mojibake)

## Cause
Potential encoding failure points:
1. **HTTP response charset**: If server doesn't send `Content-Type: text/html; charset=UTF-8`,
   browser may default to Latin-1, corrupting multi-byte UTF-8 sequences.
2. **Python string encoding**: `str()` calls or file I/O without explicit `encoding='utf-8'`
   may use system default (ASCII/Latin-1), causing `UnicodeEncodeError` substitution.
3. **JSON serialization**: `json.dumps()` with `ensure_ascii=True` (default) escapes
   all non-ASCII chars to `\uXXXX`, which may be mangled on round-trip.
4. **Selector construction**: Text-based selectors with special chars must be properly escaped
   or the CSS engine may reject them.
5. **Regex character classes**: `[^"']` patterns may silently strip multi-byte characters.

## Reproduction
```bash
# 1. Run encoding test: reads UTF-8 text from DOM
pytest bug_lab/tests/test_bug_encoding.py::test_spanish_text_preserved -v

# 2. Run encoding test: reads Portuguese accented text
pytest bug_lab/tests/test_bug_encoding.py::test_portuguese_text_preserved -v

# 3. Run encoding test: German umlauts preserved
pytest bug_lab/tests/test_bug_encoding.py::test_german_text_preserved -v

# 4. Run encoding test: French accents preserved
pytest bug_lab/tests/test_bug_encoding.py::test_french_text_preserved -v

# 5. Run all encoding tests
pytest bug_lab/tests/test_bug_encoding.py -v
```

**Manual reproduction:**
1. Load `bug_lab/pages/bug-encoding/index.html` in browser
2. Inspect the DOM — all characters should render correctly
3. Try recording interactions with buttons containing special characters:
   - Click "Añadir información"
   - Click "Configuração avançada"
   - Click "Öffnen"
4. Check recorded output — if button text appears mangled (e.g., `AÃ±adir` instead of `Añadir`),
   encoding is corrupted.

## Fix
Not yet applied (bug confirmed, fix pending):

Potential fixes:
1. Ensure server sends correct `Content-Type` header with `charset`
2. Use `encoding='utf-8'` for all file I/O in recording pipeline
3. Use `json.dumps(obj, ensure_ascii=False)` for human-readable output
4. Use `\\.` CSS escaping for special characters in selectors

## Validation
```bash
# All encoding tests
pytest bug_lab/tests/test_bug_encoding.py -v

# Run all bug lab tests
pytest bug_lab/tests/ -v
```

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_spanish_text_preserved` | Spanish special chars (ñ, é, ¿, ¡) read correctly from DOM |
| `test_portuguese_text_preserved` | Portuguese accented chars (ç, ã, õ) preserved |
| `test_german_text_preserved` | German umlauts (ü, ö, ß) preserved |
| `test_french_text_preserved` | French accents (è, é, ê, œ) preserved |
| `test_symbols_preserved` | Special symbols (€, ¥, ©, —, …) preserved |
| `test_spanish_words_list` | Spanish words with accents in list items |
| `test_portuguese_words_list` | Portuguese words with ç, ã, õ in list items |
| `test_german_words_list` | German words with umlauts in list items |
| `test_french_words_list` | French words with accents in list items |
| `test_button_spanish_click` | Button with ñ character clickable by text locator |
| `test_button_portuguese_click` | Button with ç, ã characters clickable by text locator |
| `test_button_german_click` | Button with ö character clickable by text locator |
| `test_meta_charset_present` | Page declares charset=UTF-8 |
| `test_html_lang_declared` | Page declares lang attribute |
| `test_special_chars_in_output` | Button clicks produce correct accented output |
| `test_no_mojibake` | Assertion that text != common mojibake patterns |

(End of file — total 117 lines)
