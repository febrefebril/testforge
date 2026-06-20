# Documentação TestForge v0.4.0

**Bem-vindo!** Esta é a documentação completa do TestForge, um gravador de intenção para testes resilientes com self-healing.

---

## 🎯 Novo por Aqui?

Comece pelo [OVERVIEW.md](OVERVIEW.md) — Visão geral em 5 minutos.

---

## 👥 Para Testers / Usuários Finais

| Link | Descrição |
|------|-----------|
| [Quick Start](USER-GUIDE/QUICK-START.md) | 5 minutos para gravar seu 1º teste |
| [Guia Completo](USER-GUIDE/GRAVAR-FLUXO.md) | Como gravar, compilar, executar testes |
| [Troubleshooting](USER-GUIDE/TROUBLESHOOTING.md) | Problemas comuns e soluções |

---

## 📚 Tutoriais Passo a Passo

Aprenda TestForge com exemplos práticos:

1. [Setup do Ambiente](TUTORIAIS/01-setup-ambiente.md) — Instalar dependências
2. [Seu Primeiro Teste](TUTORIAIS/02-gravar-seu-primeiro-teste.md) — Primeira gravação
3. [Compilar e Executar](TUTORIAIS/03-compilar-executar.md) — Gerar e rodar script
4. [Healing Determinístico](TUTORIAIS/04-healing-deterministico.md) — Estratégias L0-L1
5. [Healing com LLM](TUTORIAIS/05-llm-healing.md) — Self-healing automático
6. [Execução Incremental](TUTORIAIS/06-incremental-execution.md) — Runner passo a passo
7. [Data-Driven Testing](TUTORIAIS/07-data-driven-testing.md) — Múltiplos datasets
8. [Modo Piloto](TUTORIAIS/08-modo-piloto.md) — Fase de avaliação

---

## 🏗️ Arquitetura (Para Desenvolvedores)

Entenda como o TestForge funciona internamente:

| Seção | Conteúdo |
|-------|----------|
| [Visão Geral das Fases](ARQUITETURA/FASES.md) | A-D: Recorder → Intent → Compiler → Executor |
| [Pipeline Semantic MIS](ARQUITETURA/FLUXO-SEMANTIC-MIS.md) | Fluxo de transformação raw_events → SemanticTestCase |
| [Healing L0-L3](ARQUITETURA/HEALING-L0-L3.md) | Estratégias de recuperação automática |
| [Intent Reconstruction](ARQUITETURA/INTENT-RECONSTRUCTION.md) | 5 estratégias de reconstrução de intenção |
| [Field Values Mapping](ARQUITETURA/FIELD-VALUES-MAPPING.md) | Mapeamento de valores de formulário |
| [Oracle e Promotion Gate](ARQUITETURA/ORACLE-PROMOTION-GATE.md) | Validação e gates de qualidade |
| [Incremental Runner](ARQUITETURA/INCREMENTAL-RUNNER.md) | Executor com healing L0-L2 |

---

## 📖 Referência Rápida

Consulte informações específicas:

| Link | Descrição |
|------|-----------|
| [Todos os Comandos CLI](REFERENCIA/CLI.md) | `record`, `compile`, `run`, `heal` |
| [Bugs Conhecidos](REFERENCIA/BUGS-KNOWNS.md) | Issues abertos e corrigidos |
| [Glossário](REFERENCIA/GLOSSARIO.md) | Termos e conceitos do TestForge |
| [Governance e Processo](REFERENCIA/GOVERNANCE.md) | Princípios de design e roadmap |
| [Decisões de Arquitetura (ADRs)](REFERENCIA/ADR-INDEX.md) | Decisões técnicas documentadas |
| [Stack Tecnológico](REFERENCIA/STACK-TECNOLOGICO.md) | Dependências e versões |

---

## 🔬 Pesquisa e Desenvolvimento

Conhecimento de desenvolvimento e análises:

| Link | Descrição |
|------|-----------|
| [Análise de Validação LLM](PESQUISA/ANALISE-LLM.md) | Como o LLM valida testes e evidência |
| [Preservação de Contexto](PESQUISA/PRESERVED-INTENT.md) | Métodos de preservação de intenção |

---

## 📊 Diagramas

Visualizações da arquitetura:

| Diagrama | Descrição |
|----------|-----------|
| [Versioning](DIAGRAMAS/DIAGRAMA-VERSIONING.md) | Versionamento de gravações e compilações |
| [Healing Flow](DIAGRAMAS/DIAGRAMA-HEALING.md) | Fluxo de healing L0-L3 |

---

## 📜 Histórico e Arquivo

Documentação anterior e histórico de planejamento:

- [Planos Anteriores](./../.planning/ARCHIVE/) — Planos arquivados por fase
- [Conhecimento Ancestral](./../../conhecimento_ancestral/) — Pesquisa de contexto

---

## 🗺️ Mapas de Migração

Documentação movida durante consolidação v0.4.0:

| Arquivo Antigo | Novo Local | Tipo | Status |
|----------------|-----------|------|--------|
| `BUGS.md` + `bugs.md` | `REFERENCIA/BUGS-KNOWNS.md` | Consolidado | ✅ |
| `FASE-B-PLAN.md` | `.planning/ARCHIVE/` | Arquivado | ✅ |
| `FASE-B-COMPLETION-REPORT.md` | `ARQUITETURA/FASES.md` | Consolidado | ✅ |
| `TUTORIAL-LLM-HEALING.md` | `TUTORIAIS/05-llm-healing.md` | Movido | ✅ |
| `run-incremental.md` | `TUTORIAIS/06-incremental-execution.md` | Movido | ✅ |
| `PHASE-B-RUNBOOK.md` | `TUTORIAIS/09-debugging-fase-b.md` | Movido | ✅ |
| `GOVERNANCA.md` | `REFERENCIA/GOVERNANCE.md` | Movido | ✅ |
| `DIAGRAMA-VERSIONING.md` | `DIAGRAMAS/` | Movido | ✅ |
| `ANALISE-LLM.md` | `PESQUISA/` | Movido | ✅ |
| `PRESERVACAO-CONHECIMENTO.md` | `PESQUISA/PRESERVED-INTENT.md` | Movido | ✅ |
| BUG-FIX-PLAN* | `.planning/ARCHIVE/` | Arquivado | ✅ |
| PLANO-* | `.planning/ARCHIVE/` | Arquivado | ✅ |
| SPRINT-REVIEW* | `.planning/ARCHIVE/` | Arquivado | ✅ |

---

## 🔗 Links Rápidos

- **README Principal:** [../../README.md](../../README.md)
- **Agents & Governance:** [../../AGENTS.md](../../AGENTS.md)
- **Changelog:** [../../CHANGELOG.md](../../CHANGELOG.md)
- **Source Code:** `src/testforge/`
- **Tests:** `tests/`

---

## 📞 Suporte

- **Issues:** GitHub issues no repositório
- **Discussões:** GitHub discussions
- **Email:** andre.pnetto@gmail.com

---

**Última atualização:** 2026-06-20  
**Versão:** v0.4.0  
**Status:** Documentação consolidada e navegável
