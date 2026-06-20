# TestForge — Arquivo Histórico

**Data:** 2026-06-20  
**Versão:** v0.4.0

Este diretório contém documentação histórica, planos arquivados e artefatos de fases anteriores do TestForge.

---

## 📑 Arquivo por Fase

### Fase A — Recorder (Congelada)

Documentação de planejamento e execução:

- `BUG-FIX-PLAN.md` (381 linhas) — Plano de correções v0.3.0
- `BUG-FIX-PLAN-v2.md` (615 linhas) — Revisão de correções
- `PLANO-DE-TESTE.md` (744 linhas) — Plano de testes da Fase A
- `PLANO-TESTE-INTENT-LAB.md` (274 linhas) — Laboratório de testes de intenção
- `SPRINT-REVIEW.md` (283 linhas) — Review de sprint
- `SPRINT-REVIEW-SLIDES.md` (303 linhas) — Apresentação de sprint
- `testforge_plano_consolidado_2026-06-16.md` (798 linhas) — Plano consolidado
- `testforge_plano_sprints_intent_readiness.md` (935 linhas) — Readiness de sprints

### Fase B — Intent Reconstructor (Implementada)

- `FASE-B-PLAN.md` (627 linhas) — Plano inicial da Fase B
- `FASE-B-COMPLETION-REPORT.md` (211 linhas) — Relatório de conclusão

### Consolidados em v0.4.0

Documentação consolidada e movida para `docs/`:

- `BUGS.md` → `docs/REFERENCIA/BUGS-KNOWNS.md`
- `bugs.md` → `docs/REFERENCIA/BUGS-KNOWNS.md`
- `TUTORIAL-LLM-HEALING.md` → `docs/TUTORIAIS/05-llm-healing.md`
- `TUTORIAL.md` → `docs/TUTORIAIS/` (dividido)
- `run-incremental.md` → `docs/TUTORIAIS/06-incremental-execution.md`
- `PHASE-B-RUNBOOK.md` → `docs/TUTORIAIS/09-debugging-fase-b.md`
- `GOVERNANCA.md` → `docs/REFERENCIA/GOVERNANCE.md`
- `DIAGRAMA-VERSIONING.md` → `docs/DIAGRAMAS/`
- `ANALISE-LLM.md` → `docs/PESQUISA/`
- `PRESERVACAO-CONHECIMENTO.md` → `docs/PESQUISA/PRESERVED-INTENT.md`

---

## 📊 Estatísticas do Arquivo

| Tipo | Contagem | Linhas Totais |
|------|----------|---------------|
| Planos de Teste | 4 | ~2,000 |
| Planos de Bug/Fix | 2 | ~996 |
| Reviews de Sprint | 2 | ~586 |
| Planos Consolidados | 2 | ~1,733 |
| Fase B | 2 | ~838 |
| **Total** | **14** | **~6,153 linhas** |

---

## 🗺️ Navegação

### Para Encontrar Informações Histórias

1. **Buglist Completa:** → `../docs/REFERENCIA/BUGS-KNOWNS.md`
2. **Fase B Details:** → `../docs/ARQUITETURA/FASES.md`
3. **Planos de Teste:** Veja `PLANO-DE-TESTE.md` neste diretório
4. **Documentação Ancestral:** → `../../conhecimento_ancestral/`

### Links para Documentação Ativa

- **Índice Principal:** `../docs/INDEX.md`
- **Overview:** `../docs/OVERVIEW.md`
- **Arquitetura:** `../docs/ARQUITETURA/`
- **Referência:** `../docs/REFERENCIA/`
- **Tutoriais:** `../docs/TUTORIAIS/`

---

## 🔄 Política de Arquivo

- Documentação de **planejamento** é arquivada após execução da fase
- Documentação **ativa** é consolidada em `docs/`
- Decisões técnicas (**ADRs**) são mantidas em `adrs/`
- Histórico é preservado para auditoria e aprendizado

---

## 📝 Como Usar Este Arquivo

1. **Pesquisa histórica:** Use grep para buscar em arquivos antigos
   ```bash
   grep -r "bug-001" .
   ```

2. **Comparação de versões:** Compare planos arquivados com docs/ atuais
   ```bash
   diff FASE-B-PLAN.md ../docs/ARQUITETURA/FASES.md
   ```

3. **Aprendizado:** Leia planos antigos para entender decisões
   ```bash
   cat BUG-FIX-PLAN.md
   ```

---

## ⏰ Timeline

| Data | Evento |
|------|--------|
| 2026-06-16 | Fase A congelada, 162 testes passando |
| 2026-06-17 | Fase B planejamento concluído |
| 2026-06-18 | Fase B implementação iniciada |
| 2026-06-20 | Fase B concluída, consolidação de docs v0.4.0 |

---

**Arquivo Mantido Por:** André PN  
**Última Atualização:** 2026-06-20  
**Próxima Revisão:** Após Fase C concluída
