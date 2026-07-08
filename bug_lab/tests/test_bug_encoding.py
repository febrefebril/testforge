"""BUG: UTF-8 Encoding — Special characters lost in recording.

Symptom:
    Pages with UTF-8 special characters (ç, ñ, é, ü, ã, ô, €, —, …)
    may have content mangled if the recording pipeline doesn't handle
    encoding properly (charset, file I/O, JSON serialization, selectors).

Cause:
    Multiple failure points: HTTP Content-Type header, Python str encoding,
    JSON ensure_ascii, CSS selector escaping, regex character classes.

Fix:
    Ensure UTF-8 at all layers: HTTP headers, file I/O, JSON serialization,
    CSS selector escaping, and regex patterns.
"""
import json
import os

import pytest


# ── Text content preservation tests ──────────────────────────────────────

@pytest.mark.slow
def test_spanish_text_preserved(test_server, page):
    """Spanish chars (ñ, é, ¿, ¡) read correctly from DOM."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="spanish-text"]').text_content()

    expected_substrings = [
        "niño",         # enye char
        "café",         # e-acute
        "piñata",       # enye char
        "¿Cómo",        # inverted question + o-acute
        "¡Qué",         # inverted exclamation + e-acute
    ]
    for sub in expected_substrings:
        assert sub in text, f"Expected '{sub}' in Spanish text, got: {text!r}"


@pytest.mark.slow
def test_portuguese_text_preserved(test_server, page):
    """Portuguese accented chars (ç, ã, õ, ô) preserved."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="portuguese-text"]').text_content()

    expected_substrings = [
        "preguiçoso",   # c-cedilla
        "Coração",      # a-tilde (capital C in HTML)
        "atenção",      # c-cedilla
        "promoção",     # c-cedilla
        "ação",         # c-cedilla
        "compreensão",  # a-tilde
    ]
    for sub in expected_substrings:
        assert sub in text, f"Expected '{sub}' in Portuguese text, got: {text!r}"


@pytest.mark.slow
def test_german_text_preserved(test_server, page):
    """German umlauts (ü, ö, ß, ä) preserved."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="german-text"]').text_content()

    expected_substrings = [
        "Fußballspieler",  # esszet
        "wünschte",        # u-umlaut
        "großes",          # esszet
        "Öfter",           # O-umlaut
        "Übermäßig",       # U-umlaut + esszet + a-umlaut
        "Sonderzeichen",   # no special chars, basic check
    ]
    for sub in expected_substrings:
        assert sub in text, f"Expected '{sub}' in German text, got: {text!r}"


@pytest.mark.slow
def test_french_text_preserved(test_server, page):
    """French accents (è, é, ê, ë, œ) preserved."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="french-text"]').text_content()

    expected_substrings = [
        "élève",      # e-acute + e-grave
        "réussi",     # e-acute
        "grâce",      # a-circumflex
        "étude",      # e-acute
        "Cœur",       # o-e ligature
        "sœur",       # o-e ligature
        "œuvre",      # o-e ligature
    ]
    for sub in expected_substrings:
        assert sub in text, f"Expected '{sub}' in French text, got: {text!r}"


@pytest.mark.slow
def test_symbols_preserved(test_server, page):
    """Special symbols (€, ¥, ©, —, …) preserved."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="symbols-text"]').text_content()

    expected_symbols = [
        "€",       # Euro
        "¥",       # Yen
        "£",       # Pound
        "©",       # Copyright
        "®",       # Registered
        "™",       # Trademark
        "—",       # em-dash (not - hyphen; not -- en-dash)
        "…",       # ellipsis (not ... three dots)
    ]
    for sym in expected_symbols:
        assert sym in text, f"Expected '{sym}' in symbols text, got: {text!r}"


# ── Word list preservation tests ─────────────────────────────────────────

@pytest.mark.slow
def test_spanish_words_list(test_server, page):
    """Spanish words with accents in list items."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    items = page.locator('[data-testid="spanish-words"] li').all_text_contents()

    expected = ["año", "mañana", "señor", "camión", "baño"]
    for i, exp in enumerate(expected):
        assert exp in items[i], f"Expected '{exp}' in item {i}, got: {items[i]!r}"


@pytest.mark.slow
def test_portuguese_words_list(test_server, page):
    """Portuguese words with ç, ã, õ in list items."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    items = page.locator('[data-testid="portuguese-words"] li').all_text_contents()

    expected = ["açaí", "coração", "atenção", "promoção", "feijão"]
    for i, exp in enumerate(expected):
        assert exp in items[i], f"Expected '{exp}' in item {i}, got: {items[i]!r}"


@pytest.mark.slow
def test_german_words_list(test_server, page):
    """German words with umlauts in list items."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    items = page.locator('[data-testid="german-words"] li').all_text_contents()

    expected = ["schön", "Füße", "Österreich", "über", "größte"]
    for i, exp in enumerate(expected):
        assert exp in items[i], f"Expected '{exp}' in item {i}, got: {items[i]!r}"


@pytest.mark.slow
def test_french_words_list(test_server, page):
    """French words with accents in list items."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    items = page.locator('[data-testid="french-words"] li').all_text_contents()

    expected = ["élève", "grâce", "cœur", "sœur", "œuvre"]
    for i, exp in enumerate(expected):
        assert exp in items[i], f"Expected '{exp}' in item {i}, got: {items[i]!r}"


# ── Button interaction with special chars ────────────────────────────────

@pytest.mark.slow
def test_button_spanish_click(test_server, page):
    """Button with ñ character clickable by text locator."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    # Click using text= locator (tests that CSS text selector handles ñ)
    page.locator('text=Añadir información').click()

    output = page.locator('[data-testid="output"]').text_content()
    assert "Seleccionaste" in output
    assert "Español" in output
    assert "¡Olé!" in output


@pytest.mark.slow
def test_button_portuguese_click(test_server, page):
    """Button with ç, ã characters clickable by text locator."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    page.locator('text=Configuração avançada').click()

    output = page.locator('[data-testid="output"]').text_content()
    assert "Selecionaste" in output
    assert "Português" in output
    assert "Obrigado!" in output


@pytest.mark.slow
def test_button_german_click(test_server, page):
    """Button with ö character clickable by text locator."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    page.locator('text=Öffnen').click()

    output = page.locator('[data-testid="output"]').text_content()
    assert "Ausgewählt" in output
    assert "Deutsch" in output
    assert "Wunderbar!" in output


# ── Metadata preservation tests ──────────────────────────────────────────

@pytest.mark.slow
def test_meta_charset_present(test_server, page):
    """Page declares charset=UTF-8."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    # Check the charset meta tag
    charset_meta = page.locator('meta[charset]').get_attribute("charset")
    assert charset_meta and charset_meta.upper() in ("UTF-8", "UTF8"), \
        f"Expected charset=UTF-8, got: {charset_meta!r}"


@pytest.mark.slow
def test_html_lang_declared(test_server, page):
    """Page declares lang attribute for locale awareness."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    lang = page.locator("html").get_attribute("lang")
    assert lang, "Expected <html lang='...'> attribute"
    assert "pt" in lang.lower(), \
        f"Expected Portuguese locale, got: {lang!r}"


# ── No mojibake / corruption tests ──────────────────────────────────────

@pytest.mark.slow
def test_no_mojibake_spanish(test_server, page):
    """Spanish text doesn't contain common UTF-8 corruption artifacts."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="spanish-text"]').text_content()

    # Mojibake patterns: double-encoded or Latin-1 misinterpretations
    mojibake_patterns = [
        "Ã±",    # UTF-8 ñ interpreted as Latin-1 = Ã±
        "Ã©",    # UTF-8 é as Latin-1 = Ã©
        "Ã¡",    # UTF-8 á as Latin-1 = Ã¡
        "Ã³",    # UTF-8 ó as Latin-1 = Ã³
        "Â¿",    # UTF-8 ¿ as Latin-1 = Â¿
        "Â¡",    # UTF-8 ¡ as Latin-1 = Â¡
        "ï¿½",   # Replacement char mojibake
        "\ufffd",  # Unicode replacement character (�)
    ]
    for pattern in mojibake_patterns:
        assert pattern not in text, \
            f"Mojibake pattern {pattern!r} found in Spanish text: {text!r}"


@pytest.mark.slow
def test_no_mojibake_portuguese(test_server, page):
    """Portuguese text doesn't contain common UTF-8 corruption artifacts."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="portuguese-text"]').text_content()

    mojibake_patterns = [
        "Ã§",    # UTF-8 ç as Latin-1 = Ã§
        "Ã£",    # UTF-8 ã as Latin-1 = Ã£
        "Ãµ",    # UTF-8 õ as Latin-1 = Ãµ
        "Ã´",    # UTF-8 ô as Latin-1 = Ã´
        "Ãª",    # UTF-8 ê as Latin-1 = Ãª
        "Ã¡",    # UTF-8 á as Latin-1 = Ã¡
        "\ufffd",
    ]
    for pattern in mojibake_patterns:
        assert pattern not in text, \
            f"Mojibake pattern {pattern!r} found in Portuguese text: {text!r}"


@pytest.mark.slow
def test_no_mojibake_german(test_server, page):
    """German text doesn't contain common UTF-8 corruption artifacts."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    text = page.locator('[data-testid="german-text"]').text_content()

    mojibake_patterns = [
        "Ã¼",   # UTF-8 ü as Latin-1 = Ã¼
        "Ã¶",   # UTF-8 ö as Latin-1 = Ã¶
        "Ã¤",   # UTF-8 ä as Latin-1 = Ã¤
        "ÃŸ",   # UTF-8 ß as Latin-1 = ÃŸ
        "\ufffd",
    ]
    for pattern in mojibake_patterns:
        assert pattern not in text, \
            f"Mojibake pattern {pattern!r} found in German text: {text!r}"


# ── JSON round-trip encoding test ────────────────────────────────────────

@pytest.mark.slow
def test_json_roundtrip_encoding(test_server, page):
    """JSON serialization round-trips without mangling UTF-8 characters."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    # Collect all text content from data-testid elements
    test_data = {}
    for el in page.locator('[data-testid]').all():
        tid = el.get_attribute("data-testid")
        text = el.text_content()
        if text and tid:
            test_data[tid] = text

    # Round-trip through JSON
    json_str = json.dumps(test_data, ensure_ascii=False)
    parsed = json.loads(json_str)

    # Verify round-trip preserves content
    for key, original in test_data.items():
        assert key in parsed, f"Key '{key}' lost in JSON round-trip"
        assert parsed[key] == original, \
            f"JSON round-trip corrupted '{key}': {original!r} -> {parsed[key]!r}"


# ── Page encoding metadata test ──────────────────────────────────────────

@pytest.mark.slow
def test_page_title_encoding(test_server, page):
    """Page title preserves UTF-8 special characters."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    title = page.title()

    # Title should contain accented chars
    assert "ç" in title.lower() or "especiais" in title.lower(), \
        f"Title encoding wrong: {title!r}"
    assert len(title) > 10, f"Title too short, likely mangled: {title!r}"


# ── Special chars in data-testid attributes ──────────────────────────────

@pytest.mark.slow
def test_data_testid_utf8_buttons(test_server, page):
    """Buttons with special chars have correct data-testid values."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    # data-testid values should be preserved as-is (ASCII in these cases)
    btn_ids = ["btn-español", "btn-português", "btn-deutsch"]
    for bid in btn_ids:
        el = page.locator(f'[data-testid="{bid}"]')
        count = el.count()
        assert count == 1, f"Expected 1 element with data-testid='{bid}', found {count}"


@pytest.mark.slow
def test_special_chars_in_output(test_server, page):
    """Button clicks produce correct accented output text."""
    page.goto(f"{test_server}/bug-encoding/index.html")

    # Test Spanish
    page.locator('[data-testid="btn-español"]').click()
    output = page.locator('[data-testid="output"]').text_content()
    assert "Seleccionaste" in output
    assert "Olé" in output  # accented

    # Test Portuguese
    page.locator('[data-testid="btn-português"]').click()
    output = page.locator('[data-testid="output"]').text_content()
    assert "Selecionaste" in output
    assert "Obrigado" in output

    # Test German
    page.locator('[data-testid="btn-deutsch"]').click()
    output = page.locator('[data-testid="output"]').text_content()
    assert "Ausgewählt" in output  # a-umlaut
    assert "Wunderbar" in output
