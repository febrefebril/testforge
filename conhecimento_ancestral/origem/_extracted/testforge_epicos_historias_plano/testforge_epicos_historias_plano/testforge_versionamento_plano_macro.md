# TestForge — Guia de Versionamento do Plano Macro

## 1. Objetivo

Garantir que o plano macro, os épicos, as histórias, os critérios de aceite e as políticas arquiteturais sejam rastreáveis e auditáveis.

## 2. Artefatos versionados

```text
docs/plano_macro.md
docs/backlog_epicos_historias.md
policies/promotion_gate_policy.yaml
policies/evidence_sensitive_data_policy.yaml
schemas/semantic_test_case.schema.yaml
CHANGELOG.md
VERSION
adrs/*.md
```

## 3. Versionamento semântico

Formato:

```text
MAJOR.MINOR.PATCH
```

Regras:

```text
MAJOR: muda premissas arquiteturais, governança central ou fluxo de promoção.
MINOR: adiciona épicos, histórias, policies, fases ou escopo funcional.
PATCH: corrige texto, critérios, exemplos ou inconsistências sem mudar escopo.
```

## 4. Estados do plano

```text
draft
review
approved
superseded
deprecated
```

## 5. Cabeçalho obrigatório do plano

```yaml
artifact: TestForge Plano Macro
version: 0.2.0
status: draft
owner: Andre Perotti Netto
date: 2026-06-12
source_of_truth: docs/plano_macro.md
related_adrs:
  - ADR-0001-shadow-mode-before-auto-heal
  - ADR-0002-evidence-alert-only-sensitive-data
```

## 6. Changelog obrigatório

Toda alteração relevante deve registrar:

```markdown
## [0.2.0] - 2026-06-12

### Added
- Plano de épicos e histórias.

### Changed
- EvidenceCollector definido como alert_only para dados sensíveis no MVP.

### Removed
- Mascaramento automático no EvidenceCollector no MVP.
```

## 7. ADRs iniciais recomendados

```text
ADR-0001 — Usar shadow mode antes de auto-heal.
ADR-0002 — EvidenceCollector em modo alert-only para dados sensíveis.
ADR-0003 — Usar Synthetic Lab antes de piloto real.
ADR-0004 — Promotion Gate obrigatório para promoção de healing.
ADR-0005 — LLM apenas como curadoria, não como mecanismo principal.
```

## 8. Regra de governança

Nenhuma mudança estrutural deve existir apenas em conversa ou mensagem. Mudanças devem ser refletidas em:

1. plano macro;
2. backlog;
3. changelog;
4. ADR, quando alterar decisão arquitetural;
5. policy YAML, quando alterar regra executável.
