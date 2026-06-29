"""Auto-healing multi-atributo em runtime — resolve seletores pontuando elementos DOM
vivos contra a fingerprint gravada.

Heuristico sobre estrito — score 0.0-1.0, threshold define confianca.
Projetado para ser chamado de scripts de teste gerados quando o locator Playwright falha.

Catalogo auto-aprendido: resolucoes de healing bem-sucedidas sao gravadas em arquivo JSONL.
Proxima vez que a mesma fingerprint aparecer, o catalogo retorna instantaneamente (<1ms)
em vez de re-pontuar contra o DOM vivo.

Uso (script gerado)::

    from testforge.runtime.healer import resolve_selector
    _best = resolve_selector(page, ["input#foo", "input[name='bar']"], {"tag": "input", "placeholder": "R$0,00"})
    if _best:
        page.fill(_best, "5000")
    else:
        raise AssertionError("fill step 1 falhou")
"""

import json
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default confidence threshold — below this, None is returned
CONFIDENCE_THRESHOLD = 0.40

# Default catalog path (relative to CWD)
_DEFAULT_CATALOG_PATH = ".testforge/heal_catalog.jsonl"

# Max entries in catalog before oldest eviction
_CATALOG_MAX_ENTRIES = 1000

# Entry TTL: 30 days in seconds
_CATALOG_TTL = 30 * 24 * 3600

# Injected JS to extract live element attributes for scoring
_LIVE_ATTRS_JS = """(el) => ({
    tag: (el.tagName || '').toLowerCase(),
    role: el.getAttribute('role') || '',
    accessible_name: el.getAttribute('aria-label') || '',
    placeholder: el.getAttribute('placeholder') || '',
    name: el.getAttribute('name') || '',
    id: el.id || '',
    text: (el.textContent || '').trim().slice(0, 60),
})"""


def _score_match(live: dict, fingerprint: dict) -> float:
    """Pontua 0.0-1.0 o quanto um elemento vivo corresponde a fingerprint gravada.

    Cada chave da fingerprint contribui com seu peso apenas quando presente.
    Correspondencias sao exatas a menos que marcadas fuzzy (substring permitida a 0.6x).
    """
    if not fingerprint or not live:
        return 0.0

    total_weight = 0.0
    matched_weight = 0.0

    # (live_key, fp_key, peso, permitir_substring)
    checks = [
        ("tag", "tag", 0.15, False),
        ("role", "role", 0.20, False),
        ("accessible_name", "accessible_name", 0.25, True),
        ("placeholder", "placeholder", 0.15, True),
        ("name", "name", 0.10, False),
        ("id", "id", 0.10, False),
        ("text", "text", 0.15, True),
    ]

    for live_key, fp_key, weight, allow_substring in checks:
        lv = (live.get(live_key) or "").strip()
        fv = (fingerprint.get(fp_key) or "").strip()
        if not fv:
            continue  # nao registrado na fingerprint, pula
        total_weight += weight
        if not lv:
            continue  # elemento nao tem este atributo, sem match
        if allow_substring:
            lv_lower = lv.lower()
            fv_lower = fv.lower()
            if lv_lower == fv_lower:
                matched_weight += weight
            elif fv_lower in lv_lower or lv_lower in fv_lower:
                matched_weight += weight * 0.6
        else:
            if lv == fv:
                matched_weight += weight

    if total_weight == 0.0:
        return 0.0
    return min(matched_weight / total_weight, 1.0)


# ---------------------------------------------------------------------------
# Catalogo auto-aprendido — registra resolucoes de healing bem-sucedidas para reuso <1ms
# ---------------------------------------------------------------------------

def _fp_key(fp: dict) -> str:
    """Canonical JSON key for a fingerprint (sorted keys for determinism)."""
    return json.dumps(fp, sort_keys=True, ensure_ascii=False, default=str)


@dataclass
class _CatalogEntry:
    fingerprint: dict
    selector: str
    score: float
    success_count: int
    last_success: float  # epoch seconds


class HealCatalog:
    """Catalogo persistente de resolucoes de healing bem-sucedidas.

    Mapeia fingerprints de elementos para seletores que funcionaram antes.
    Busca e O(1) dict indexado por fingerprint JSON canonica.

    Armazenamento e JSONL em ``path`` — um objeto JSON por linha.
    Caminho padrao e ``.testforge/heal_catalog.jsonl`` (sobrescreve via
    ``TESTFORGE_HEAL_CATALOG`` env var). Defina path como ``""`` para
    apenas memoria (sem persistencia).
    """

    def __init__(self, path: str | None = None):
        env_path = os.environ.get("TESTFORGE_HEAL_CATALOG", "")
        self.path = (
            path if path is not None
            else env_path if env_path
            else _DEFAULT_CATALOG_PATH
        )
        self._entries: dict[str, _CatalogEntry] = {}
        self._load()

    def lookup(self, fingerprint: dict) -> str | None:
        """Retorna melhor selector para correspondencia *exata* de fingerprint, ou None.

        Entradas expiradas (30d desde ultimo sucesso) sao puladas e removidas.
        """
        if not fingerprint:
            return None
        key = _fp_key(fingerprint)
        entry = self._entries.get(key)
        if entry is None:
            return None
        age = time.time() - entry.last_success
        if age > _CATALOG_TTL:
            del self._entries[key]
            return None
        logger.info("heal_catalog: HIT fp_key=%s sel=%s score=%.2f n=%d",
                     key, entry.selector, entry.score, entry.success_count)
        return entry.selector

    def record(self, fingerprint: dict, selector: str, score: float):
        """Registra ou reforca um healing bem-sucedido.

        Novas entradas sao adicionadas. Entradas existentes tem seu contador
        incrementado e score atualizado para max(antigo, novo).
        """
        if not fingerprint or not selector:
            return
        key = _fp_key(fingerprint)
        now = time.time()
        if key in self._entries:
            entry = self._entries[key]
            entry.success_count += 1
            entry.last_success = now
            if score > entry.score:
                entry.score = score
        else:
            self._entries[key] = _CatalogEntry(
                fingerprint=fingerprint,
                selector=selector,
                score=score,
                success_count=1,
                last_success=now,
            )
        self._save()

    def _key_set(self) -> set[str]:
        return set(self._entries.keys())

    # ----- serialization -----

    def _load(self):
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("heal_catalog: skip bad line in %s: %r",
                                       self.path, line[:80])
                        continue
                    entry = _CatalogEntry(
                        fingerprint=data["fp"],
                        selector=data["sel"],
                        score=data["score"],
                        success_count=data.get("n", 1),
                        last_success=data.get("ts", 0.0),
                    )
                    self._entries[_fp_key(entry.fingerprint)] = entry
            # Evict expired at load time
            now = time.time()
            expired = [k for k, e in self._entries.items()
                       if now - e.last_success > _CATALOG_TTL]
            for k in expired:
                del self._entries[k]
        except Exception as exc:
            logger.warning("heal_catalog: load error %s — %s", self.path, exc)

    def _save(self):
        if not self.path:
            return
        try:
            # Evict oldest if over limit
            if len(self._entries) > _CATALOG_MAX_ENTRIES:
                sorted_entries = sorted(
                    self._entries.items(),
                    key=lambda x: x[1].last_success,
                )
                excess = len(sorted_entries) - _CATALOG_MAX_ENTRIES
                for k, _ in sorted_entries[:excess]:
                    del self._entries[k]

            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            now = time.time()
            with open(self.path, "w", encoding="utf-8") as f:
                for entry in self._entries.values():
                    # Skip expired at write time
                    if now - entry.last_success > _CATALOG_TTL:
                        continue
                    f.write(json.dumps({
                        "fp": entry.fingerprint,
                        "sel": entry.selector,
                        "score": entry.score,
                        "n": entry.success_count,
                        "ts": entry.last_success,
                    }, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("heal_catalog: save error %s — %s", self.path, exc)

    def clear(self):
        """Limpa todas as entradas (usado em testes)."""
        self._entries.clear()
        if self.path and os.path.exists(self.path):
            try:
                os.remove(self.path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Singleton do catalogo global — transparente para scripts gerados
# ---------------------------------------------------------------------------

_CATALOG: HealCatalog | None = None


def _get_catalog() -> HealCatalog:
    """Inicializacao lazy do singleton do catalogo global."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = HealCatalog()
    return _CATALOG


def reset_catalog():
    """Reseta o singleton do catalogo e limpa arquivo persistente (para isolamento de teste)."""
    global _CATALOG
    if _CATALOG is not None:
        _CATALOG.clear()
    _CATALOG = None


def resolve_selector(
    page,
    selectors: list[str],
    fingerprint: dict | None = None,
    threshold: float | None = None,
) -> str | None:
    """Tenta cada seletor CSS contra DOM vivo e pontua correspondencias contra fingerprint.

    Verifica :class:`HealCatalog` primeiro — se uma resolucao bem-sucedida anterior
    existir para a fingerprint exata, retorna instantaneamente (<1ms).

    Caso contrario, faz fallback para pontuacao DOM vivo. Em sucesso, grava automaticamente
    o resultado no catalogo para reuso futuro.

    Args:
        page: Playwright Page (API sync).
        selectors: Strings de seletor CSS para avaliar.
        fingerprint: Dict de atributos de elemento gravados (de SemanticTarget).
        threshold: Score minimo para aceitar uma correspondencia. Padrao: CONFIDENCE_THRESHOLD.

    Returns:
        Melhor string de seletor correspondente, ou None se nenhum pontuar acima do threshold.
    """
    thresh = threshold if threshold is not None else CONFIDENCE_THRESHOLD

    # Caminho rapido: busca no catalogo (<1ms, sem interacao DOM)
    if fingerprint:
        cat = _get_catalog()
        cached = cat.lookup(fingerprint)
        if cached is not None:
            return cached

    # Caminho lento: pontuacao DOM vivo
    candidates: list[tuple[float, str]] = []

    for sel in selectors:
        loc = page.locator(sel)
        try:
            count = loc.count()
        except Exception:
            continue
        if count == 0:
            continue

        # Extrai atributos do primeiro (e tipicamente unico) match
        try:
            handle = loc.first.element_handle()
            if not handle:
                continue
            live = page.evaluate(_LIVE_ATTRS_JS, handle)
            if not live:
                continue
        except Exception:
            continue

        score = _score_match(live, fingerprint or {})
        if score > 0.0:
            candidates.append((score, sel))
            logger.debug("resolve_selector: sel=%s score=%.2f live=%s", sel, score, live)

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_sel = candidates[0]
    if best_score >= thresh:
        logger.info("resolve_selector: best=%s score=%.2f threshold=%.2f", best_sel, best_score, thresh)
        # Auto-registro no catalogo para reuso futuro
        if fingerprint:
            try:
                _get_catalog().record(fingerprint, best_sel, best_score)
            except Exception:
                pass
        return best_sel

    logger.info("resolve_selector: best=%s score=%.2f below threshold=%.2f", best_sel, best_score, thresh)
    return None
