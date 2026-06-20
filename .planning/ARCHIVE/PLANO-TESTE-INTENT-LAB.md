# Plano de Teste — Intent Lab

## Objetivo

Validar manualmente todos os fluxos críticos do gravador universal do TestForge
usando as páginas do Intent Lab. Cada teste cobre um padrão específico
de captura, reconstrução e validação de intenção.

## Páginas

| # | Página | Fluxo | Automação |
|---|--------|-------|-----------|
| 1 | ready-flow | Fluxo feliz completo | CT-AUTO-5.1 |
| 2 | missing-fill-gap | Gap de digitação sem input event | CT-AUTO-1.2 |
| 3 | prevent-default-input | preventDefault + JS setter | CT-AUTO-3.1 |
| 4 | currency-mask | Máscara monetária | CT-AUTO-3.2 |
| 5 | native-select | Select nativo | CT-AUTO-3.4 |
| 6 | custom-combobox | role=combobox customizado | Manual |
| 7 | contenteditable | Editor rico contenteditable | CT-AUTO-3.3 |
| 8 | network-payload-only | Valor enviado via fetch POST | CT-AUTO-4.3 |
| 9 | iframe-field | Campo em iframe same-origin | Manual |
| 10 | shadow-dom-field | Campo em shadow DOM | Manual |
| 11 | upload-file | Input type=file | Manual |
| 12 | two-similar-fields | Dois campos parecidos | CT-AUTO-5.2 |
| 13 | dynamic-result | Resultado dinâmico | Manual |
| 14 | blocking-step-failure | Falha bloqueante em cascata | CT-AUTO-5.4 |

## Pré-condições

1. TestForge instalado e ambiente ativado (`source activate.sh`)
2. Servidor de páginas estáticas rodando:
   ```bash
   cd tests/intent_lab
   python -m http.server 8080
   ```
3. Gravação configurada:
   ```bash
   testforge record --url http://localhost:8080/pages/<pagina>/index.html
   ```

## Casos de Teste Manual

### CT-MAN-6.1 — Fluxo feliz (ready-flow)

**Página:** ready-flow

**Comando:**
```bash
testforge record --url http://localhost:8080/pages/ready-flow/index.html
```

**Passos do QA:**
1. Preencher campo "Nome completo"
2. Selecionar "Cidade"
3. Marcar "Aceito os termos"
4. Clicar em "Enviar"
5. Finalizar gravação (Shift+S)
6. Conferir artefatos gerados

**Resultado esperado:**
- Status final: `ready_for_team`
- `field_value_map.json` contém nome, cidade, aceite
- `semantic_steps.jsonl` contém fill, select_option, click
- `readiness_report.md` mostra PASS

**Artefatos a conferir:**
- `recording.json` — status
- `field_value_map.json` — 3 campos
- `semantic_steps.jsonl` — steps sem skip
- `readiness_report.json` — verdict PASS

### CT-MAN-6.2 — Missing fill gap (missing-fill-gap)

**Página:** missing-fill-gap

**Passos do QA:**
1. Clicar no campo "Valor"
2. Digitar algo rapidamente (que pode não gerar input event)
3. Clicar em outro campo ou botão
4. Finalizar gravação

**Resultado esperado:**
- Campo "Valor" aparece como `missing_fill` no field_value_map
- Se snapshot_diff capturou, campo resolvido automaticamente
- Se não capturou, CLI pergunta o valor (modo interativo)
- Relatório de completude mostra campo pendente ou resolvido

### CT-MAN-6.3 — PreventDefault + JS setter (prevent-default-input)

**Página:** prevent-default-input

**Passos do QA:**
1. Clicar no campo
2. Tentar digitar (evento pode ser prevenido)
3. Clicar em "OK"
4. Finalizar gravação

**Resultado esperado:**
- Valor capturado por setter_hook ou snapshot_diff
- field_value_map mostra source = snapshot_diff
- Não solicita valor no CLI (auto-resolvido)

### CT-MAN-6.4 — Currency mask (currency-mask)

**Página:** currency-mask

**Passos do QA:**
1. Digitar valor monetário (ex: 1.234,56)
2. Clicar em "Confirmar"
3. Finalizar gravação

**Resultado esperado:**
- Valor raw capturado em field_snapshots.jsonl
- IntentReconstructor resolve por snapshot_diff
- Estratégia recomendada: press_sequentially

### CT-MAN-6.5 — Select nativo (native-select)

**Página:** native-select

**Passos do QA:**
1. Selecionar opção no select
2. Clicar em "OK"
3. Finalizar gravação

**Resultado esperado:**
- selected value e selected text capturados
- Semantic step: select_option
- field_value_map com source = fill_event

### CT-MAN-6.6 — Custom combobox (custom-combobox)

**Página:** custom-combobox

**Passos do QA:**
1. Clicar no campo combobox
2. Digitar para filtrar opções
3. Clicar em uma opção
4. Clicar em "Confirmar"
5. Finalizar gravação

**Resultado esperado:**
- Interação capturada (cliques + input)
- Valor final capturado por snapshot_diff
- field_value_map contém o valor selecionado

### CT-MAN-6.7 — Contenteditable (contenteditable)

**Página:** contenteditable

**Passos do QA:**
1. Editar o conteúdo do editor rich text
2. Clicar fora
3. Finalizar gravação

**Resultado esperado:**
- MutationObserver capturou a mudança
- Semantic step gerado: content_edit ou fill
- Valor capturado por snapshot_diff

### CT-MAN-6.8 — Network payload (network-payload-only)

**Página:** network-payload-only

**Passos do QA:**
1. Preencher campo
2. Clicar em "Enviar" (faz fetch POST)
3. Finalizar gravação

**Resultado esperado:**
- Payload da rede capturado em network_log.json
- IntentReconstructor correlaciona payload ao campo
- field_value_map source = network_payload

### CT-MAN-6.9 — Iframe field (iframe-field)

**Página:** iframe-field

**Passos do QA:**
1. Preencher campo externo
2. Preencher campos dentro do iframe
3. Clicar em "Finalizar"
4. Finalizar gravação

**Resultado esperado:**
- Campos do iframe são capturados
- frame_id está presente nos eventos
- field_value_map contém campos do iframe

### CT-MAN-6.10 — Shadow DOM field (shadow-dom-field)

**Página:** shadow-dom-field

**Passos do QA:**
1. Preencher campo normal
2. Preencher campo dentro do shadow DOM
3. Clicar em "Enviar"
4. Finalizar gravação

**Resultado esperado:**
- Shadow DOM field é capturado via snapshots
- Shadow path registrado nos eventos
- field_value_map contém shadow field

### CT-MAN-6.11 — Upload file (upload-file)

**Página:** upload-file

**Passos do QA:**
1. Preencher "Nome do documento"
2. Selecionar "Tipo"
3. Selecionar arquivo (navegador abre diálogo)
4. Clicar em "Enviar"
5. Finalizar gravação

**Resultado esperado:**
- Input type=file não gera fill fakepath
- Nome/tipo capturados normalmente
- Campo file tratado como set_input_files

### CT-MAN-6.12 — Campos parecidos (two-similar-fields)

**Página:** two-similar-fields

**Passos do QA:**
1. Preencher endereço de entrega
2. Preencher endereço de cobrança
3. Clicar em "Salvar Endereço"
4. Finalizar gravação

**Resultado esperado:**
- Valores mapeados aos campos corretos
- Validação incremental detecta associação errada se ocorrer
- Status: ready_for_team ou needs_review

### CT-MAN-6.13 — Resultado dinâmico (dynamic-result)

**Página:** dynamic-result

**Passos do QA:**
1. Preencher Valor 1 e Valor 2
2. Selecionar operação
3. Clicar em "Calcular"
4. Finalizar gravação

**Resultado esperado:**
- Assert não deve depender de valor fixo
- Deve usar texto base/regex/estrutura
- Gravação pronta para reexecução com dados diferentes

### CT-MAN-6.14 — Falha bloqueante (blocking-step-failure)

**Página:** blocking-step-failure

**Passos do QA:**
1. Pular seleção de UF
2. Tentar selecionar cidade (deve estar desabilitada)
3. Clicar em "Enviar" (deve mostrar erro)
4. Finalizar gravação

**Resultado esperado:**
- Step de UF marcado como blocking
- Steps dependentes marcados como blocked
- RecordingReadinessGate rejeita (needs_review)

## Critérios de Aprovação

Cada teste manual é aprovado quando:

1. A gravação finaliza sem crash
2. Os artefatos esperados são gerados
3. O status da gravação é compatível com o fluxo
4. Nenhuma gravação incompleta é marcada como READY
5. O relatório de readiness é compreensível por um QA
