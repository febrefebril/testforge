# Documentação TestForge v0.4.0

Índice navegável com links e descrições. Comece pela seção que se aplica a você.

---

## Novo por Aqui?

- [OVERVIEW.md](OVERVIEW.md) — Visão geral do TestForge em 5 minutos: o que é, como funciona, as 4 fases

---

## Para Testers / Usuários Finais

Guias para usar o TestForge no dia a dia:

- [Quick Start](USER-GUIDE/QUICK-START.md) — Grave seu primeiro teste em 5 minutos (instalação + gravação + execução)
- [Guia Completo de Gravação](USER-GUIDE/GRAVAR-FLUXO.md) — Como gravar fluxos, atalhos, asserts, envio de gravações
- [Troubleshooting](USER-GUIDE/TROUBLESHOOTING.md) — Problemas comuns e soluções

---

## Tutoriais

Aprenda com exemplos práticos:

- [LLM Self-Healing](TUTORIAIS/llm-healing.md) — Healing automático L0-L3: gravar, compilar, testar healing com e sem LLM real
- [Debugging Fase B](TUTORIAIS/debugging-fase-b.md) — Runbook para depurar field_values ausentes, blind_spots, máscaras JS
- [Execução Incremental](TUTORIAIS/incremental-runner.md) — Runner passo a passo: arquitetura, estados de step, CLI

---

## Arquitetura (Para Desenvolvedores)

Entenda como o TestForge funciona internamente:

- [Fases A-D](ARQUITETURA/FASES.md) — Visão geral do pipeline: Recorder, Intent Reconstructor, Compiler, Executor+Healer
- [Diagramas PlantUML](diagramas/) — 14 diagramas C4, componentes, classes, estados, sequências (`.puml` + `.png`)
- [Versionamento de Diagramas](DIAGRAMAS/DIAGRAMA-VERSIONING.md) — Política de versionamento e sincronização código-diagrama

---

## Referência Rápida

Consulte informações específicas:

- [Bugs Conhecidos e Resolvidos](REFERENCIA/BUGS-KNOWNS.md) — 5 bugs corrigidos, 20 bugs abertos (P0/P1/P2), limitações
- [Governance e Processo](REFERENCIA/GOVERNANCE.md) — Pipeline oficial, regras, artefatos obrigatórios, quality gates
- [Decisões de Arquitetura (ADRs)](REFERENCIA/ADR-INDEX.md) — Índice de ADRs e matriz de decisões técnicas

---

## Pesquisa e Desenvolvimento

Conhecimento interno e análises técnicas:

- [Análise de Validação LLM](PESQUISA/ANALISE-LLM.md) — Como o LLM valida testes, heurísticas, debug de 18 commits
- [Preservação de Contexto](PESQUISA/PRESERVED-INTENT.md) — Métodos de preservação de intenção em 3 camadas

---

## Histórico e Arquivo

Documentação de planejamento e sprints anteriores:

- [Arquivo de Planejamento](../.planning/ARCHIVE/) — Planos de fase, bugs históricos, planos de teste, sprint reviews
- [Conhecimento Ancestral](./conhecimento_ancestral/) — Pesquisa de contexto de tentativas anteriores

---

## Links Rápidos

- [README Principal](../README.md) — README do projeto
- [AGENTS.md](../AGENTS.md) — Instruções de agente e governance GSD
- [CHANGELOG.md](../CHANGELOG.md) — Changelog do projeto
- [ADRs](../adrs/) — Decisões arquiteturais formais (ADR-0001 a ADR-0006)
- **Source Code:** `src/testforge/`
- **Testes:** `tests/`

---

## Sobre este documento

Este índice contém apenas links para arquivos que existem. Se encontrar um link quebrado, abra uma issue.

**Última atualização:** 2026-06-22
**Versão:** v0.4.0
