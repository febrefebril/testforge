# TESTFORGE — Manual Checkpoint Policy

**Objetivo:** definir quando o Agente Curador deve parar, solicitar intervenção humana ou registrar pendência, evitando locators, asserts ou patches inventados.

## 1. Estados permitidos

- `MANUAL_REQUIRED`: há risco, ambiguidade ou limite técnico que exige decisão humana.
- `UNRESOLVED`: o curador tentou estratégias seguras, mas não conseguiu validar a correção.
- `PARTIALLY_RESOLVED`: há correção útil, mas a conclusão depende de ação humana ou premissa externa.

## 2. Gatilhos obrigatórios para checkpoint manual

| Gatilho | IDs relacionados | Decisão padrão |
|---|---|---|
| Iframe cross-origin inacessível | CTX-002, LIM-002 | `MANUAL_REQUIRED` |
| Shadow DOM fechado | CTX-004 | `MANUAL_REQUIRED` ou `UNRESOLVED` justificado |
| CAPTCHA/desafio humano | INP-008, LIM-001 | `MANUAL_REQUIRED` |
| Assert ambíguo | AST-008 | `MANUAL_REQUIRED` |
| Operação irreversível ou crítica | LIM-004 | `MANUAL_REQUIRED` antes da ação |
| Dado sensível mascarado/segredo | LIM-003 | aplicar mascaramento/tokenização; se impossível, `MANUAL_REQUIRED` |
| Permissão insuficiente | STA-005 | `MANUAL_REQUIRED` ou `UNRESOLVED`, sem alterar script indevidamente |

## 3. Regra anti-invenção

O curador **não deve** fabricar:

- locator para DOM inacessível;
- assert sem alvo objetivo;
- dado sensível em claro;
- bypass para CAPTCHA;
- confirmação automática para ação irreversível;
- causa técnica sem evidência mínima.

## 4. Registro obrigatório no relatório

Todo checkpoint manual deve registrar:

1. `taxonomy_id`;
2. evidência mínima coletada;
3. risco ou ambiguidade detectada;
4. estratégia tentada, se houver;
5. motivo da interrupção;
6. ação esperada do usuário;
7. estado final.

## 5. Template YAML

```yaml
manual_checkpoint:
  taxonomy_id: CTX-002
  state: MANUAL_REQUIRED
  evidence:
    - "iframe cross-origin detectado"
    - "DOM interno inacessível por política do browser"
  reason: "Não é seguro fabricar seletor para conteúdo inacessível."
  expected_user_action: "Informar contrato externo, ambiente de teste acessível ou aceitar checkpoint manual."
  safe_to_continue: false
```
