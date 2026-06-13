# TestForge — Prompt Pack GSD v0.2.0

Prompts para guiar agentes GSD no desenvolvimento do TestForge.
Use com `/gsd-plan-phase` e `/gsd-execute-phase`.

---

## Prompt Base (todas as sessoes)

```text
Voce e um agente de desenvolvimento trabalhando no projeto TestForge v0.2.0.

Contexto:
TestForge e uma ferramenta CLI Python que grava fluxos de usuario em paginas web
e gera scripts Playwright com self-healing deterministico.
Zero dependencia de LLM no caminho critico.

Stack: Python 3.10+, Playwright, Typer, YAML, JSONL, pytest

Arquitetura (9 modulos em src/testforge/):
- recorder/  → Gravacao via JS injection + Playwright nativo
- evidence/  → Coleta de evidencias (JSONL, sem SQLite)
- semantic/  → MIS (RecordingNormalizer) + Compiler Playwright
- oracle/    → OracleRunner (visual_dom, business_state)
- promotion/ → PromotionGate (experimental, shadow_validated, rejected)
- taxonomy/  → FailureClassifier (11 codigos, 6 familias)
- runner/    → FallbackRunner + ShadowValidator
- metrics/   → MetricsRepository (precision, false_heal_rate)
- cli/       → Comandos: record, compile, run, pipeline, demo-heal

Principios:
1. Deterministico primeiro — LLM apenas como curador, off critical path
2. SemanticTestCase YAML e fonte de verdade — script Python e derivado
3. JSONL + filesystem — zero SQLite no MVP
4. Playwright nativo — sem extensao browser
5. Todo codigo tem teste — pytest obrigatorio

Restricoes:
- NAO usar LLM para gerar/corrigir seletores no caminho principal
- NAO adicionar dependencias sem discutir
- NAO alterar a arquitetura sem ADR
- Todo commit segue conventional commits (hook bloqueia fora do padrao)
- Rodar `python -m pytest tests/ -q` antes de commitar

Diretorios:
- src/testforge/       → Codigo fonte
- tests/               → Testes pytest
- scripts/             → Scripts auxiliares (demo.py, test_all.py, stress_test.py)
- docs/                → Documentacao e diagramas PlantUML
- recordings/          → Sessoes de gravacao (gitignored)
- evidence/            → Evidencias de execucao (gitignored)
- semantic_tests/      → Contratos semanticos gerados (gitignored)
- generated_tests/     → Scripts Playwright gerados (gitignored)
- conhecimento_ancestral/ → Documentacao das 4 tentativas anteriores
- .planning/           → Planejamento GSD
```

---

## Prompt: Implementar Feature no Recorder

```text
Tarefa: Implementar melhoria no Recorder Sensorial.

Modulo: src/testforge/recorder/

O que existe:
- RecorderController com JS injection (add_init_script)
- Eventos: click, fill, navigation
- Comandos: Shift+P (pause), Shift+S (stop), Shift+A (assert)
- 4 tipos de assert: textual, estado, visivel, automatico
- Artefatos: raw_events.jsonl, steps.jsonl, screenshots, DOM snapshots

O que fazer:
[DESCREVER A FEATURE AQUI]

Validacao:
- Testes em tests/test_recorder_unit.py e tests/test_recorder_e2e.py
- Rodar: python -m pytest tests/test_recorder_unit.py tests/test_recorder_e2e.py -v
- Rodar demo: python scripts/demo.py --headless
- Verificar artefatos em recordings/

Nao esquecer:
- Atualizar CHANGELOG.md
- Commitar com mensagem conventional commit
```

---

## Prompt: Implementar Feature no Compiler/Runner

```text
Tarefa: Implementar melhoria no Compiler ou Runner.

Modulos: src/testforge/semantic/ (compiler), src/testforge/runner/ (fallback)

O que existe:
- RecordingNormalizer: raw events → SemanticTestCase
- PlaywrightCompiler: gera script Python com fallback loop
- FallbackRunner: deterministico, timeout 2s por candidato
- ShadowValidator: sugere healing, nao aplica
- FailureClassifier: 11 codigos em 6 familias

O que fazer:
[DESCREVER A FEATURE AQUI]

Validacao:
- Testes em tests/test_semantic.py e tests/test_taxonomy_runner.py
- Rodar: testforge compile <RECORDING_ID>
- Verificar script gerado compila
- Rodar: testforge pipeline http://localhost:8765 --headless
- Rodar: testforge demo-heal --headless

Nao esquecer:
- Atualizar diagramas em docs/diagramas/ se arquitetura mudar
- Atualizar CHANGELOG.md
- Commitar com mensagem conventional commit
```

---

## Prompt: Code Review

```text
Tarefa: Revisar codigo da ultima implementacao.

Verifique:
1. Testes passam? pytest tests/ -q
2. Pipeline funciona? testforge pipeline http://localhost:8765 --headless
3. Demo healing funciona? testforge demo-heal --headless
4. Testes novos cobrem a feature?
5. Codigo segue os principios (deterministico, sem LLM, sem SQLite)?
6. CHANGELOG atualizado?
7. Diagramas atualizados se arquitetura mudou?
8. Nomes de variaveis/funcoes em portugues claro?
9. Sem secrets ou credenciais no codigo?
10. Imports organizados (stdlib → third-party → testforge)?

Entregue:
- Lista de problemas encontrados
- Correcoes necessarias
- Decisao: APROVADO ou REJEITADO
```

---

## Prompt: Verificacao de Milestone

```text
Tarefa: Verificar milestone concluido.

Artefatos para verificar:
1. .planning/phases/{N}-{nome}/PLAN.md — plano existe?
2. .planning/phases/{N}-{nome}/DISCUSSION.md — decisoes documentadas?
3. src/testforge/ — codigo implementado?
4. tests/ — testes escritos e passando?
5. docs/diagramas/ — diagramas atualizados?
6. CHANGELOG.md — entrada adicionada?

Checklist:
- [ ] python -m pytest tests/ -q (todos passam)
- [ ] python scripts/test_all.py (26 checks)
- [ ] testforge pipeline http://localhost:8765 --headless
- [ ] git status (working tree limpo?)
- [ ] git log --oneline -3 (commits convencionais?)

Atualizar:
- .planning/STATE.md com status do milestone
- CHANGELOG.md com entrada da versao

Entregue:
- Relatorio de verificacao
- Problemas encontrados (se houver)
- Decisao: APROVADO ou REQUER CORRECOES
```
