# TESTFORGE — Revisão de Implementabilidade da Taxonomia v1.0

## Veredito

A taxonomia está implementável como catálogo de classificação do Agente Curador e já cobre os pontos críticos discutidos para o TestForge: seletores frágeis, JSF/PrimeFaces, AJAX, iframes, overlay, uploads/downloads, asserts antes/durante/depois, evidência, flakiness e limites técnicos.

## Ajustes recomendados antes de congelar como fonte normativa

### 1. Normalizar estratégias citadas fora da lista oficial

Alguns casos usam estratégias que aparecem na tabela, mas não estão listadas em `2.3 Estratégias conhecidas`. Recomenda-se incluir no enum oficial:

- `popup_context_capture`
- `native_dialog_handler`
- `file_fixture_binding`
- `precondition_validation`
- `environment_failure_classification`
- `sensitive_data_masking`
- `critical_action_checkpoint`
- `trace_evidence_capture`
- `patch_audit_trail`
- `flakiness_gate`
- `browser_policy_event_inference`
- `screen_ready_marker_wait`
- `virtual_list_scroll_search`
- `datepicker_component_selection`
- `custom_combobox_selection`
- `rich_text_editor_binding`
- `input_mask_user_typing`
- `drag_and_drop_semantic`

### 2. Tratar duplicidade intencional de CAPTCHA

`INP-008` e `LIM-001` tratam CAPTCHA. A recomendação é manter ambos, mas com papéis diferentes:

- `INP-008`: detecção durante interação especializada.
- `LIM-001`: classificação final de limite técnico/não automatizável.

No motor, `INP-008` pode ser um caso de entrada que redireciona para a política de limite `LIM-001`.

### 3. Definir regra de precedência

Para evitar múltiplas classificações conflitantes, usar a seguinte precedência:

1. Segurança/limite técnico: `LIM-*`
2. Checkpoints manuais e recorder: `REC-*`
3. Contexto/escopo: `CTX-*`
4. Estado da aplicação: `STA-*`
5. Timing/DOM: `TIM-*` e `DOM-*`
6. Seletores: `SEL-*`
7. Inputs/arquivos/asserts: `INP-*`, `FILE-*`, `AST-*`
8. Observabilidade: `OBS-*` como anotação transversal

### 4. Tornar observabilidade transversal

`OBS-*` deve funcionar como família transversal. Exemplo: uma falha `SEL-001` também pode gerar `OBS-004` se o patch foi aplicado. O relatório deve permitir `primary_taxonomy_id` e `related_taxonomy_ids`.

### 5. Adicionar campos de implementação ao schema

Campos recomendados por caso:

```yaml
id: SEL-001
family: Seletores frágeis
priority: P0
matchers:
  - type: selector_pattern
    value: "j_idt"
strategies:
  primary: semantic_locator_conversion
  fallbacks:
    - label_proximity
    - text_content_match
risk_level: low
requires_manual_checkpoint: false
produces_patch: true
requires_validation_runs: 3
related_cases:
  - OBS-004
  - OBS-006
```

## Critério de congelamento

A taxonomia pode ser congelada como v1.0 quando:

- todos os P0 tiverem teste automatizado na matriz;
- o enum de estratégias estiver completo;
- houver política formal para `MANUAL_REQUIRED`;
- o relatório do curador aceitar `primary_taxonomy_id` e `related_taxonomy_ids`;
- o PatchValidator rejeitar loops repetidos conforme `OBS-005`;
- a promoção exigir rodadas limpas conforme `OBS-006`.
