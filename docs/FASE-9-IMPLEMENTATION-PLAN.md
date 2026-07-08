# Fase 9 — Taxonomy + Lifecycle Overhaul: Plano de Implementação

**RC coberto**: RC-17 (16 bugs: REC-22, 64, 71, 75, 76, 77, 79, 80, 81, 82, 83, 87, 88, 90, 91, 92)  
**Estimativa**: ~8h  
**Branch**: `feature/inline-overlay-prompt` (branch ativa — não criar nova)

## Contexto obrigatório antes de começar

Leia nesta ordem:
1. `docs/HANDOFF-NEXT-LLM.md` — estado atual do projeto
2. `docs/RECORDING-BUGS-FIX-PLAN.md` seção "FASE 9"
3. `src/testforge/recorder/recording_session.py` — `RecordingSession`, `RecordingSessionManager`, `_resolve_name`
4. `src/testforge/recorder/recording_status.py` — `RecordingStatus` enum
5. `src/testforge/cli/app.py` linhas 38–55 (`_sanitize_name`) e 317–343 (`_mark_failed_recording`)
6. `src/testforge/recorder/capture_fingerprint.py` — `CAPTURE_SCHEMA_VERSION`

Sanity antes de mexer: `pytest -m "unit or contract or regression" -q` → deve dar **346 passed, 1 xfailed**.

---

## Contratos hard (nunca quebrar)

- `[[feedback-no-regrave]]`: nunca regravar para testar fix. Iterar `compile + run` sobre recordings existentes.
- `[[feedback-pii-alert-only]]`: dados sensíveis nunca mascarados — detectar e alertar apenas.
- `[[feedback-no-regression]]`: multi-source matrix. Se tocar `_sanitize_name`, rodar todos testes que usam names/slugs.

---

## Grupos de trabalho

A fase é dividida em 3 grupos independentes. Implementar na ordem A → B → C (B e C podem paralelizar após A).

- **Grupo A** — Schema + taxonomy (REC-22, 64, 79, 80, 81, 87): mudanças em `recording_session.py` e `recording_status.py`
- **Grupo B** — Dedup + sufixo (REC-71, 75, 76, 77, 82): mudanças em `cli/app.py` e `recording_session.py`
- **Grupo C** — recordings_failed lifecycle (REC-83, 88, 90, 91, 92): mudanças em `cli/app.py`

---

## Grupo A — Schema + Taxonomy

### A1: Suporte ao 4º nível de taxonomy (REC-22)

**Origem do bug**: Recording R3 (`PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda`). Path tem 4 níveis mas `recording_metadata.json` só captura 3 (`system/suite/test_case`). O folder `Valida_zeros_a_esquerda` não aparece em metadata.

**Confirmar que é bug real**:
```bash
cat "src/testforge/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda/recording_metadata.json" | python3 -m json.tool | grep -E "system|suite|test_case|scenario"
```
Esperado: campo `scenario` ausente. Path é 4 níveis. Bug confirmado.

**Fix em `src/testforge/recorder/recording_session.py`**:

1. Adicionar `scenario: str = ""` ao dataclass `RecordingSession` (linha ~17, após `test_case`).
2. Incluir `"scenario": self.scenario` no método `to_dict()` (linha ~57).
3. Adicionar parâmetro `scenario: str = ""` ao método `RecordingSessionManager.start()` (linha ~89).
4. Passar `scenario=scenario` na criação do `RecordingSession` (linha ~103).
5. Incluir `"scenario": scenario` no dict de metadata gravado em `recording_metadata.json` (linha ~118).

**Fix em `src/testforge/cli/app.py`**:

6. Adicionar `--scenario` ao argparser (próximo ao `--test-case`, linha ~2580):
   ```python
   rec.add_argument("--scenario", default="", help="Cenário (4º nível: system/suite/test_case/scenario)")
   ```
7. Passar `scenario=args.scenario` ao chamar `manager.start()` na função de record.

**Teste** `tests/unit/recorder/test_taxonomy_when_4_levels_then_scenario_field_persisted.py`:
```python
@pytest.mark.unit
class TestTaxonomyWhen4LevelsThenScenarioFieldPersisted:
    def test_recording_session_has_scenario_field(self):
        from testforge.recorder.recording_session import RecordingSession
        s = RecordingSession(recording_id="x", system="SYS", suite="SUITE",
                             test_case="TC", scenario="SC")
        d = s.to_dict()
        assert d["scenario"] == "SC"

    def test_scenario_empty_by_default(self):
        from testforge.recorder.recording_session import RecordingSession
        s = RecordingSession(recording_id="x")
        assert s.to_dict()["scenario"] == ""
```

**Anti-regressão**: rodar `pytest tests/unit/recorder/ tests/contract/ -q` — nenhum teste existente deve quebrar porque `scenario` tem default `""`.

---

### A2: Cross-check metadata.system vs page_title (REC-64)

**Origem do bug**: Recording R8 GESTAO. `metadata.system = "GESTAO"` mas `page_title` do primeiro evento é `"Sistema de Gestão de Honras"` (abreviação oficial = **SGH**, não GESTAO). Discrepância de naming.

**Confirmar que é bug real**:
```bash
python3 -c "
import json
data = json.load(open('src/testforge/GESTAO/suite exploratoria/deve_fazer_upload_sisgh_3/recording_metadata.json'))
print('system:', data.get('system'))
events = [json.loads(l) for l in open('src/testforge/GESTAO/suite exploratoria/deve_fazer_upload_sisgh_3/raw_events.jsonl')]
print('first page_title:', events[0].get('page_title') if events else 'N/A')
" 2>/dev/null || echo "Path pode variar — confirmar com recording R8"
```
Bug é de baixo impacto (reporting), mas alerta útil.

**Fix em `src/testforge/cli/app.py`** — na função `compile` (após carregar metadata e raw_events):

```python
def _warn_system_title_mismatch(meta: dict, raw_events_path: str) -> None:
    """REC-64: alert when metadata.system diverges from page_title of first event."""
    system = (meta.get("system") or "").strip().lower()
    if not system:
        return
    try:
        with open(raw_events_path, encoding="utf-8") as f:
            first_line = f.readline()
        if not first_line.strip():
            return
        event = json.loads(first_line)
        page_title = (event.get("page_title") or "").strip().lower()
        if page_title and system not in page_title and page_title not in system:
            print(f"[TestForge] [WARN] metadata.system='{meta.get('system')}' "
                  f"diverge do page_title='{event.get('page_title')}' do primeiro evento. "
                  f"Verifique se o sistema está categorizado corretamente.")
    except Exception:
        pass
```

Chamar `_warn_system_title_mismatch(meta, raw_events_path)` no início do fluxo `compile`.

**Teste** `tests/unit/recorder/test_metadata_reconciliation_when_system_vs_title_diverge_then_warns.py`:
```python
@pytest.mark.unit
class TestMetadataReconciliationWhenSystemVsTitleDivergesThenWarns:
    def test_warns_when_system_not_in_title(self, tmp_path, capsys):
        import json
        from testforge.cli.app import _warn_system_title_mismatch

        raw = tmp_path / "raw_events.jsonl"
        raw.write_text(json.dumps({"page_title": "Sistema de Gestão de Honras", "type": "nav"}) + "\n")
        _warn_system_title_mismatch({"system": "GESTAO"}, str(raw))
        out = capsys.readouterr().out
        assert "WARN" in out
        assert "diverge" in out

    def test_no_warn_when_system_in_title(self, tmp_path, capsys):
        import json
        from testforge.cli.app import _warn_system_title_mismatch

        raw = tmp_path / "raw_events.jsonl"
        raw.write_text(json.dumps({"page_title": "SIMULADOR - Login", "type": "nav"}) + "\n")
        _warn_system_title_mismatch({"system": "SIMULADOR"}, str(raw))
        out = capsys.readouterr().out
        assert "WARN" not in out
```

---

### A3: Migração recordings sem taxonomy (REC-79)

**Origem do bug**: 12 recordings em `src/testforge/uncategorized/` foram criados antes do schema de taxonomy. Metadata tem `recording_id`, `application`, `base_url`, `status` mas falta `system/suite/test_case`.

**Confirmar que é bug real**:
```bash
python3 -c "
import json, glob
for p in glob.glob('src/testforge/uncategorized/*/recording_metadata.json'):
    m = json.load(open(p))
    print(p.split('/')[-2], '| system:', m.get('system','MISSING'), '| test_case:', m.get('test_case','MISSING'))
"
```

**Fix em `src/testforge/cli/app.py`** — novo subcomando CLI:

```python
def _cmd_migrate_uncategorized(args) -> None:
    """REC-79: infer system/suite/test_case for recordings without taxonomy."""
    import glob, json
    recordings_root = str(_PROJECT_ROOT / "recordings")
    uncategorized = [
        d for d in glob.glob(f"{recordings_root}/*/recording_metadata.json")
        if True  # will filter below
    ]
    # Also scan src/testforge/uncategorized if exists
    unc_dir = _PROJECT_ROOT / "src" / "testforge" / "uncategorized"
    if unc_dir.exists():
        uncategorized += list(unc_dir.glob("*/recording_metadata.json"))

    needs_migration = []
    for meta_path in uncategorized:
        try:
            meta = json.loads(pathlib.Path(meta_path).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not meta.get("system") and not meta.get("test_case"):
            needs_migration.append((meta_path, meta))

    if not needs_migration:
        print("[TestForge] Nenhum recording sem taxonomy encontrado.")
        return

    print(f"[TestForge] {len(needs_migration)} recordings sem taxonomy:\n")
    for meta_path, meta in needs_migration:
        rec_id = meta.get("recording_id") or pathlib.Path(meta_path).parent.name
        base_url = meta.get("base_url") or ""
        # Infer system from base_url hostname
        from urllib.parse import urlparse
        host = urlparse(base_url).hostname or ""
        inferred_system = host.split(".")[0].upper() if host else ""

        print(f"  Recording: {rec_id}")
        print(f"  base_url:  {base_url}")
        print(f"  Sugestão:  system={inferred_system or '?'} suite=? test_case={rec_id}")

        if not args.dry_run:
            system = input(f"    system [{inferred_system}]: ").strip() or inferred_system
            suite = input(f"    suite: ").strip()
            test_case = input(f"    test_case [{rec_id}]: ").strip() or rec_id
            meta.update({"system": system, "suite": suite, "test_case": test_case})
            pathlib.Path(meta_path).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"    [OK] Atualizado.\n")
        else:
            print(f"    [DRY-RUN] Sem alteração.\n")
```

Registrar no argparser: `sub.add_parser("migrate-uncategorized")` com `--dry-run` flag.

**Teste** `tests/unit/cli/test_migrate_uncategorized_when_missing_taxonomy_then_infers.py`:
```python
@pytest.mark.unit
class TestMigrateUncategorizedWhenMissingTaxonomyThenInfers:
    def test_dry_run_lists_recordings_without_taxonomy(self, tmp_path, capsys):
        import json
        rec = tmp_path / "test_rec"
        rec.mkdir()
        (rec / "recording_metadata.json").write_text(
            json.dumps({"recording_id": "test_rec", "base_url": "https://simulador.des.example/"})
        )
        # Chamar função com mock de _PROJECT_ROOT apontando para tmp_path
        # (ajustar conforme implementação real)
        # Verificar que output menciona "test_rec" e "SIMULADOR"
```

---

### A4: Depreciar `application` field (REC-80)

**Origem do bug**: recordings em `uncategorized/` usam `application` de forma inconsistente — às vezes `"web"` (tipo), às vezes `"SIMULADOR"` (nome do sistema). Dois significados no mesmo campo.

**Confirmar**:
```bash
python3 -c "
import json, glob
for p in glob.glob('src/testforge/uncategorized/*/recording_metadata.json'):
    m = json.load(open(p))
    print(m.get('recording_id','?'), '| application:', m.get('application','?'))
"
```

**Fix em `src/testforge/recorder/recording_session.py`**:

No `RecordingSession.to_dict()`, adicionar aviso se `application` não é um dos valores válidos:

```python
_VALID_APPLICATION_TYPES = {"web", "mobile", "desktop", "api", ""}

def to_dict(self) -> dict:
    d = { ... }  # dict existente
    # REC-80: alert if application is used as system name (legacy misuse)
    if self.application and self.application.lower() not in _VALID_APPLICATION_TYPES:
        import logging
        logging.getLogger(__name__).warning(
            "REC-80: 'application' field contains '%s' which looks like a system name. "
            "Use --system instead. 'application' should be 'web'/'mobile'/'desktop'/'api'.",
            self.application
        )
    return d
```

**Não renomear o campo ainda** (migration breaking). Só alertar. Adicionar `application_type` como alias opcional:

```python
# in RecordingSession dataclass
application_type: str = ""  # enum: web/mobile/desktop/api. Preferred over 'application'.
```

**Teste** `tests/unit/recorder/test_application_field_when_system_name_then_warns.py`:
```python
@pytest.mark.unit
class TestApplicationFieldWhenSystemNameThenWarns:
    def test_warns_when_application_looks_like_system(self, caplog):
        import logging
        from testforge.recorder.recording_session import RecordingSession
        with caplog.at_level(logging.WARNING):
            s = RecordingSession(recording_id="x", application="SIMULADOR")
            s.to_dict()
        assert "REC-80" in caplog.text or "application" in caplog.text.lower()

    def test_no_warn_for_valid_application_type(self, caplog):
        import logging
        from testforge.recorder.recording_session import RecordingSession
        with caplog.at_level(logging.WARNING):
            s = RecordingSession(recording_id="x", application="web")
            s.to_dict()
        assert "REC-80" not in caplog.text
```

---

### A5: Statuses documentados + `needs_review` restaurado (REC-81)

**Origem do bug**: recordings `uncategorized/` usam statuses legados (`needs_review`, `ready_for_team`, `completed`) que desapareceram da doc. O `RecordingStatus` em `recording_status.py` **já define** `needs_review` e `ready_for_team` (linhas 33-40) — o bug é de documentação e de `completed` não estar no enum.

**Confirmar**:
```bash
grep -n "needs_review\|ready_for_team\|completed\b\|intent_complete\|incomplete_intent" src/testforge/recorder/recording_status.py
```
→ `completed` **não existe** no enum atual. Recordings antigos com `status: "completed"` vão falhar no parse.

**Fix em `src/testforge/recorder/recording_status.py`**:

```python
class RecordingStatus(str, Enum):
    # Active statuses
    recording = "recording"
    stopped = "stopped"
    intent_complete = "intent_complete"
    incomplete_intent = "incomplete_intent"
    needs_review = "needs_review"
    ready_for_team = "ready_for_team"
    incremental_validation_running = "incremental_validation_running"
    # Legacy aliases (pre-schema-4 recordings) — read-only, never write
    completed = "completed"            # REC-81: legacy alias for intent_complete
    completed_raw = "completed_raw"    # REC-81: legacy alias for stopped
```

Adicionar método `normalize()` que mapeia legados:

```python
_LEGACY_MAP = {
    "completed": "intent_complete",
    "completed_raw": "stopped",
}

@classmethod
def normalize(cls, value: str) -> "RecordingStatus":
    """Map legacy status strings to current enum values."""
    mapped = cls._LEGACY_MAP.get(value, value)
    try:
        return cls(mapped)
    except ValueError:
        return cls.incomplete_intent  # safe fallback
```

**Teste** `tests/unit/recorder/test_recording_status_when_legacy_completed_then_normalizes.py`:
```python
@pytest.mark.unit
class TestRecordingStatusWhenLegacyCompletedThenNormalizes:
    def test_completed_maps_to_intent_complete(self):
        from testforge.recorder.recording_status import RecordingStatus
        assert RecordingStatus.normalize("completed") == RecordingStatus.intent_complete

    def test_completed_raw_maps_to_stopped(self):
        from testforge.recorder.recording_status import RecordingStatus
        assert RecordingStatus.normalize("completed_raw") == RecordingStatus.stopped

    def test_current_status_unchanged(self):
        from testforge.recorder.recording_status import RecordingStatus
        assert RecordingStatus.normalize("intent_complete") == RecordingStatus.intent_complete

    def test_unknown_status_falls_back(self):
        from testforge.recorder.recording_status import RecordingStatus
        assert RecordingStatus.normalize("unknown_xyz") == RecordingStatus.incomplete_intent
```

**Anti-regressão**: `grep -rn "RecordingStatus(" src/testforge/ tests/` — verificar que nenhum caller passa `"completed"` sem usar `.normalize()`.

---

### A6: Alias `recording_id` → `test_case` backward compat (REC-87)

**Origem do bug**: schema antigo usa `recording_id` como slug. Schema novo usa `test_case`. Código que lê `meta.get("recording_id")` de recordings novos recebe `None`.

**Fix em `src/testforge/recorder/recording_session.py`**:

No `RecordingSession.from_dict()` (ou onde metadata é lida):

```python
@staticmethod
def _read_meta_field(meta: dict, *keys: str, default: str = "") -> str:
    """REC-87: try multiple keys for backward compat (recording_id → test_case)."""
    for k in keys:
        v = meta.get(k)
        if v:
            return str(v)
    return default
```

Usar: `test_case = _read_meta_field(meta, "test_case", "recording_id")`.

**Teste** `tests/unit/recorder/test_recording_id_alias_when_old_schema_then_maps_to_test_case.py`:
```python
@pytest.mark.unit
class TestRecordingIdAliasWhenOldSchemaThenMapsToTestCase:
    def test_recording_id_used_when_test_case_absent(self):
        from testforge.recorder.recording_session import RecordingSession
        meta = {"recording_id": "my_test", "system": "SYS", "suite": "S"}
        tc = RecordingSession._read_meta_field(meta, "test_case", "recording_id")
        assert tc == "my_test"

    def test_test_case_takes_priority_over_recording_id(self):
        from testforge.recorder.recording_session import RecordingSession
        meta = {"recording_id": "old_id", "test_case": "new_id"}
        tc = RecordingSession._read_meta_field(meta, "test_case", "recording_id")
        assert tc == "new_id"
```

---

## Grupo B — Dedup + Sufixo

### B1: Sanitize convention única para caracteres especiais (REC-77)

**Origem do bug**: `_sanitize_name` em `cli/app.py:40-44` usa `re.sub(r'[^a-zA-Z0-9_-]', '_', name)` sem normalização unicode prévia. Strings podem chegar em NFC (`ç` = U+00E7, 1 char → `_`) ou NFD (`ç` = U+0063 + U+0327, 2 chars → `c_`). Resultado: `"terça"` vira `"ter_a"` (NFC) OU `"terc_a"` (NFD) — duas convenções no mesmo codebase.

**Confirmar**:
```python
import unicodedata, re
name = "terça"
# NFC path:
nfc = unicodedata.normalize("NFC", name)
print(re.sub(r'[^a-zA-Z0-9_-]', '_', nfc))   # → "ter_a"
# NFD path:
nfd = unicodedata.normalize("NFD", name)
print(re.sub(r'[^a-zA-Z0-9_-]', '_', nfd))   # → "terc_a"
```

**Fix em `src/testforge/cli/app.py` linhas 40-44**:

```python
import unicodedata

def _sanitize_name(name: str) -> str:
    """Sanitiza nome de teste/gravacao.

    REC-77: normaliza unicode para NFKD antes do regex para garantir convenção única.
    'ç' → 'c', 'á' → 'a', 'ã' → 'a', 'ô' → 'o', etc.
    NFKD decompõe caracteres compostos; bytes ASCII resultantes ficam intactos;
    bytes não-ASCII (combining marks) são filtrados pelo encode/decode roundtrip.
    """
    # Decompose + strip combining chars → pure ASCII letters
    ascii_approx = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    sanitized = _re.sub(r'[^a-zA-Z0-9_-]', '_', ascii_approx)
    sanitized = _re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized or "unnamed"
```

**Teste** `tests/unit/cli/test_sanitize_name_when_cedilha_then_unique_convention.py`:
```python
@pytest.mark.unit
class TestSanitizeNameWhenCedilhaThenUniqueConvention:
    def test_terca_always_produces_terca(self):
        from testforge.cli.app import _sanitize_name
        # Both NFC and NFD input must produce identical output
        import unicodedata
        nfc_input = unicodedata.normalize("NFC", "terça")
        nfd_input = unicodedata.normalize("NFD", "terça")
        assert _sanitize_name(nfc_input) == _sanitize_name(nfd_input)
        assert _sanitize_name("terça") == "terca"

    def test_horario_strips_accent(self):
        from testforge.cli.app import _sanitize_name
        assert _sanitize_name("horário") == "horario"

    def test_cedilha_produces_c_not_underscore(self):
        from testforge.cli.app import _sanitize_name
        # 'ç' must become 'c', not '_'
        result = _sanitize_name("ça")
        assert result == "ca", f"Expected 'ca', got '{result}'"

    def test_ascii_unchanged(self):
        from testforge.cli.app import _sanitize_name
        assert _sanitize_name("login_cpf") == "login_cpf"

    def test_spaces_become_underscore(self):
        from testforge.cli.app import _sanitize_name
        assert _sanitize_name("deve logar") == "deve_logar"
```

**Anti-regressão CRÍTICA**: `_sanitize_name` é usada ao criar recording IDs em disco. Mudança afeta nomes de pastas para recordings novos. Recordings **existentes** não são renomeados. Verificar:
```bash
grep -rn "_sanitize_name" src/testforge/ tests/
```
Todos os callers devem continuar funcionando. Rodar `pytest tests/ -k "sanitize or name or slug" -q`.

---

### B2: Sufixo timestamp único em vez de `_2/_3/_N` (REC-75, REC-76)

**Origem do bug**: `_resolve_name` em `recording_session.py:74-88` gera `base_name_2`, `base_name_3` quando o nome já existe. Resulta em `busca_de_massagem_em_brasilia_2_2` e 2 padrões coexistindo com sufixo timestamp.

**Fix em `src/testforge/recorder/recording_session.py` linhas 74-88**:

```python
def _resolve_name(recordings_root: str, base_name: str) -> str:
    """REC-76: use timestamp suffix instead of _2/_3/_N for duplicate recordings.

    If recordings/{base_name} does not exist, returns base_name.
    Otherwise returns base_name_YYYYMMDD-HHMMSS (UTC).
    """
    if not os.path.isdir(os.path.join(recordings_root, base_name)):
        return base_name
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{base_name}_{stamp}"
```

**Teste** `tests/unit/recorder/test_resolve_name_when_duplicate_then_timestamp_suffix.py`:
```python
@pytest.mark.unit
class TestResolveNameWhenDuplicateThenTimestampSuffix:
    def test_unique_name_returned_unchanged(self, tmp_path):
        from testforge.recorder.recording_session import RecordingSessionManager
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        assert result == "my_test"

    def test_duplicate_gets_timestamp_suffix(self, tmp_path):
        import re
        from testforge.recorder.recording_session import RecordingSessionManager
        (tmp_path / "my_test").mkdir()
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        assert result.startswith("my_test_")
        # Must match YYYYMMDD-HHMMSS
        assert re.match(r"my_test_\d{8}-\d{6}$", result), f"Got: {result}"

    def test_no_incremental_suffix_pattern(self, tmp_path):
        from testforge.recorder.recording_session import RecordingSessionManager
        (tmp_path / "my_test").mkdir()
        result = RecordingSessionManager._resolve_name(str(tmp_path), "my_test")
        # Must NOT produce _2, _3, _4 pattern
        import re
        assert not re.match(r"my_test_\d+$", result), f"Got incremental suffix: {result}"
```

**Anti-regressão**: verificar que `pytest tests/unit/recorder/ -q` ainda passa. O contrato `_resolve_name` é interno; nenhum caller externo depende do sufixo ser `_2`.

---

### B3: Dedup detector de regravação por hash (REC-71, REC-82)

**Origem do bug**: R9 CONSULTA tem 20 recordings, maioria com `raw=18 vm=5` idênticos. User regravou o mesmo teste 3-4x sem detector de duplicata. REC-82 mostra regravações em múltiplos sistemas (AGENDAMENTO, GESTAO, CONSULTA).

**Confirmar**:
```bash
python3 -c "
import json, glob, hashlib

def event_sequence_hash(raw_events_path):
    try:
        events = [json.loads(l) for l in open(raw_events_path) if l.strip()]
        sig = '|'.join(f\"{e.get('type','')},{e.get('target',{}).get('element_id','') if e.get('target') else ''},{e.get('value','')[:20] if e.get('value') else ''}\" for e in events)
        return hashlib.md5(sig.encode()).hexdigest()
    except: return None

hashes = {}
for p in glob.glob('src/testforge/consulta/**/raw_events.jsonl', recursive=True):
    h = event_sequence_hash(p)
    if h:
        hashes.setdefault(h, []).append(p)

for h, paths in hashes.items():
    if len(paths) > 1:
        print('DUPLICATES:', paths)
"
```

**Fix em `src/testforge/cli/app.py`** — novo utilitário e hook no início do `record`:

```python
def _compute_recording_hash(raw_events_path: str) -> str:
    """REC-71/82: compute stable hash of event sequence for duplicate detection."""
    import hashlib
    try:
        events = [json.loads(l) for l in pathlib.Path(raw_events_path).read_text().splitlines() if l.strip()]
        sig_parts = []
        for e in events:
            target = e.get("target") or {}
            sig_parts.append(f"{e.get('type','')},{target.get('element_id','')},{str(e.get('value',''))[:30]}")
        return hashlib.md5("|".join(sig_parts).encode()).hexdigest()
    except Exception:
        return ""


def _check_duplicate_recording(recordings_root: str, new_raw_events_path: str, new_rid: str) -> None:
    """REC-71/82: warn user if identical recording already exists."""
    import glob
    new_hash = _compute_recording_hash(new_raw_events_path)
    if not new_hash:
        return
    for existing in glob.glob(f"{recordings_root}/*/raw_events.jsonl"):
        existing_rid = pathlib.Path(existing).parent.name
        if existing_rid == new_rid:
            continue
        if _compute_recording_hash(existing) == new_hash:
            print(f"\n[TestForge] [WARN] REC-71: Esta gravacao parece idêntica a '{existing_rid}'.")
            print(f"  Sequência de eventos igual. Considere:")
            print(f"    (1) Usar o recording existente e iterar com 'testforge compile'")
            print(f"    (2) Manter esta gravacao se o objetivo for diferente")
            print(f"  Recording existente: recordings/{existing_rid}/")
            break
```

Chamar `_check_duplicate_recording(...)` ao finalizar gravação (após `flush_events`), antes do compile automático.

**Teste** `tests/unit/recorder/test_duplicate_detection_when_same_sequence_then_warns.py`:
```python
@pytest.mark.unit
class TestDuplicateDetectionWhenSameSequenceThenWarns:
    def _write_events(self, path, events):
        import json
        pathlib.Path(path).write_text("\n".join(json.dumps(e) for e in events))

    def test_identical_sequences_produce_same_hash(self, tmp_path):
        from testforge.cli.app import _compute_recording_hash
        events = [{"type": "fill", "target": {"element_id": "cpf"}, "value": "123"}]
        p1 = tmp_path / "raw1.jsonl"
        p2 = tmp_path / "raw2.jsonl"
        self._write_events(str(p1), events)
        self._write_events(str(p2), events)
        assert _compute_recording_hash(str(p1)) == _compute_recording_hash(str(p2))

    def test_different_sequences_produce_different_hash(self, tmp_path):
        from testforge.cli.app import _compute_recording_hash
        p1 = tmp_path / "raw1.jsonl"
        p2 = tmp_path / "raw2.jsonl"
        self._write_events(str(p1), [{"type": "fill", "value": "AAA"}])
        self._write_events(str(p2), [{"type": "fill", "value": "BBB"}])
        assert _compute_recording_hash(str(p1)) != _compute_recording_hash(str(p2))

    def test_check_warns_when_duplicate_found(self, tmp_path, capsys):
        import json, pathlib
        from testforge.cli.app import _check_duplicate_recording
        events = [{"type": "click", "target": {"element_id": "btn"}, "value": None}]
        existing = tmp_path / "existing_rec"
        existing.mkdir()
        (existing / "raw_events.jsonl").write_text(json.dumps(events[0]))
        new_raw = tmp_path / "new_raw.jsonl"
        new_raw.write_text(json.dumps(events[0]))
        _check_duplicate_recording(str(tmp_path), str(new_raw), "new_rec")
        out = capsys.readouterr().out
        assert "WARN" in out or "idêntica" in out
```

---

## Grupo C — recordings_failed Lifecycle

### C1: Banner schema antigo ao compile/run (REC-83)

**Origem do bug**: `deve_logar_no_sifap` em `uncategorized/` (2026-06-26) teve 20/39 steps falhando porque foi gravado com recorder pré-hotfix. O mesmo teste regravado 6 dias depois (R5a) ficou muito melhor. Sem aviso ao usuário de que o recording é de versão obsoleta.

**Confirmar**: recordings sem `capture_schema_version` em metadata = v0 (pre-fingerprint).

**Fix em `src/testforge/cli/app.py`** — no início da função `compile`:

```python
_CURRENT_SCHEMA = 4  # sync with CAPTURE_SCHEMA_VERSION in capture_fingerprint.py

def _warn_old_schema(meta: dict, rec_id: str) -> None:
    """REC-83: alert when recording was created by a significantly older recorder."""
    fingerprint = meta.get("fingerprint") or {}
    schema_version = fingerprint.get("capture_schema_version", 0)
    if schema_version < _CURRENT_SCHEMA:
        print(f"\n[TestForge] [WARN] Recording '{rec_id}' usa schema v{schema_version} "
              f"(atual: v{_CURRENT_SCHEMA}).")
        if schema_version == 0:
            print(f"  Este recording foi criado antes de 2026-06-27 (pré-fingerprint).")
        print(f"  Fixes de captura lançados após esta gravação não estão presentes.")
        print(f"  Se os resultados forem ruins, considere regravar o cenário.")
        print(f"  Para ignorar este aviso: use --no-schema-warn\n")
```

Chamar `_warn_old_schema(meta, rec_id)` no início do fluxo `compile`.

**Teste** `tests/unit/cli/test_old_schema_warning_when_v0_then_banner_shown.py`:
```python
@pytest.mark.unit
class TestOldSchemaWarningWhenV0ThenBannerShown:
    def test_warns_when_no_fingerprint(self, capsys):
        from testforge.cli.app import _warn_old_schema
        _warn_old_schema({}, "my_rec")
        out = capsys.readouterr().out
        assert "WARN" in out
        assert "schema v0" in out or "pré-fingerprint" in out

    def test_warns_when_schema_older(self, capsys):
        from testforge.cli.app import _warn_old_schema
        _warn_old_schema({"fingerprint": {"capture_schema_version": 2}}, "my_rec")
        out = capsys.readouterr().out
        assert "WARN" in out

    def test_no_warn_when_current_schema(self, capsys):
        from testforge.cli.app import _warn_old_schema
        _warn_old_schema({"fingerprint": {"capture_schema_version": 4}}, "my_rec")
        out = capsys.readouterr().out
        assert "WARN" not in out
```

---

### C2: Alerta QA ao mover para recordings_failed + mensagem de recuperação (REC-88)

**Origem do bug**: `_mark_failed_recording` em `cli/app.py:317-343` copia o recording para `recordings_failed/` mas imprime apenas `"[FAIL] Gravacao marcada como falha: recordings_failed/{target.name}/"`. QA não sabe como iterar sobre o recording sem regravar.

**Fix em `cli/app.py`** — ampliar a mensagem em `_mark_failed_recording`:

```python
# Após o print atual:
print(f"[TestForge] [FAIL] Gravacao marcada como falha: recordings_failed/{target.name}/")
# Adicionar:
print(f"\n[TestForge] Para iterar sobre esta gravação sem regravar:")
print(f"  testforge compile {rid} --check    # ver o que está faltando")
print(f"  testforge compile {rid} --data     # recompilar com dados separados")
print(f"  (Não é necessário regravar — itere sobre compile + run)")
print(f"\n[TestForge] Recording preservado em: recordings_failed/{target.name}/")
print(f"  FAILED_MARKER.json explica o motivo da falha.\n")
```

**Teste** `tests/unit/cli/test_mark_failed_when_incomplete_then_shows_recovery_hint.py`:
```python
@pytest.mark.unit
class TestMarkFailedWhenIncompleteThenShowsRecoveryHint:
    def test_prints_recovery_hint(self, tmp_path, capsys, monkeypatch):
        import json
        from testforge.cli import app as cli_app

        # Setup fake recording dir
        rec_dir = tmp_path / "recordings" / "my_rec"
        rec_dir.mkdir(parents=True)
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec_dir / "raw_events.jsonl").write_text("")

        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        cli_app._mark_failed_recording(str(rec_dir), "my_rec")
        out = capsys.readouterr().out
        assert "compile" in out.lower()
        assert "regravar" in out.lower() or "itere" in out.lower()
```

---

### C3: Link entre recordings_failed e canonical via `previous_attempt_id` (REC-90)

**Origem do bug**: R11 mostra `recordings_failed/as_de_sexta_20260703-202821` e `consulta/as_de_sexta` — mesmo teste, dois artefatos sem link. Analytics conta 2x.

**Fix em `_mark_failed_recording`** — adicionar `canonical_recording_id` no FAILED_MARKER:

```python
marker = {
    "recording_id": rid,
    "reason": reason,
    "source_dir": rel_source,
    "failed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    # REC-90: permite link de "esta gravação foi substituída por <id>"
    "superseded_by": None,  # caller pode preencher depois via update
}
```

Adicionar CLI `testforge link-failed <failed_id> <canonical_id>` que atualiza `FAILED_MARKER.json`:

```python
def _cmd_link_failed(args) -> None:
    """REC-90: link a failed recording to its canonical replacement."""
    failed_path = _PROJECT_ROOT / "recordings_failed" / args.failed_id / "FAILED_MARKER.json"
    if not failed_path.exists():
        print(f"[TestForge] FAILED_MARKER não encontrado: {failed_path}")
        return
    marker = json.loads(failed_path.read_text(encoding="utf-8"))
    marker["superseded_by"] = args.canonical_id
    failed_path.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[TestForge] {args.failed_id} → superseded_by={args.canonical_id}")
```

**Teste** `tests/unit/cli/test_failed_marker_when_linked_then_superseded_by_set.py`:
```python
@pytest.mark.unit
class TestFailedMarkerWhenLinkedThenSupersededBySet:
    def test_link_failed_updates_marker(self, tmp_path, monkeypatch):
        import json, argparse
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        failed_dir = tmp_path / "recordings_failed" / "rec_old_20260703-202821"
        failed_dir.mkdir(parents=True)
        (failed_dir / "FAILED_MARKER.json").write_text(
            json.dumps({"recording_id": "rec_old", "superseded_by": None})
        )
        args = argparse.Namespace(failed_id="rec_old_20260703-202821", canonical_id="rec_new")
        cli_app._cmd_link_failed(args)
        marker = json.loads((failed_dir / "FAILED_MARKER.json").read_text())
        assert marker["superseded_by"] == "rec_new"
```

---

### C4: README em recordings_failed (REC-91)

**Origem do bug**: pasta `recordings_failed/` existe mas sem README. QA não sabe o que fazer.

**Fix**: ao criar `recordings_failed/` pela primeira vez em `_mark_failed_recording`, criar README:

```python
_FAILED_README = """# recordings_failed/

Esta pasta contém gravações que falharam na validação ou foram marcadas como incompletas.

## Por que um recording acaba aqui?

O pipeline detecta `status: incomplete_intent` (campos sem resolver) e move o recording
para cá automaticamente, preservando todos os artefatos para debugging.

## Como recuperar uma gravação?

NÃO é necessário regravar. Itere sobre o recording existente:

```bash
# Ver o que está faltando:
testforge compile <recording_id> --check

# Recompilar após corrigir:
testforge compile <recording_id>

# Linkar ao recording canonical que substituiu este:
testforge link-failed <failed_id> <canonical_id>
```

## Posso deletar esta pasta?

Sim, se não precisar mais dos artefatos. Os recordings em `recordings/` não são afetados.
"""

def _mark_failed_recording(...):
    ...
    failed_root.mkdir(parents=True, exist_ok=True)
    readme = failed_root / "README.md"
    if not readme.exists():  # REC-91: criar apenas uma vez
        readme.write_text(_FAILED_README, encoding="utf-8")
    ...
```

**Teste** `tests/unit/cli/test_recordings_failed_when_first_failure_then_readme_created.py`:
```python
@pytest.mark.unit
class TestRecordingsFailedWhenFirstFailureThenReadmeCreated:
    def test_readme_created_on_first_move(self, tmp_path, monkeypatch):
        import json
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        cli_app._mark_failed_recording(str(rec), "my_rec")
        readme = tmp_path / "recordings_failed" / "README.md"
        assert readme.exists()
        assert "testforge compile" in readme.read_text()
```

---

### C5: Prune de artifacts pesados ao mover para failed (REC-92)

**Origem do bug**: `_mark_failed_recording` usa `shutil.copytree` — copia TUDO incluindo `ax_snapshots/`, `dom_snapshots/`, `_pilot_runs/`, `_pilot_tmp/`. Esses podem ter centenas de arquivos.

**Fix em `_mark_failed_recording`**: após copytree, deletar dirs derivados:

```python
# REC-92: prune heavy derived artifacts from failed copy — keep only essentials
_PRUNE_DIRS = ["ax_snapshots", "dom_snapshots", "_pilot_runs", "_pilot_tmp",
               "screenshots", "trace.zip"]
for name in _PRUNE_DIRS:
    artifact = target / name
    if artifact.is_dir():
        shutil.rmtree(artifact, ignore_errors=True)
    elif artifact.is_file():
        artifact.unlink(missing_ok=True)
```

**Teste** `tests/unit/cli/test_failed_recording_when_moved_then_artifacts_pruned.py`:
```python
@pytest.mark.unit
class TestFailedRecordingWhenMovedThenArtifactsPruned:
    def test_dom_snapshots_removed_after_move(self, tmp_path, monkeypatch):
        import json, shutil
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text("")
        (rec / "dom_snapshots").mkdir()
        (rec / "dom_snapshots" / "snap_001.html").write_text("<html/>")
        cli_app._mark_failed_recording(str(rec), "my_rec")
        failed = list((tmp_path / "recordings_failed").glob("my_rec*"))
        assert failed, "No failed dir created"
        assert not (failed[0] / "dom_snapshots").exists()

    def test_raw_events_preserved_after_move(self, tmp_path, monkeypatch):
        import json
        from testforge.cli import app as cli_app
        monkeypatch.setattr(cli_app, "_PROJECT_ROOT", tmp_path)
        rec = tmp_path / "recordings" / "my_rec"
        rec.mkdir(parents=True)
        (rec / "recording_metadata.json").write_text(json.dumps({"recording_id": "my_rec"}))
        (rec / "raw_events.jsonl").write_text('{"type":"nav"}')
        cli_app._mark_failed_recording(str(rec), "my_rec")
        failed = list((tmp_path / "recordings_failed").glob("my_rec*"))
        assert (failed[0] / "raw_events.jsonl").exists()
```

---

## Ordem de commit

```
1. feat(taxonomy): support 4th level scenario field in RecordingSession
2. feat(taxonomy): warn when metadata.system diverges from page_title
3. feat(cli): migrate-uncategorized command with taxonomy inference
4. fix(recorder): deprecate application field ambiguity — warn + application_type alias
5. fix(status): add legacy completed/completed_raw to RecordingStatus enum + normalize()
6. fix(recorder): backward compat recording_id → test_case alias
7. fix(sanitize): unicode NFKD normalization in _sanitize_name (ç→c, ã→a)
8. fix(recorder): timestamp suffix in _resolve_name instead of _2/_3/_N
9. feat(recorder): duplicate recording detection by event sequence hash
10. feat(cli): banner when recording uses old capture schema (v0 < v4)
11. feat(cli): expand recordings_failed message with recovery hints
12. feat(cli): link-failed command to set superseded_by in FAILED_MARKER
13. feat(cli): auto-create README.md in recordings_failed on first use
14. fix(cli): prune heavy artifacts (dom_snapshots, ax_snapshots) when moving to failed
```

---

## Sanity gates

Antes de cada commit:
```bash
pytest -m "unit or contract or regression" -q
```
Deve terminar: **346+ passed, 1 xfailed** (0 failures).

Ao final da fase inteira:
```bash
pytest tests/ -q --ignore=tests/e2e
```

Regressões específicas a verificar:
```bash
# _sanitize_name afeta nomes de pastas — verificar que testes de recording ainda passam
pytest tests/unit/recorder/ tests/regression/recording/ -q

# RecordingStatus enum — verificar que status history ainda funciona
pytest tests/ -k "status" -q

# _resolve_name — verificar que manager.start() ainda funciona
pytest tests/unit/recorder/ -k "session" -q
```
