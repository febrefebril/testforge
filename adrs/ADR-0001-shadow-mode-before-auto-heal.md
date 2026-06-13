# ADR-0001: Shadow mode before auto-heal

**Status:** Accepted
**Date:** 2026-06-13

## Context

Self-healing pode introduzir falsos positivos — o sistema "cura" um teste que na verdade deveria falhar. Precisamos de validacao antes de aplicar healing automatico.

## Decision

Toda sugestao de healing passa por shadow mode antes de ser promovida a auto-heal. No shadow mode, a sugestao e registrada com evidencias e oracles, mas NAO e aplicada automaticamente. Requer revisao humana.

## Consequences

- Maior seguranca: falso healing e detectado antes de causar dano
- Maior latencia: healing nao e instantaneo
- Necessario: fila de revisao humana (pending_reviews)
