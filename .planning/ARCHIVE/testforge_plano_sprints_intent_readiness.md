# TestForge — Plano de Sprints, Épicos, Histórias, Testes e Validação

Data: 2026-06-18

## Objetivo

Definir o plano de implementação para tornar o TestForge capaz de finalizar uma gravação somente quando a intenção do teste estiver completa e validada por execução incremental.

A gravação somente será marcada como pronta quando cumprir três provas:

1. Prova de completude: todos os dados necessários estão representados na intenção.
2. Prova de aplicação: os dados foram aplicados nos campos corretos.
3. Prova de execução: o fluxo foi reexecutado incrementalmente e validado por step.

## Fluxo-alvo

```text
Gravação termina
↓
Normalizer tenta reconstruir intenção
↓
Intent Completeness Checker encontra campos pendentes
↓
CLI pergunta ao usuário
↓
Usuário informa valores faltantes
↓
TestForge atualiza field_value_map / test_data / semantic_steps
↓
TestForge reexecuta incrementalmente a gravação
↓
Precondição, execução e pós-condição são validadas por step
↓
RecordingReadinessGate decide
↓
Gravação é marcada como READY ou NEEDS_REVIEW
```

---

# Sprint 1 — Contrato de Completude da Intenção

## Objetivo

Criar a fundação que impede uma gravação incompleta de ser tratada como pronta.

## Épico 1 — Intent Completeness Contract

### História 1.1 — Criar estados formais da gravação

Como desenvolvedor do TestForge,
quero representar estados claros da gravação,
para impedir que uma gravação incompleta seja usada como pronta.

Estados sugeridos:

- completed_raw
- intent_reconstructed
- needs_user_input
- intent_complete
- incremental_validation_running
- incrementally_validated
- ready_for_team
- incomplete_intent
- needs_review

Critérios de aceite:

- A gravação possui status persistido em metadata.
- O status muda de forma rastreável.
- O compile não considera pronta uma gravação em incomplete_intent ou needs_review.

### História 1.2 — Criar IntentCompletenessChecker

Como TestForge,
quero validar se todos os campos necessários possuem valor confiável,
para saber se a intenção do teste está completa.

Critérios de aceite:

- Detecta campos com missing_fill.
- Detecta selects sem valor resolvido.
- Detecta cliques em campos com gap de digitação e sem fill associado.
- Gera lista de campos pendentes com label, placeholder, id, name, selector provável e step.
- Classifica cada campo como resolved, resolved_with_warning, review_required ou missing.

### História 1.3 — Gerar relatório de completude

Como QA,
quero receber um relatório claro ao final da gravação,
para saber se preciso complementar algum valor.

Critérios de aceite:

- Gera intent_completeness_report.json.
- Gera intent_completeness_report.md.
- Mostra campos capturados, campos sintetizados, campos pendentes e fontes de evidência.

## Testes automatizados da Sprint 1

### CT-AUTO-1.1 — Recording sem campos pendentes

Página: pages/intent-complete-basic/index.html

Fluxo:

1. Abrir página.
2. Preencher input normal.
3. Clicar em enviar.
4. Finalizar gravação.

Validação:

- IntentCompletenessChecker retorna complete.
- Nenhum campo missing.
- Status final após normalização: intent_complete.

### CT-AUTO-1.2 — Input com foco e gap, mas sem fill

Página: pages/missing-fill-gap/index.html

Fluxo:

1. Clicar no campo Valor.
2. Simular digitação que não gera input event.
3. Clicar em continuar.

Validação:

- Campo é marcado como missing.
- Relatório informa reason = typing_not_captured.
- Compile é bloqueado.

### CT-AUTO-1.3 — Select sem valor capturado

Página: pages/select-not-captured/index.html

Validação:

- Campo select é detectado como pendente se não houver selected value confiável.
- Relatório mostra label e options disponíveis.

## Testes manuais da Sprint 1

### CT-MAN-1.1 — Revisar relatório de completude

Passos:

1. Rodar gravação em página com campo normal e campo problemático.
2. Finalizar com Shift+S.
3. Abrir intent_completeness_report.md.

Resultado esperado:

- O relatório é compreensível por um QA.
- O campo problemático aparece com contexto suficiente para correção.

---

# Sprint 2 — Complementação Assistida via CLI

## Objetivo

Permitir que o QA complemente valores faltantes imediatamente ao final da gravação.

## Épico 2 — Interactive Completion Prompt

### História 2.1 — Perguntar valores faltantes no CLI

Como QA,
quero que o TestForge me pergunte valores não capturados,
para corrigir a gravação sem regravar.

Critérios de aceite:

- O prompt aparece apenas em modo interativo.
- O prompt mostra intenção provável, step, motivo, identificadores e selector provável.
- O usuário pode informar valor ou deixar pendente.
- Valores informados são salvos com source = user_supplied_cli.

### História 2.2 — Atualizar field_value_map

Como TestForge,
quero salvar valores informados pelo usuário no field_value_map,
para que o executor consiga aplicá-los.

Critérios de aceite:

- field_value_map.json inclui entradas user_supplied_cli.
- Cada entrada possui field_key, value, intention, identifiers, source, confidence e step_index.
- Confidence de valor informado pelo usuário é 1.0, mas a aplicação ainda precisa ser validada por execução incremental.

### História 2.3 — Atualizar test_data.json

Como QA,
quero que valores complementados sejam persistidos em massa de dados,
para poder reexecutar o teste sem digitar novamente.

Critérios de aceite:

- test_data.json é criado ou atualizado.
- O arquivo registra metadata.source por campo.
- Valores sensíveis geram alerta, não mascaramento automático.

### História 2.4 — Modo não interativo

Como usuário em CI ou automação,
quero que o TestForge não trave esperando input,
para permitir uso em scripts.

Critérios de aceite:

- Flag --no-interactive não abre prompt.
- Campos pendentes geram test_data.template.json.
- Status fica incomplete_intent.

## Testes automatizados da Sprint 2

### CT-AUTO-2.1 — Prompt resolve campo missing_fill

Página: pages/missing-fill-gap/index.html

Validação:

- Simular entrada do usuário no stdin.
- Verificar field_value_map.json com source user_supplied_cli.
- Verificar test_data.json preenchido.
- Verificar status intent_complete após nova checagem.

### CT-AUTO-2.2 — Usuário pula campo pendente

Validação:

- Simular Enter vazio no prompt.
- Status final: incomplete_intent.
- test_data.template.json contém campo pendente.

### CT-AUTO-2.3 — Modo --no-interactive

Validação:

- O comando termina sem input humano.
- Nenhum prompt é exibido.
- test_data.template.json é criado.

## Testes manuais da Sprint 2

### CT-MAN-2.1 — QA corrige valor ao final da gravação

Passos:

1. Gravar página missing-fill-gap.
2. Finalizar gravação.
3. Informar valor quando o CLI perguntar.
4. Conferir field_value_map.json e test_data.json.

Resultado esperado:

- Valor informado aparece nos artefatos.
- Relatório indica campo resolvido por user_supplied_cli.

---

# Sprint 3 — Captura Universal de Estado de Campos

## Objetivo

Reduzir ao máximo a necessidade de prompt humano usando snapshots, hooks e observadores genéricos.

## Épico 3 — Field State Snapshot

### História 3.1 — Capturar field_snapshots.jsonl

Como TestForge,
quero capturar snapshots periódicos dos campos,
para reconstruir valores mesmo sem input event.

Critérios de aceite:

- Captura input, textarea, select, contenteditable e ARIA fields.
- Snapshot possui timestamp, fingerprint, identificadores, valor, visibilidade, enabled e bounding box.
- Snapshots são compactados para evitar volume excessivo.

### História 3.2 — Capturar final_state_snapshot.json

Como TestForge,
quero salvar o estado final da tela,
para recuperar valores no encerramento da gravação.

Critérios de aceite:

- final_state_snapshot.json é obrigatório.
- É gerado em Shift+S, submit, beforeunload e navegação relevante.
- Se falhar, quality_flag é registrado.

## Épico 4 — Setter Hook e MutationObserver

### História 4.1 — Instrumentar setters de value

Como TestForge,
quero detectar mudanças programáticas de valor,
para capturar frameworks que não disparam input event.

Critérios de aceite:

- Hook em HTMLInputElement.value.
- Hook em HTMLTextAreaElement.value.
- Hook em HTMLSelectElement.value.
- Alterações são salvas como value_mutation.

### História 4.2 — Observar contenteditable e ARIA widgets

Como TestForge,
quero detectar alterações em componentes customizados,
para cobrir comboboxes e editores ricos.

Critérios de aceite:

- MutationObserver captura mudanças relevantes.
- Eventos são correlacionados ao elemento focado ou alvo mais próximo.

## Testes automatizados da Sprint 3

### CT-AUTO-3.1 — Campo com preventDefault

Página: pages/prevent-default-input/index.html

Validação:

- Nenhum input event confiável é emitido.
- O valor é recuperado por setter_hook ou snapshot_diff.
- Campo não aparece como missing.

### CT-AUTO-3.2 — Currency mask

Página: pages/currency-mask/index.html

Validação:

- Valor digitado é capturado em raw, displayed e normalized.
- Valor final entra no field_value_map.
- Estratégia recomendada de execução é press_sequentially quando aplicável.

### CT-AUTO-3.3 — Contenteditable

Página: pages/contenteditable/index.html

Validação:

- Texto editado é recuperado por MutationObserver/snapshot.
- Semantic step gerado é content_edit ou fill equivalente.

### CT-AUTO-3.4 — Select nativo

Página: pages/native-select/index.html

Validação:

- selected value e selected text são capturados.
- Semantic step usa select_option.

## Testes manuais da Sprint 3

### CT-MAN-3.1 — Testar campos problemáticos visualmente

Passos:

1. Abrir página currency-mask.
2. Digitar valor.
3. Finalizar gravação.
4. Conferir field_snapshots.jsonl e final_state_snapshot.json.

Resultado esperado:

- Valor aparece mesmo se não houver fill event.

---

# Sprint 4 — Reconstrução de Intenção por Evidências

## Objetivo

Criar motor que combina eventos, snapshots, form_values e rede para sintetizar steps semânticos confiáveis.

## Épico 5 — Intent Reconstructor

### História 5.1 — Reconstruir fill ausente por snapshot diff

Como TestForge,
quero sintetizar um step fill quando o valor mudou entre snapshots,
para evitar regravação.

Critérios de aceite:

- Detecta before/after de campo.
- Associa mudança a click/focus/gap próximo.
- Cria SemanticAction com source = snapshot_diff.

### História 5.2 — Reconstruir valor por form_values

Como TestForge,
quero usar valores capturados no submit,
para preencher campos que não emitiram eventos.

Critérios de aceite:

- Propaga form_values para campos anteriores compatíveis.
- Registra source = form_values.
- Mantém evidência do evento de submit.

### História 5.3 — Reconstruir valor por payload de rede

Como TestForge,
quero usar payloads enviados pela aplicação,
para recuperar dados não visíveis ou componentes customizados.

Critérios de aceite:

- Parseia JSON e form-urlencoded.
- Correlaciona payload key com field_key por name/id/label/value/timestamp.
- Registra source = network_payload.

## Testes automatizados da Sprint 4

### CT-AUTO-4.1 — Fill reconstruído por snapshot_diff

Página: pages/prevent-default-input/index.html

Validação:

- Semantic step sintetizado possui source snapshot_diff.
- Não solicita valor no CLI.

### CT-AUTO-4.2 — Fill reconstruído por form_values

Página: pages/form-submit-values/index.html

Validação:

- Campo sem input event é resolvido pelo submit.
- field_value_map aponta source form_values.

### CT-AUTO-4.3 — Valor reconstruído por network_payload

Página: pages/network-payload-only/index.html

Validação:

- Payload enviado contém valor.
- Valor é correlacionado ao campo correto.
- IntentCompletenessChecker considera resolved_with_warning ou resolved.

## Testes manuais da Sprint 4

### CT-MAN-4.1 — Conferir reconstrução de intenção

Passos:

1. Gravar página network-payload-only.
2. Finalizar gravação.
3. Abrir semantic_steps.jsonl.
4. Conferir source de cada step.

Resultado esperado:

- O step ausente foi sintetizado com evidência clara.

---

# Sprint 5 — Validação Incremental antes de READY

## Objetivo

Garantir que intenção completa seja executável antes de marcar a gravação como pronta.

## Épico 6 — Incremental Recording Validator

### História 6.1 — Reexecutar gravação incrementalmente

Como TestForge,
quero reexecutar a gravação após completar a intenção,
para provar que o teste funciona.

Critérios de aceite:

- Executa semantic_steps usando field_value_map/test_data.
- Valida precondição, execução e pós-condição por step.
- Gera validation_run/execution_report.json.

### História 6.2 — Validar valores user_supplied_cli

Como TestForge,
quero provar que valores informados no CLI foram aplicados corretamente,
para evitar falso pronto.

Critérios de aceite:

- Cada valor user_supplied_cli é usado por pelo menos um step.
- O campo apresenta estado esperado após aplicação.
- Se aplicação falhar, status = needs_review.

### História 6.3 — Criar RecordingReadinessGate

Como TestForge,
quero decidir se uma gravação está pronta com critérios objetivos,
para proteger o piloto com QAs.

Critérios de aceite:

- Só aprova se completude passou.
- Só aprova se steps bloqueantes passaram ou foram healed_validated.
- Rejeita healing sem oracle positivo.
- Rejeita campos obrigatórios pendentes.
- Salva readiness_report.json e readiness_report.md.

## Testes automatizados da Sprint 5

### CT-AUTO-5.1 — Gravação completa passa incrementalmente

Página: pages/ready-flow/index.html

Validação:

- Status final: ready_for_team.
- readiness_report mostra passed.

### CT-AUTO-5.2 — Valor user_supplied_cli aplicado no campo errado

Página: pages/two-similar-fields/index.html

Validação:

- Validação incremental detecta pós-condição errada.
- Status final: needs_review.

### CT-AUTO-5.3 — Campo com currency mask exige press_sequentially

Página: pages/currency-mask/index.html

Validação:

- fill direto falha ou não altera estado.
- estratégia correta aplica valor.
- Pós-condição passa.

### CT-AUTO-5.4 — Falha bloqueante impede READY

Página: pages/blocking-step-failure/index.html

Validação:

- Step dependente é marked blocked.
- RecordingReadinessGate rejeita.

## Testes manuais da Sprint 5

### CT-MAN-5.1 — QA grava, complementa e valida incrementalmente

Passos:

1. Rodar testforge record em ready-flow.
2. Informar valor faltante se solicitado.
3. Aguardar validação incremental.
4. Conferir readiness_report.md.

Resultado esperado:

- Gravação só fica READY após execução incremental bem-sucedida.

---

# Sprint 6 — Páginas de Exemplo e Matriz de Fluxos

## Objetivo

Criar páginas locais para testar automaticamente e manualmente todos os fluxos críticos do gravador universal.

## Épico 7 — Intent Lab Pages

Criar pasta:

```text
tests/intent_lab/pages/
```

## Páginas obrigatórias

### Página 1 — ready-flow

Cobre fluxo feliz:

- input normal;
- select;
- checkbox;
- botão submit;
- resultado final.

### Página 2 — missing-fill-gap

Cobre:

- click/focus em campo;
- gap de digitação;
- ausência de input/change;
- prompt CLI.

### Página 3 — prevent-default-input

Cobre:

- keydown com preventDefault;
- alteração por JS;
- captura por setter_hook/snapshot.

### Página 4 — currency-mask

Cobre:

- campo monetário;
- valor displayed diferente do raw;
- execução com press_sequentially;
- validação pós-ação.

### Página 5 — native-select

Cobre:

- select nativo;
- selected value;
- selected text;
- geração select_option.

### Página 6 — custom-combobox

Cobre:

- role=combobox;
- opções renderizadas dinamicamente;
- valor escolhido por texto.

### Página 7 — contenteditable

Cobre:

- editor rico simples;
- MutationObserver;
- snapshot diff.

### Página 8 — network-payload-only

Cobre:

- valor enviado via fetch POST;
- correlação payload → field_value_map.

### Página 9 — iframe-field

Cobre:

- campo dentro de iframe same-origin;
- frame_id;
- execução incremental.

### Página 10 — shadow-dom-field

Cobre:

- input dentro de shadow DOM;
- shadow path;
- fallback de captura.

### Página 11 — upload-file

Cobre:

- input type=file;
- set_input_files;
- não gerar fill fakepath.

### Página 12 — two-similar-fields

Cobre:

- dois campos parecidos;
- risco de associar valor ao campo errado;
- validação incremental detectando erro.

### Página 13 — dynamic-result

Cobre:

- resultado muda conforme dado de entrada;
- assert não pode depender de valor monetário fixo gravado;
- validação por texto base/regex/estrutura.

### Página 14 — blocking-step-failure

Cobre:

- step obrigatório falha;
- dependentes são blocked;
- readiness gate rejeita.

## Testes automatizados da Sprint 6

Criar:

```text
tests/intent_lab/test_intent_lab_pages.py
tests/intent_lab/test_recording_readiness.py
tests/intent_lab/test_cli_completion.py
tests/intent_lab/test_incremental_validation.py
```

Critérios:

- Cada página tem pelo menos um teste automatizado.
- Cada página tem README próprio.
- Cada teste valida artefatos gerados.
- Cada teste roda sem sistemas internos.

## Testes manuais da Sprint 6

Criar:

```text
docs/PLANO-TESTE-INTENT-LAB.md
```

Cada caso manual deve conter:

- objetivo;
- página;
- comando;
- passos do QA;
- resultado esperado;
- artefatos a conferir;
- critérios de aprovação.

---

# Sprint 7 — Integração com CLI e Experiência do QA

## Objetivo

Consolidar o fluxo para uso no piloto por QAs.

## Épico 8 — CLI de fechamento da gravação

### História 8.1 — Flag --validate-before-ready

Como QA,
quero que o TestForge valide a gravação antes de marcá-la como pronta,
para confiar no artefato gerado.

Critérios de aceite:

- Flag executa completude + prompt + validação incremental.
- Se passar, status ready_for_team.
- Se falhar, status needs_review.

### História 8.2 — Tornar validação padrão no modo piloto

Como time TestForge,
quero habilitar validação antes de READY no piloto,
para evitar gravações quebradas.

Critérios de aceite:

- Configuração pode habilitar validate_before_ready por padrão.
- Modo debug permite desabilitar explicitamente.

### História 8.3 — Relatório amigável para QA

Como QA,
quero entender o resultado final da gravação,
para saber se posso enviar ao repositório.

Critérios de aceite:

- readiness_report.md possui resumo legível.
- Mostra status final, campos complementados, steps validados e falhas.
- Indica próximos passos quando needs_review.

## Testes automatizados da Sprint 7

### CT-AUTO-7.1 — CLI record com validate-before-ready

Validação:

- Fluxo completo roda.
- Status final correto.
- Relatórios criados.

### CT-AUTO-7.2 — CLI com --no-interactive

Validação:

- Não bloqueia.
- Gera template.
- Não marca READY.

### CT-AUTO-7.3 — CLI com falha incremental

Validação:

- Status needs_review.
- Código de saída e relatório são coerentes.

## Testes manuais da Sprint 7

### CT-MAN-7.1 — Simulação do piloto QA

Passos:

1. QA grava um fluxo em página ready-flow.
2. QA complementa valor se solicitado.
3. TestForge valida incrementalmente.
4. QA confere readiness_report.md.
5. QA envia artefatos.

Resultado esperado:

- O QA consegue operar sem ajuda de dev.

---

# Sprint 8 — Endurecimento, Métricas e Gate para Piloto

## Objetivo

Preparar a bateria de gravação com 5 a 10 QAs.

## Épico 9 — Métricas de prontidão

### História 9.1 — Registrar métricas de completude

Métricas:

- total_recordings
- ready_for_team
- incomplete_intent
- needs_review
- fields_auto_resolved
- fields_user_supplied
- fields_missing
- incremental_validation_passed
- incremental_validation_failed

### História 9.2 — Registrar motivos de falha

Categorias:

- missing_value
- selector_failed
- actionability_failed
- postcondition_failed
- network_wait_failed
- dynamic_assert_failed
- wrong_field_mapping

### História 9.3 — Dashboard/relatório consolidado do piloto

Critérios de aceite:

- Gera relatório agregado em Markdown/JSON.
- Lista gravações prontas e pendentes.
- Ajuda a priorizar correções.

## Testes automatizados da Sprint 8

### CT-AUTO-8.1 — Métricas refletem resultados reais

Validação:

- Uma gravação READY incrementa ready_for_team.
- Uma gravação incompleta incrementa incomplete_intent.
- Uma falha incremental incrementa incremental_validation_failed.

### CT-AUTO-8.2 — Relatório consolidado

Validação:

- Gera pilot_readiness_report.md.
- Contém status por recording.

## Testes manuais da Sprint 8

### CT-MAN-8.1 — Revisão final antes do piloto

Passos:

1. Rodar todas as páginas do Intent Lab.
2. Conferir relatórios.
3. Conferir métricas agregadas.
4. Validar que nenhum fluxo incompleto vira READY.

Resultado esperado:

- Time aprova distribuição para QAs.

---

# Matriz de cobertura

| Fluxo | Página | Automático | Manual | Gate |
|---|---|---|---|---|
| Fluxo feliz | ready-flow | Sim | Sim | READY |
| Missing fill | missing-fill-gap | Sim | Sim | Prompt ou INCOMPLETE |
| preventDefault | prevent-default-input | Sim | Sim | Auto-resolved |
| Máscara monetária | currency-mask | Sim | Sim | Incremental validated |
| Select nativo | native-select | Sim | Sim | select_option |
| Combobox custom | custom-combobox | Sim | Sim | resolved/review |
| Contenteditable | contenteditable | Sim | Sim | snapshot_diff |
| Payload de rede | network-payload-only | Sim | Sim | network_payload |
| Iframe | iframe-field | Sim | Sim | frame-aware |
| Shadow DOM | shadow-dom-field | Sim | Sim | shadow-aware |
| Upload | upload-file | Sim | Sim | set_input_files |
| Campos parecidos | two-similar-fields | Sim | Sim | detects wrong mapping |
| Resultado dinâmico | dynamic-result | Sim | Sim | stable assertion |
| Falha bloqueante | blocking-step-failure | Sim | Sim | NEEDS_REVIEW |

---

# Definição de pronto para o plano inteiro

O plano será considerado implementado quando:

1. Todas as páginas do Intent Lab existirem.
2. Cada página tiver teste automatizado.
3. Cada página tiver caso manual documentado.
4. O fluxo record → normalize → complete → validate incremental → readiness gate estiver implementado.
5. Nenhuma gravação incompleta puder ser marcada como READY.
6. Valores user_supplied_cli forem obrigatoriamente validados por execução incremental.
7. O piloto com QAs puder usar relatórios para saber o que está pronto e o que precisa revisão.
