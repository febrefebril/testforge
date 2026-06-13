# ADR-0002: EvidenceCollector alert_only para dados sensiveis

**Status:** Accepted
**Date:** 2026-06-13

## Context

Durante a gravacao e coleta de evidencias, dados sensiveis (CPF, CNPJ, telefone) podem ser capturados em screenshots, DOM snapshots e network logs. Precisamos de uma politica clara sobre como lidar com isso.

## Decision

No MVP, o EvidenceCollector e o Recorder operam em modo `alert_only`: detectam possiveis dados sensiveis e registram um alerta, mas NAO mascaram, NAO removem, NAO alteram os dados originais. A mascara sera implementada em versao futura quando os criterios de deteccao forem validados.

## Consequences

- Evidencias preservam fidelidade total — util para debugging
- Risco: dados sensiveis em logs e screenshots
- Mitigacao: `sensitive_data_alert.json` registra localizacao exata para revisao
