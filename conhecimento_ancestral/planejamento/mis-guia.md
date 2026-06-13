# TestForge — Implementação do Modelo Intermediário Semântico

## Objetivo

O Modelo Intermediário Semântico, ou MIS, é a camada entre o gravador e o gerador de código. Ele impede que o TestForge dependa diretamente de seletores frágeis capturados durante a gravação.

Em vez de representar um passo como:

```python
await page.locator("#btn123").click()
```

O MIS representa o passo como um contrato de intenção:

```yaml
intent: clicar no botão de pesquisar proposta
action: click
target:
  role: button
  accessible_name: Pesquisar
  visible_text: Pesquisar
context:
  page_url_pattern: /siopi/propostas
  nearby_texts:
    - CPF
    - Número da Proposta
locator_candidates:
  - strategy: role
    value: button[name="Pesquisar"]
    score: 0.95
```

## Pipeline recomendado

```text
Evento bruto capturado pelo Recorder
        ↓
Normalizer
        ↓
Semantic Enricher
        ↓
Locator Candidate Generator
        ↓
Scorer
        ↓
Semantic Test Model
        ↓
Compiler para Playwright Python
```

## Componentes

### 1. RawRecordedEvent

Evento bruto capturado pelo gravador. Deve conter tudo que foi observado, sem tentar decidir ainda o melhor seletor.

### 2. SemanticAction

Representa uma ação de usuário com intenção, alvo, contexto, candidatos de locator e assertions pós-ação.

### 3. SemanticTarget

Identidade composta do elemento. Deve conter sinais semânticos, estruturais e históricos.

### 4. LocatorCandidate

Representa uma alternativa de localização com estratégia, valor, score e justificativa.

### 5. SemanticCompiler

Transforma o MIS em código executável, priorizando locators semânticos e assertions observáveis.

## Regras de implementação

1. O gravador não escolhe o seletor definitivo.
2. O MIS preserva múltiplos candidatos.
3. O compilador escolhe o melhor candidato no momento da geração.
4. O runner pode usar o mesmo MIS para healing.
5. A LLM só atua em casos de baixa confiança ou ambiguidade.

## Ordem recomendada dos locators

1. role + accessible name
2. label
3. placeholder
4. test id
5. texto visível quando for contrato de negócio
6. atributos estáveis de domínio
7. relação com elementos próximos
8. CSS simples
9. XPath apenas como último recurso

## MVP sugerido

### Semana 1 — Modelo e normalização

- Definir schema YAML/JSON.
- Criar classes Python.
- Converter eventos brutos para SemanticAction.

### Semana 2 — Geração de candidatos

- Implementar gerador de role, label, testid, text, css e xpath.
- Implementar scoring simples.

### Semana 3 — Compiler Playwright

- Gerar código Python com fallback determinístico.
- Gerar assertions pós-ação.

### Semana 4 — Healing determinístico

- Reextrair DOM e accessibility tree.
- Recalcular candidatos.
- Persistir healing aprovado.

## Exemplo de score inicial

```text
score =
  0.30 * role_match +
  0.25 * accessible_name_match +
  0.15 * label_match +
  0.10 * nearby_text_match +
  0.10 * attribute_stability +
  0.05 * dom_position_similarity +
  0.05 * historical_success
```

## Critérios de decisão

- score >= 0.90: locator confiável.
- 0.75 <= score < 0.90: locator utilizável, mas monitorado.
- 0.60 <= score < 0.75: exigir fallback ou curadoria.
- score < 0.60: não gerar locator automático.

## Saída esperada

O MIS deve permitir que o mesmo registro de gravação seja usado para:

- gerar código Playwright;
- executar teste com fallback;
- depurar falhas;
- acionar healing determinístico;
- enviar pacote estruturado para LLM em caso de curadoria.
