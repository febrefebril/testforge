# Decisão — Dados Sensíveis no EvidenceCollector

## Contexto

Durante o desenho do TestForge, foi discutida a necessidade de lidar com evidências coletadas automaticamente, incluindo screenshots, DOM, accessibility tree, network logs e traces.

Essas evidências podem conter dados sensíveis, como CPF, identificadores de cliente, informações de contrato, dados de proposta ou outros dados internos.

## Decisão

No MVP inicial, o `EvidenceCollector` **não deve mascarar automaticamente** dados sensíveis.

A política inicial será apenas:

```text
alertar a possível presença de dados sensíveis nas evidências coletadas.
```

## Implicações

O EvidenceCollector deve:

1. coletar evidências com fidelidade;
2. registrar um campo de alerta no `manifest.json` ou metadados;
3. indicar quais tipos de dados sensíveis podem estar presentes;
4. não modificar screenshots, DOM, traces ou network logs;
5. não aplicar mascaramento automático no MVP.

## Exemplo de metadado sugerido

```json
{
  "sensitive_data_alert": {
    "enabled": true,
    "masking_applied": false,
    "possible_sensitive_data_detected": true,
    "detected_categories": ["cpf_pattern", "numeric_identifier"],
    "policy": "alert_only"
  }
}
```

## Justificativa

Nesta fase, a prioridade é validar a arquitetura de shadow mode, oracle pós-ação, evidência e Promotion Gate. O mascaramento automático pode remover contexto necessário para investigar falso healing e revisar oracles.

A decisão não elimina a necessidade de governança. Ela apenas posterga o mascaramento automático para uma fase posterior, após definição de política institucional de armazenamento, acesso, retenção e tratamento das evidências.

## Revisão futura

Esta decisão deve ser revisitada antes de integrar com ambientes reais contendo dados sensíveis ou antes de disponibilizar evidências para públicos amplos.
