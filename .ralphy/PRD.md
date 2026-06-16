# TestForge Bug Fix Sprint — P0 Priority

## Task 1: BUG-001 — `<select>` gera seletor de `<input>`
Verify that the bug exists: compile a recording with `<select>` elements and check that script generates `page.fill()` instead of `page.select_option()`. Then fix by updating compiler `_generate` to detect tag="select" and route to `_gen_select`. Run `pytest tests/ -q` to verify no regression.

## Task 2: BUG-002 — DOM snapshots com 0 bytes
Verify that `dom_snapshots/*.html` files have 0 bytes. Fix by adding content validation in `EvidenceCollector.capture_dom()`. Run tests.

## Task 3: BUG-003 — Contagem de passos divergente
Fix the step counters in `cmd_record`, `cmd_compile`, `cmd_run` to show separate counts for raw events, semantic steps, and asserts.

## Task 4: BUG-004 — event_id reinicia após navegação
Make event_id monotonic within a recording session.

## Task 5: BUG-005 — Sessões diferentes anexadas
Prevent `record --name X` from silently appending to existing recordings. Create incremental suffix.

## Task 6: BUG-006 — Browser bloqueado sem fallback
Add `--browser edge|chrome|chromium` flag and fallback chain for corporate environments.

## Task 7: BUG-007 — Tela pisca no SIMAX
Distinguish click vs submit vs postback in recorder.

## Task 8: BUG-008 — Digitação caractere por caractere
Compact sequential fill events for the same selector.

## Task 9: BUG-009 — goto() excessivo no script
Remove redundant `page.goto()` calls from generated scripts.

## Task 10: BUG-010 — Healer genérico
Penalize generic text selectors like `text=Selecione`.

## Task 11: BUG-011 — Métricas inconsistentes
Separate healing metrics into tried/applied/validated/rejected.

## Task 12: BUG-012 — Assertions frágeis
Prefer semantic assertions over long CSS chains.

## Task 13: BUG-013 — Bounding box zero
Validate element actionability before accepting as target.

## Task 14: BUG-014 — httpx ausente
Add httpx to project dependencies.

## Task 15: BUG-015 — URL com & no PowerShell
Add URL validation and PowerShell warning.

## Task 16: BUG-016 — Logs truncados
Save full execution report to file.

## Task 17: BUG-017 — Steps pulados não explicados
Log skip reason for every omitted step.

## Task 18: BUG-018 — Sem artefato semântico
Generate semantic_steps.jsonl alongside script.

## Task 19: BUG-019 — Falha em cascata
Add step dependency tracking (blocking/depends_on).

## Task 20: BUG-020 — Contrato instável
Document contract between raw_events, steps, and semantic_steps.
