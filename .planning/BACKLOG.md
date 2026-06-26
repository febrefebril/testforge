# TestForge Backlog

Pós-Sprint 0 hotfixes. Decisões: branch `hotfix/sprint-0-recorder-fixes`, 2026-06-25.

> **Leitura obrigatória antes de propor refactor**: [DECISIONS-LOG.md](DECISIONS-LOG.md).
> **Leitura obrigatória antes de hotfix**: [REGRESSION-PATTERNS.md](REGRESSION-PATTERNS.md).
> **Inventário de débito estrutural**: [DEBT-INVENTORY.md](DEBT-INVENTORY.md).
> **Plano ativo**: [CONSOLIDATION-SPRINT.md](CONSOLIDATION-SPRINT.md).
> **Próximo plano**: [REFACTOR-SPRINT.md](REFACTOR-SPRINT.md) (após piloto).
> **Invariantes enforced em CI**: [tests/test_invariants.py](../tests/test_invariants.py).

## Curto prazo — estabilizar antes de liberar piloto QA

| ID | Item | Esforço | Status |
|---|---|---|---|
| A | Fix DX `run-incremental` — aceitar diretório, auto-resolver `test_*.py` | pequeno | shipped (hotfix 8) |
| B | Repro hotfix 7 (XHR pseudo-submit) com fluxo de submit real local | pequeno | shipped (hotfix 12) |
| C | Bug `test_step_executor::_execute_select` ausente — 2 testes vermelhos | pequeno | shipped (hotfix 9) |
| D | Smoke E2E completo (record → compile → run-incremental) fluxo controlado | pequeno | shipped (hotfix 13) |
| H1 | Browser-close = graceful stop (page/context `on('close')` → mesmo path Shift+S) | pequeno | shipped (hotfix 10) |
| H2 | Final `--complete` prompt enriquecido — mostrar label + neighboring text + screenshot crop para usuário identificar campo | médio | shipped (hotfix 11) |
| H4 | Shift+S overlay UX — banner muda imediato, browser fecha antes do Gherkin prompt | pequeno | shipped (hotfix 14) |
| P1 | Recordings + IncrementalRunner ancorados em `_PROJECT_ROOT`, finalize tolerante a page fechada | pequeno | shipped (hotfix 15) |
| F1 | Fill helpers em `step_executor.py` — clear before type + raw digits + date mask | médio | shipped (hotfix 16) |
| F2 | Currency mask por placeholder além de attribute | pequeno | shipped (hotfix 17) |

## Sprint de consolidação — bloqueia piloto até concluir

Detalhes: [CONSOLIDATION-SPRINT.md](CONSOLIDATION-SPRINT.md).

| ID | Item | Esforço | Status |
|---|---|---|---|
| CS-1 | Consolidar 4 fill helpers em `_fill_masked` único | 3-4h | pending |
| CS-2 | Pinar fixture Material currency/date mask sem `currencymask` attr | 2-3h | pending |
| CS-3 | Path telemetry — span `fill.attempted` com `fill_path`, `mask_detect` | 1h | pending |
| CS-4a | Investigar `fill [FAIL]` em valores `--complete` (divergência label record vs runtime) | 1h | pending |
| CS-4b | Backlog ou fix: file upload `C:\fakepath\` — capturar real path via `page.on('filechooser')` | 1h cap | pending |

## Médio prazo — piloto QA + telemetria

| ID | Item | Esforço | Status |
|---|---|---|---|
| E | Liberar branch para QA com diagnostic mode ligado | — | bloqueado por CS-1..CS-3 |
| F | Dashboard `.testforge/spans.jsonl` — heals L0/L1/L2/L3 por sessão, % asserts pass | médio | pending |
| H3 | Inline overlay prompt — quando capture_quality detecta `typing_not_captured` mid-recording, abrir modal no overlay com ícone de atenção e input para usuário preencher valor faltante | médio | pending |
| H5 | File upload — capturar real path via `page.on('filechooser')`, copiar para `recordings/<rid>/uploads/`, runner usa `set_input_files` | médio | pending — CS-4b time-boxed out, design abaixo |

### H5 — File upload design (CS-4b spillover)

Pesquisa em git history (`git log -S "set_input_files"` etc.) confirmou: implementação anterior **nunca existiu no source**. Apenas `bug_lab/tests/test_bug_file_input.py` (commit `38d4966`) demonstrou o bug, mas o fix em recorder/compiler nunca pousou.

**Problema técnico**: HTML5 file input expõe `value="C:\fakepath\name.ext"` por segurança. JS não vê o path real. Headed Playwright também não — `FileChooser` event dá o input element mas `chooser.set_files()` é input-only (replay), não output (read).

**Solução proposta** (alinha com fluxo --complete existente):

1. **Recorder** (`recorder_controller.py`):
   - Atacha `page.on('filechooser')` quando inicia sessão
   - Quando dispara, emite `raw_event{ type: "file_upload", target: <input>, file_name: chooser.element + JS read of files[0].name, no_path: true }`
   - Marca step como `missing_fill` com `value_kind="file"`

2. **Normalizer** (`recording_normalizer.py`):
   - Reconhece `value_kind=file`
   - Emite step com `action="set_input_files"` + `target=input` + `value="<file_name>"`
   - field_value_map entry com `source=missing_fill`, `intention=upload <name>`

3. **`--complete` prompt** (`_interactive_completion.py`):
   - Para campos com `value_kind=file`: prompt diferente — "Caminho do arquivo para '<file_name>':" + glob support
   - Copia arquivo para `recordings/<rid>/uploads/<basename>`
   - field_value_map armazena `value=<basename>`

4. **Compiler** (`semantic/compiler.py`):
   - Quando step.action == "set_input_files": emite `page.set_input_files(selector, "recordings/<rid>/uploads/<basename>")`

5. **Runner** (`step_executor.py`):
   - Adiciona `_execute_set_input_files(step, selector)` que chama `page.set_input_files`

6. **Fixture pinned**: `tests/test_pages/file_upload/index.html` + `tests/test_runner_file_upload.py`

Esforço: 1-2 dias. Bloqueia QA piloto se sistema sob teste usa uploads. SIOPI Caixa não usa upload no fluxo testado — pode aguardar refactor sprint.
| T1 | Pesquisa: quais dados de telemetria respondem "consegui gerar teste resiliente self-healing em ambiente multi-framework?" | pequeno | shipped — ver TELEMETRY-PLAN.md |

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

Histórico vivo em [DECISIONS-LOG.md](DECISIONS-LOG.md).

- **Q1** (2026-06-25): fechar A-C antes de liberar.
- **Q2** (2026-06-25): adicionar telemetria. Pesquisa T1 concluída (`TELEMETRY-PLAN.md`).
- **Q3** (2026-06-25): aguardar dados do piloto antes de atacar gaps G1-G7.
- **Q4** (2026-06-25): validar fluxo XHR/postback (item B) localmente antes de QA.
- **Q5** (2026-06-26): pausar novos hotfixes pontuais após hotfix 17. Rodar sprint de consolidação (`CONSOLIDATION-SPRINT.md`) que ataca a causa estrutural: 4 fill helpers duplicados em `step_executor.py`. Piloto bloqueado até CS-1..CS-3 verde.
- **Q6** (2026-06-26): codegen do Playwright não substitui recorder (perde captura de masked inputs + asserts + ranking). Copiar cadeia de prioridade dele em G2 — separado, pós-piloto.
- **Q7** (2026-06-26): inventariar débito estrutural em `DEBT-INVENTORY.md`. Após sprint de consolidação + piloto, rodar sprint de refactor (`REFACTOR-SPRINT.md`) atacando P1 (collapse stop/finalize, paths module, @tolerate policy, kill click→fill magic, stable step_id, RecorderController/overlay JS/Normalizer splits, LocatorStrategy enum). Tudo P2/P3 fica pra depois de dados do piloto.
