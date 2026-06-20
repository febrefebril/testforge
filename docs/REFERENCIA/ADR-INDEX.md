# Índice de Decisões de Arquitetura (ADRs)

**Versão:** 0.4.0  
**Última atualização:** 2026-06-20

---

## Introdução

Este documento indexa todas as **Architectural Decision Records (ADRs)** — decisões técnicas formalmente documentadas que moldaram a arquitetura do TestForge.

Cada ADR segue o padrão: **Contexto → Decisão → Consequências**.

---

## 📑 Índice de ADRs

### ADR-0001: Shadow Mode Before Auto-Heal

**Status:** ✅ Aceita  
**Data:** v0.3.0  
**Responsável:** André PN

**Decisão:**  
Antes de aplicar healing automático, TestForge valida a proposta em "shadow mode" — executa sem efeito colateral, verifica resultado, aprova antes de aplicar.

**Por quê:**  
Evita false positives que quebram testes ao invés de consertá-los.

**Impacto:**  
- Healing mais confiável (menos false heals)
- Overhead: 20-30% mais lento (vale a pena)

**Link:** `adrs/ADR-0001-shadow-mode-before-auto-heal.md`

---

### ADR-0002: Alert-Only for Sensitive Data

**Status:** ✅ Aceita  
**Data:** v0.3.0  
**Responsável:** André PN

**Decisão:**  
TestForge **não mascara** valores sensíveis (CPF, senha) nos artefatos. Em vez disso, alerta visualmente quando detecta padrão.

**Por quê:**  
- Mascaramento complica debugging (valores aparecem mascarados no log)
- Responsabilidade do desenvolvedor: não gravar dados reais
- MVP: apenas alerta, não mascaramento automático

**Impacto:**  
- Documentação: "Gravar com dados de teste, não dados reais"
- No futuro: considerar mascaramento opcional

**Link:** `adrs/ADR-0002-alert-only-sensitive-data.md`

---

### ADR-0003: SemanticTestCase as Source of Truth

**Status:** ✅ Aceita  
**Data:** v0.3.0  
**Responsável:** André PN

**Decisão:**  
`SemanticTestCase` (YAML) é a "source of truth". Qualquer mudança (healing, data injection, etc) atualiza SemanticTestCase, não o script.py gerado.

**Por quê:**  
- Script.py é apenas render de SemanticTestCase
- Mudanças manuais no .py são descartadas no próximo compile
- Histórico de mudanças fica em SemanticTestCase

**Impacto:**  
- Usuários não editam script.py diretamente
- Healing atualiza SemanticTestCase
- Compiler sempre regenera from scratch

**Link:** `adrs/ADR-0003-semantic-test-case-source-of-truth.md`

---

### ADR-0006: Phase B — Evidence Consumption Strategy

**Status:** ✅ Implementada  
**Data:** v0.3.1  
**Responsável:** André PN

**Decisão:**  
Fase B consome 5 fontes de evidência em ordem de prioridade:

1. Setter hooks (value_mutations.jsonl) — score 100
2. Snapshot diff (field_snapshots) — score 60
3. Checked transitions (radio/checkbox) — score 65
4. Network payload (POST/PUT) — score 75
5. Final state (fallback) — score 55

**Por quê:**  
- Setter hooks são explícitos (captura JS mutation diretamente)
- Network payloads são prova de envio real
- Final state é fallback quando nada mais funciona

**Impacto:**  
- 95%+ campos com intenção reconstruída
- Score de completude (gate 0.70) robusto
- Blind spots identificados automaticamente

**Link:** `adrs/ADR-006-phase-b-evidence-consumption.md`

---

## 📊 Matriz de Decisões

| ADR | Tópico | Status | Impacto | Risco |
|-----|--------|--------|--------|-------|
| ADR-0001 | Validação de healing | ✅ Ativa | Alto (confiança) | Baixo |
| ADR-0002 | Privacidade | ✅ Ativa | Médio (docs) | Médio |
| ADR-0003 | Source of Truth | ✅ Ativa | Alto (design) | Baixo |
| ADR-0006 | Reconstrução de intent | ✅ Ativa | Alto (cobertura) | Baixo |

---

## 🔄 Fluxo de ADR

Quando uma decisão arquitetural é necessária:

```
1. Problema identificado
2. ADR proposto (contexto, opções, decisão)
3. Review por team
4. ✅ Aceita ou ❌ Rejeitada
5. Documentado em adrs/ADR-NNN-*.md
6. Implementado em fase correspondente
7. Histórico mantido mesmo após implementação
```

---

## 📋 Decisões Pendentes (Candidatas a ADR)

| Decisão | Prioridade | Status |
|---------|-----------|--------|
| Oracle architecture (L3 learning) | P1 | ⏳ Em discussão |
| Data file format standardization | P2 | ⏳ Em discussão |
| Multi-browser support strategy | P1 | ⏳ Em discussão |
| Distributed healing (agent swarm) | P3 | 🎯 Planejada |

---

## 🔗 Links Relacionados

- **Arquivo de ADRs:** `adrs/`
- **Governance:** [GOVERNANCE.md](GOVERNANCE.md)
- **Roadmap:** [../../AGENTS.md](../../AGENTS.md)

---

## 📚 Como Ler um ADR

Cada ADR segue este template:

```markdown
# ADR-NNN: {Título da Decisão}

## Status
✅ Aceita | ⏳ Pendente | ❌ Rejeitada

## Contexto
O problema que levou a essa decisão.

## Decisão
O que foi decidido.

## Consequências
Impactos positivos e negativos.

## Alternativas Consideradas
Opções que foram descartadas e por quê.
```

---

**Última atualização:** 2026-06-20  
**Versão:** v0.4.0  
**Responsável:** André PN
