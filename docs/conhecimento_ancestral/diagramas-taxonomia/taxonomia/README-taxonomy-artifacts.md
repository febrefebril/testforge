# Artefatos gerados — TestForge Taxonomia v1.0

Foram gerados dois artefatos complementares à taxonomia enviada:

1. `curator-decision-tree.puml` — diagrama PlantUML da árvore de decisão do Agente Curador.
2. `taxonomy-case-schema.yaml` — contrato YAML sugerido para cadastrar casos taxonômicos de forma implementável.

## Observações rápidas de revisão

- A taxonomia está boa para implementação incremental porque já separa ID, família, sintoma, detecção, estratégia, fallback, saída, sucesso e prioridade.
- Para virar base de código com menos ambiguidade, recomendo adicionar em cada caso: `probable_causes`, `evidence_requirements`, `validator_policy` e `risk_flags`.
- Há sobreposição intencional entre `INP-*` e `FILE-*`; para evitar duplicidade na implementação, trate `INP-*` como interação de UI e `FILE-*` como gestão/validação de artefato.
- Há sobreposição entre `CTX-002`, `LIM-002` e `INP-008`/`LIM-001`; a regra prática deve ser: família técnica primeiro, limite de segurança como classificação final quando a automação segura não for possível.
- `waitForFunction`, captura de popup e handler de diálogo aparecem como estratégias, mas ainda não estão na lista canônica da seção 2.3. Sugiro promovê-las para estratégias conhecidas ou registrá-las como `custom`.
