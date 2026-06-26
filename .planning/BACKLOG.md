# TestForge Backlog

Pós-Sprint 0 hotfixes. Decisões: branch `hotfix/sprint-0-recorder-fixes`, 2026-06-25.

## Curto prazo — estabilizar antes de liberar piloto QA

| ID | Item | Esforço | Status |
|---|---|---|---|
| A | Fix DX `run-incremental` — aceitar diretório, auto-resolver `test_*.py` | pequeno | pending |
| B | Repro hotfix 7 (XHR pseudo-submit) com fluxo de submit real local | pequeno | pending |
| C | Bug `test_step_executor::_execute_select` ausente — 2 testes vermelhos | pequeno | pending |
| D | Smoke E2E completo (record → compile → run-incremental) fluxo controlado | pequeno | pending |
| H1 | Browser-close = graceful stop (page/context `on('close')` → mesmo path Shift+S) | pequeno | pending |
| H2 | Final `--complete` prompt enriquecido — mostrar label + neighboring text + screenshot crop para usuário identificar campo | médio | pending |

## Médio prazo — piloto QA + telemetria

| ID | Item | Esforço | Status |
|---|---|---|---|
| E | Liberar branch para QA com diagnostic mode ligado | — | bloqueado por A-D, H1, H2 |
| F | Dashboard `.testforge/spans.jsonl` — heals L0/L1/L2/L3 por sessão, % asserts pass | médio | pending |
| H3 | Inline overlay prompt — quando capture_quality detecta `typing_not_captured` mid-recording, abrir modal no overlay com ícone de atenção e input para usuário preencher valor faltante | médio | pending |
| T1 | Pesquisa: quais dados de telemetria respondem "consegui gerar teste resiliente self-healing em ambiente multi-framework?" | pequeno | in_progress (research agent) |

## Longo prazo — gaps de pesquisa state-of-the-art

Fonte: `.planning/research-modern-healing-tools.md`.

| ID | Gap | Inspiração | Esforço |
|---|---|---|---|
| G1 | YAML AX-tree snapshot por step (input do LLM) | Playwright MCP | médio |
| G2 | `LocatorCandidate` → super-selector tuple `(role, name, AX path, backendNodeId, CSS, XPath, confidence)` | browser-use + Testim | grande |
| G3 | Per-locator stability score no `readiness_report` | Testim | pequeno |
| G4 | Ancestor-N-levels context por elemento | mabl | médio |
| G5 | Heal events com *why healed* (qual atributo mudou) | Healenium | pequeno |
| G6 | Re-extract só do seletor quebrado (não full re-discovery) | arXiv 2603.20358 | médio |
| G7 | Intent-text como cache key de L0 | Stagehand | médio |

Priorização sugerida pós-piloto: G1 → G5 → G3 → G7 → G4 → G6 → G2 (G2 depende de G1+G4).

## Decisões registradas

- **Q1** (2026-06-25): fechar A-C antes de liberar.
- **Q2** (2026-06-25): adicionar telemetria. Pesquisa T1 em andamento.
- **Q3** (2026-06-25): aguardar dados do piloto antes de atacar gaps G1-G7.
- **Q4** (2026-06-25): validar fluxo XHR/postback (item B) localmente antes de QA.
