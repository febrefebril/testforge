# Sprint Planning — TestForge v0.2.0

**Data:** 2026-06-13
**Duracao:** 1 sprint
**Objetivo:** CLI installavel + pipeline run integrada + demo healing real

---

## Sprint 8: CLI + Pipeline Integrada

### US-07.01: CLI Entry Point
**Tarefas:**
- [ ] T-07.01.01 — Atualizar `pyproject.toml` com `[project.scripts]`
- [ ] T-07.01.02 — `testforge = "testforge.cli.app:main"`
- [ ] T-07.01.03 — `pip install -e .` → comando `testforge` disponivel
- [ ] T-07.01.04 — `testforge --help` mostra comandos

### US-07.02: Comando Record
**Tarefas:**
- [ ] T-07.02.01 — `testforge record <url>` funcional
- [ ] T-07.02.02 — Flags: `--name`, `--app`, `--headless`
- [ ] T-07.02.03 — Overlay + keyboard shortcuts ativos
- [ ] T-07.02.04 — Artefatos salvos em `recordings/{name}/`

### US-07.03: Comando Compile
**Tarefas:**
- [ ] T-07.03.01 — `testforge compile <recording_id>` funcional
- [ ] T-07.03.02 — Flag: `--output` para diretorio de saida
- [ ] T-07.03.03 — Script gerado em `semantic_tests/`

### US-07.04: Comando Run
**Tarefas:**
- [ ] T-07.04.01 — `testforge run <script>` funcional
- [ ] T-07.04.02 — Executa script Playwright com fallback loop
- [ ] T-07.04.03 — Se falhar, tenta candidatos do MIS
- [ ] T-07.04.04 — Classifica falha com FailureClassifier
- [ ] T-07.04.05 — OracleRunner valida resultado
- [ ] T-07.04.06 — Metricas registradas

### US-07.05: Pipeline Completa
**Tarefas:**
- [ ] T-07.05.01 — `testforge pipeline <url>`: record → compile → run
- [ ] T-07.05.02 — Output: metricas, oracles, gate decision
- [ ] T-07.05.03 — Relatorio final

### US-07.06: Demo Healing Real
**Tarefas:**
- [ ] T-07.06.01 — Gravar fluxo CPF no fake-bank
- [ ] T-07.06.02 — Alterar ID do botao (mutation change_id)
- [ ] T-07.06.03 — Executar script → fallback encontra candidato alternativo
- [ ] T-07.06.04 — Oracle valida resultado
- [ ] T-07.06.05 — Gate promove se oracles passarem
- [ ] T-07.06.06 — Metricas mostram healing bem-sucedido

---

## Sprint 9: Prompt Pack GSD

### US-08.05: Prompt Pack
**Tarefas:**
- [ ] T-08.05.01 — Criar `.planning/prompt-pack-v0.2.0.md`
- [ ] T-08.05.02 — Prompts para cada sprint (record, compile, run)
- [ ] T-08.05.03 — Prompt de code review
- [ ] T-08.05.04 — Prompt de verificacao

---

## Criterios de Aceite da Sprint

- [ ] `pip install -e .` instala comando `testforge`
- [ ] `testforge record http://localhost:8765` grava fluxo
- [ ] `testforge compile REC-001` gera script valido
- [ ] `testforge run semantic_tests/test_*.py` executa com healing
- [ ] Demo: gravar → quebrar seletor → healing corrige
- [ ] 100% testes passando
