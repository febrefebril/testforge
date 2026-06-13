# ADR-0003: SemanticTestCase como fonte de verdade

**Status:** Accepted
**Date:** 2026-06-13

## Context

Precisamos decidir qual artefato e a fonte de verdade do teste: o script Playwright gerado ou o contrato semantico.

## Decision

O `SemanticTestCase` (YAML) e a fonte de verdade. O script Playwright Python e um artefato derivado que pode ser regenerado a qualquer momento a partir do contrato semantico.

## Consequences

- Se o compiler melhorar, todos os scripts sao regenerados sem perder intencao
- Scripts gerados nao devem ser editados manualmente
- O contrato semantico deve ser versionado (git); scripts gerados podem ser regenerados
