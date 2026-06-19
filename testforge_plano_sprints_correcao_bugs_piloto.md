# TestForge — Plano Detalhado de Sprints para Correção dos Bugs e Preparação do Piloto

**Data:** 2026-06-18  
**Objetivo:** estabilizar o TestForge para gravação real por QAs, removendo complexidade desnecessária, corrigindo erros básicos de captura e consolidando o contrato entre gravação, intenção semântica, compilação, execução, métricas e readiness.  
**Escopo:** TestForge apenas. CDP deixa de ser caminho principal. MCP RTC/RQM/RDNG, MCP mestre e SpecKit permanecem fora do escopo.  
**Diretriz central:** antes de evoluir self-healing/LLM, o TestForge precisa gravar corretamente campos básicos, preservar eventos, gerar ações Playwright corretas e produzir artefatos auditáveis.

---

## 1. Resumo Executivo

A proposta está dividida em sete sprints:

1. **Sprint 0: Hotfix de amanhã** — reduzir risco imediato, remover CDP do fluxo principal, desativar evidência intrusiva, corrigir CLI básico e preparar gravação estável para piloto.
2. **Sprint 1: Gravador não intrusivo** — tornar o recorder leve, estável, resiliente a reload/postback e capaz de registrar eventos sem alterar layout.
3. **Sprint 2: Captura básica correta** — corrigir captura de campos fundamentais: `select`, `input`, campos mascarados, fills sequenciais e valores pendentes.
4. **Sprint 3: Contrato semântico** — estabilizar o contrato entre `raw_events`, `steps`, `semantic_steps`, `test_data`, metadata e script.
5. **Sprint 4: Compilação e execução confiáveis** — garantir que o script gerado execute ações compatíveis com cada tipo de elemento e evite asserts frágeis.
6. **Sprint 5: Métricas, readiness e relatórios** — corrigir métricas, readiness gate, relatórios e bloqueio de cascata.
7. **Sprint 6: Limpeza, documentação e piloto** — remover complexidade residual, atualizar documentação, criar checklist operacional e preparar distribuição para QAs.

---

## 2. Princípios de Execução

### 2.1. Princípios técnicos

1. **Gravador deve ser leve e não intrusivo.**  
   O recorder não deve alterar viewport, layout, zoom, escala, `body`, `html`, scroll ou estilos globais da aplicação.

2. **CDP não é solução de captura.**  
   CDP pode abrir o navegador em ambientes específicos, mas não corrige perda de eventos, campos não capturados, snapshots vazios, `select` mal compilado ou contrato instável. Para o piloto, CDP deve sair do fluxo principal.

3. **Evidência não pode atrapalhar a gravação.**  
   Capturas pesadas de screenshot/DOM por evento devem ser opt-in, não padrão. O padrão do piloto deve ser evidência leve.

4. **Intenção semântica é a fonte de verdade.**  
   O script Playwright deve ser uma renderização da intenção semântica, não uma interpretação direta e frágil dos eventos brutos.

5. **Toda ação precisa ser compatível com o tipo do elemento.**  
   `select` gera `select_option`, `input text` gera `fill`, `checkbox` gera `check/uncheck`, `radio` gera `check`, `input file` gera `set_input_files`.

6. **Nenhuma gravação incompleta deve ser marcada como pronta.**  
   Se houver campo pendente, valor não validado, step bloqueante falho ou readiness inconsistente, o status deve ser `incomplete_intent` ou `needs_review`.

7. **Diagnóstico deve ser auditável.**  
   O terminal pode mostrar resumo, mas os relatórios JSON/Markdown devem conter detalhes completos.

---

## 3. Sprint 0 — Hotfix de Amanhã

### 3.1. Objetivo da Sprint

Reduzir risco imediato para permitir uma bateria de gravação inicial com QAs. A Sprint 0 não busca resolver toda a arquitetura; ela busca impedir que o TestForge falhe nos pontos mais básicos:

- página piscando/diminuindo durante gravação;
- CDP adicionando complexidade ao fluxo;
- `record` sem URL quebrando com `goto(None)`;
- `--complete` informando valor mas readiness usando relatório antigo;
- `compile --check` bloqueado indevidamente;
- logs orientando uso de `testforge.exe` bloqueado por GPO.

### 3.2. Resultado Esperado

Ao final da Sprint 0, um QA deve conseguir rodar:

```powershell
python -m testforge.cli.app record --browser chrome --complete "https://simax.caixa/simax/" --name simax_piloto_001
```

E obter:

- gravação sem flick causado pelo TestForge;
- artefatos mínimos salvos;
- valores pendentes solicitados no CLI;
- status coerente após informar valores;
- possibilidade de rodar `compile --check` mesmo se a gravação estiver incompleta.

---

### Épico 0.1 — Remover CDP do Fluxo Principal

#### História 0.1.1 — Remover CDP das recomendações do CLI e da documentação

**Como** time TestForge,  
**quero** retirar CDP do caminho recomendado do piloto,  
**para** reduzir complexidade operacional e evitar que o time foque no workaround errado.

**Motivação:**  
O CDP foi criado como tentativa de contornar problemas de browser corporativo, mas não corrigiu flick, campos não capturados, snapshots vazios nem problemas de normalização. Para amanhã, ele deve ser fallback excepcional, não fluxo principal.

**Tarefas técnicas:**

- Remover comandos CDP do roteiro do piloto.
- Atualizar README/Tutorial para usar `--browser chrome` ou `--browser edge`.
- Não ativar CDP automaticamente quando `--windows-caixa` estiver ausente.
- Marcar `cdp_launcher.py` como experimental ou fora do piloto.
- Se possível, remover `--windows-caixa` e `--cdp-browser` do help principal ou esconder sob seção experimental.

**Critérios de aceite:**

- O comando recomendado não usa CDP.
- O tutorial do piloto não menciona CDP como primeira opção.
- `record --help` não induz o QA a usar CDP sem necessidade.
- Se CDP permanecer no código, deve estar documentado como fallback experimental.

**Testes manuais:**

```powershell
python -m testforge.cli.app record --help
python -m testforge.cli.app run --help
```

Validar que o roteiro operacional principal usa Chrome/Edge normal.

---

#### História 0.1.2 — Definir browser padrão de piloto

**Como** QA,  
**quero** usar um browser corporativo normal,  
**para** gravar fluxos reais sem depender de CDP.

**Tarefas técnicas:**

- Definir `--browser chrome` como recomendação inicial.
- Definir `--browser edge` como segunda opção.
- Evitar fallback automático para CDP.
- Registrar no metadata o browser usado.

**Critérios de aceite:**

- Metadata da gravação inclui `browser=chrome` ou `browser=edge`.
- O QA sabe qual browser foi usado.
- O TestForge não muda de browser silenciosamente.

---

### Épico 0.2 — Modo de Gravação Leve para Evitar Flick

#### História 0.2.1 — Desabilitar screenshot por evento durante gravação padrão

**Como** QA,  
**quero** que o TestForge não capture screenshot pesado a cada interação,  
**para** evitar flick, resize, reflow e interferência visual.

**Hipótese técnica:**  
O flick pode estar sendo causado por rotina de evidência visual, especialmente se houver screenshot full-page, captura pesada por evento, medição de documento inteiro ou operação que force renderização/reflow.

**Tarefas técnicas:**

- Identificar todas as chamadas de screenshot no caminho de gravação.
- Separar screenshot de gravação e screenshot de execução/healing.
- Na gravação padrão, permitir somente:
  - screenshot inicial opcional;
  - screenshot final opcional;
  - screenshot em erro, se houver.
- Criar configuração interna `evidence_level=light` como padrão.
- Garantir que `full_page=True` não seja usado durante gravação padrão.

**Critérios de aceite:**

- Uma interação simples não dispara screenshot por evento.
- Não há alteração visual perceptível na página a cada evento.
- O relatório informa qual nível de evidência foi usado.
- Existe caminho explícito para reativar evidência completa em debug.

**Testes manuais:**

1. Gravar SIMAX em modo padrão.
2. Interagir com campo e botão.
3. Observar se a página diminui e volta.
4. Conferir metadata:

```json
{
  "evidence_level": "light",
  "screenshots_per_event": false
}
```

---

#### História 0.2.2 — Não alterar viewport em gravação headed

**Como** usuário do TestForge,  
**quero** que o navegador mantenha o tamanho real da janela,  
**para** impedir layout shift causado por viewport artificial.

**Tarefas técnicas:**

- Remover `page.set_viewport_size(...)` do caminho de `record` em modo headed.
- Evitar `new_context(viewport={...})` para gravação interativa, quando possível.
- Registrar viewport inicial e final.
- Se viewport mudar, registrar `VIEWPORT_CHANGED` em `quality_flags`.

**Critérios de aceite:**

- Durante gravação headed, o TestForge não força `1280x720`.
- A janela permanece no tamanho escolhido pelo usuário.
- `viewport_trace.jsonl` mostra estabilidade de `innerWidth` e `innerHeight`.

**Testes manuais:**

- Abrir página no Chrome/Edge.
- Maximizar janela.
- Iniciar gravação.
- Confirmar que a página não é redimensionada.

---

#### História 0.2.3 — Criar Viewport Invariance Probe

**Como** desenvolvedor,  
**quero** medir viewport antes e depois de cada operação sensível,  
**para** provar se o flick vem de screenshot, DOM snapshot, field snapshot, flush ou outra etapa.

**Tarefas técnicas:**

- Criar utilitário JS para coletar:
  - `window.innerWidth`;
  - `window.innerHeight`;
  - `window.outerWidth`;
  - `window.outerHeight`;
  - `window.devicePixelRatio`;
  - `window.visualViewport.width`;
  - `window.visualViewport.height`;
  - `window.scrollX`;
  - `window.scrollY`.
- Registrar fases:
  - `before_event`;
  - `after_event`;
  - `before_flush`;
  - `after_flush`;
  - `before_screenshot`;
  - `after_screenshot`;
  - `before_dom_snapshot`;
  - `after_dom_snapshot`;
  - `before_field_snapshot`;
  - `after_field_snapshot`.
- Salvar em:

```text
recordings/<id>/viewport_trace.jsonl
```

**Critérios de aceite:**

- Arquivo `viewport_trace.jsonl` é gerado em modo debug/piloto.
- Se houver mudança de viewport, relatório aponta fase provável.
- Se não houver mudança, descartamos viewport como causa principal.

**Exemplo de linha esperada:**

```json
{
  "phase": "before_screenshot",
  "innerWidth": 1366,
  "innerHeight": 728,
  "devicePixelRatio": 1.25,
  "scrollX": 0,
  "scrollY": 0,
  "timestamp": "2026-06-18T22:10:00-03:00"
}
```

---

### Épico 0.3 — Correções Básicas de CLI

#### História 0.3.1 — URL obrigatória para nova gravação

**Como** QA,  
**quero** receber erro claro ao esquecer a URL,  
**para** não quebrar o comando com `page.goto(None)`.

**Tarefas técnicas:**

- No início de `cmd_record`, validar `args.url`.
- Se URL ausente, imprimir mensagem e retornar código de erro controlado.
- Não abrir browser antes dessa validação.

**Critérios de aceite:**

```powershell
python -m testforge.cli.app record --browser chrome
```

Retorna mensagem semelhante a:

```text
[TestForge] Erro: URL obrigatoria para iniciar nova gravacao.
Exemplo:
python -m testforge.cli.app record --browser chrome "https://sistema/" --name minha_gravacao
```

Sem traceback.

---

#### História 0.3.2 — `compile --check` não pode ser bloqueado por status

**Como** QA/desenvolvedor,  
**quero** rodar `compile --check` em gravação incompleta,  
**para** diagnosticar e corrigir pendências.

**Tarefas técnicas:**

- Alterar `cmd_compile` para aplicar bloqueio de status apenas quando `--check` não estiver presente.
- Permitir que `--check` normalize, rode completeness e gere relatório.
- Ajustar mensagem para sugerir `python -m testforge.cli.app`, não `testforge.exe`.

**Critérios de aceite:**

```powershell
python -m testforge.cli.app compile --check simula_3
```

Roda mesmo se metadata estiver `incomplete_intent`.

---

#### História 0.3.3 — Recalcular completude após `--complete`

**Como** QA,  
**quero** que o valor informado no CLI seja considerado imediatamente,  
**para** não receber falso `FAIL` no readiness.

**Tarefas técnicas:**

- Após `prompt_missing_fields`, rodar novamente:
  - `RecordingNormalizer.normalize(...)`;
  - `IntentCompletenessChecker.check_steps(...)`;
  - `save_completeness_report(...)`.
- Passar o relatório atualizado para o readiness.
- Atualizar metadata de forma consistente.

**Critérios de aceite:**

- Campo pendente informado via CLI deixa de aparecer como pendente.
- Readiness não usa relatório antigo.
- Status final não volta indevidamente para `incomplete_intent`.

---

## 4. Sprint 1 — Gravador Não Intrusivo

### 4.1. Objetivo da Sprint

Transformar o recorder em um componente sensorial estável, que captura eventos e estado sem interferir visualmente na página, sem perder eventos em reload/postback e sem misturar sessões.

---

### Épico 1.1 — Evidence Safe Mode

#### História 1.1.1 — Criar níveis de evidência: `none`, `light`, `full`

**Como** time TestForge,  
**quero** configurar a profundidade da evidência,  
**para** usar coleta leve no piloto e coleta completa apenas em debug.

**Níveis propostos:**

```text
none:
  raw_events.jsonl
  recording_metadata.json
  final_state_snapshot.json

light:
  raw_events.jsonl
  recording_metadata.json
  field_snapshots.jsonl
  value_mutations.jsonl
  final_state_snapshot.json
  network_log.json
  completeness/readiness reports

full:
  tudo do light
  screenshots por evento
  DOM snapshots por evento
  evidência detalhada para healing/LLM
```

**Tarefas técnicas:**

- Criar configuração `evidence_level`.
- Definir `light` como padrão.
- Expor flag futura:

```powershell
--evidence-level none|light|full
```

- Atualizar metadata com nível usado.

**Critérios de aceite:**

- Gravação padrão usa `light`.
- `full` só é ativado explicitamente.
- O relatório informa limitações de cada nível.

---

#### História 1.1.2 — Captura final obrigatória

**Como** TestForge,  
**quero** capturar o estado final da tela no encerramento,  
**para** reconstruir valores mesmo sem capturar todos os eventos intermediários.

**Tarefas técnicas:**

- No `Shift+S`, gerar `final_state_snapshot.json`.
- Capturar:
  - inputs;
  - textareas;
  - selects;
  - checkboxes;
  - radios;
  - contenteditable;
  - elementos ARIA com valor;
  - campos visíveis e habilitados.
- Registrar identificadores:
  - id;
  - name;
  - label;
  - placeholder;
  - aria-label;
  - role;
  - tag;
  - bounding box.

**Critérios de aceite:**

- `final_state_snapshot.json` existe após toda gravação.
- Selects aparecem com `selected_value` e `selected_text`.
- Campos vazios e preenchidos são diferenciados.
- Falha de captura gera `FINAL_STATE_SNAPSHOT_FAILED`.

---

#### História 1.1.3 — DOM snapshot com validação de qualidade

**Como** TestForge,  
**quero** impedir DOM snapshots vazios,  
**para** não alimentar normalizer/healing com evidência inválida.

**Tarefas técnicas:**

- Validar tamanho mínimo do HTML antes de salvar.
- Não salvar arquivo 0 bytes.
- Registrar `DOM_SNAPSHOT_EMPTY` quando falhar.
- Criar resumo de qualidade:

```json
{
  "dom_snapshots_total": 10,
  "dom_snapshots_valid": 8,
  "dom_snapshots_empty": 2,
  "empty_rate": 0.2
}
```

**Critérios de aceite:**

- Nenhum arquivo `.html` com 0 bytes é criado.
- Se snapshot vazio ocorrer, fica explícito no relatório.
- Se mais de 50% estiverem vazios, status `needs_review`.

---

### Épico 1.2 — Persistência Resiliente de Eventos

#### História 1.2.1 — Persistir eventos antes de reload/postback

**Como** TestForge,  
**quero** salvar eventos imediatamente no browser,  
**para** não perder interações quando a página recarregar rapidamente.

**Tarefas técnicas:**

- Ao capturar evento, salvar em:
  - fila em memória;
  - `sessionStorage`.
- Ao fazer flush, drenar ambas as fontes.
- Deduplicar por assinatura:

```text
event_id ou timestamp + action + selector + value + url
```

**Critérios de aceite:**

- Select que dispara reload não perde evento.
- Evento antes de navegação aparece em `raw_events.jsonl`.
- Não há duplicidade após flush.

---

#### História 1.2.2 — `event_id` monotônico global

**Como** desenvolvedor,  
**quero** `event_id` único por gravação,  
**para** correlacionar evento, DOM, screenshot, field snapshot e semantic step.

**Tarefas técnicas:**

- Criar contador global por sessão Python, não por página JS.
- Se o JS gerar um ID local, o backend deve normalizar para ID global.
- Preservar ID monotônico em navegações.

**Critérios de aceite:**

- Nenhum `event_id` duplicado em `raw_events.jsonl`.
- Sequência segue `evt_000001`, `evt_000002`, etc.
- Teste automatizado falha se houver duplicidade.

---

#### História 1.2.3 — Nova gravação nunca anexa silenciosamente

**Como** QA,  
**quero** que nomes repetidos criem pastas incrementais,  
**para** não misturar fluxos.

**Tarefas técnicas:**

- Se `recordings/<name>` existir, criar `<name>_2`, `<name>_3`, etc.
- Registrar em metadata:

```json
{
  "requested_recording_id": "simax",
  "effective_recording_id": "simax_2"
}
```

**Critérios de aceite:**

- Segunda gravação com mesmo nome não altera a primeira.
- Não há append silencioso em `raw_events.jsonl`.
- Log informa nome efetivo da gravação.

---

## 5. Sprint 2 — Captura Básica Correta

### 5.1. Objetivo da Sprint

Resolver os erros mais básicos de captura: `select`, valores não capturados, campos mascarados, fills duplicados e prompt de completude.

---

### Épico 2.1 — Select Nativo como Cidadão de Primeira Classe

#### História 2.1.1 — Capturar mudança de `<select>`

**Como** QA,  
**quero** que UF, Edifício e Data sejam capturados corretamente,  
**para** reproduzir fluxos do SIMAX sem ajuste manual.

**Tarefas técnicas:**

- Capturar evento `change` em `select`.
- Salvar:
  - `tag=select`;
  - `id`;
  - `name`;
  - `selected_value`;
  - `selected_text`;
  - lista de options.
- Persistir antes de reload.
- Incluir select no final state snapshot.

**Critérios de aceite:**

Um select SIMAX gera evento com forma semelhante:

```json
{
  "action": "select",
  "tag": "select",
  "name": "lstUf",
  "id": "lstUf",
  "selected_value": "MT",
  "selected_text": "MT"
}
```

---

#### História 2.1.2 — Normalizer gera `select_option`

**Como** TestForge,  
**quero** transformar evento de select em ação semântica correta,  
**para** impedir que o compilador procure `input` inexistente.

**Tarefas técnicas:**

- Se `target.tag == select`, action semântica deve ser `select_option`.
- Escolher selector preferencial:
  1. `select[name="..."]`;
  2. `#id`;
  3. `select[aria-label="..."]`;
  4. select próximo ao label.
- Rejeitar candidato `label + input` para select.

**Critérios de aceite:**

- `semantic_steps.jsonl` contém `select_option`.
- Candidato principal aponta para `select`.
- Valor vem de `selected_value` ou `selected_text`.

---

#### História 2.1.3 — Compiler emite `page.select_option`

**Como** QA,  
**quero** que o script Playwright use API correta para select,  
**para** executar sem falso erro.

**Tarefas técnicas:**

- Implementar geração de `select_option` no compiler.
- Garantir que runtime/runner também suporte action `select_option`.
- Criar teste com página local de select.

**Critérios de aceite:**

Script esperado:

```python
page.select_option('select[name="lstUf"]', 'MT')
```

Não pode aparecer:

```python
page.click('label:has-text("UF") + input')
```

---

### Épico 2.2 — Fills Confiáveis

#### História 2.2.1 — Compactar fills sequenciais

**Como** QA,  
**quero** que digitação caractere por caractere vire um único fill,  
**para** reduzir ruído e falhas.

**Tarefas técnicas:**

- Agrupar fills consecutivos do mesmo campo.
- Usar janela de debounce configurável, ex. 500ms.
- Preservar apenas valor final.
- Registrar steps compactados.

**Critérios de aceite:**

Sequência:

```text
4
40
407
4078
```

vira:

```text
fill final = 4078
```

---

#### História 2.2.2 — Reconstruir valor por final state/snapshot

**Como** TestForge,  
**quero** recuperar valores que não emitiram evento confiável,  
**para** reduzir dependência do prompt manual.

**Tarefas técnicas:**

- Cruzar eventos de foco/click com final state.
- Se campo mudou e não há fill, sintetizar fill com source `final_state_snapshot`.
- Integrar com `field_value_map`.
- Indicar confiança da fonte.

**Critérios de aceite:**

- Campo preenchido mas sem input event aparece no `field_value_map`.
- Source é registrado.
- Completeness considera o campo resolvido ou resolvido com warning.

---

#### História 2.2.3 — Prompt CLI para valores realmente pendentes

**Como** QA,  
**quero** informar apenas o que o TestForge não conseguiu inferir,  
**para** evitar regravar.

**Tarefas técnicas:**

- Gerar lista de campos missing após reconstrução.
- Mostrar label, placeholder, selector provável e motivo.
- Salvar valor em `field_value_map.json` e `test_data.json`.
- Recalcular completude após input.

**Critérios de aceite:**

- Valor informado some da lista de pendentes.
- Metadata fica `intent_complete` se não houver outros problemas.
- Readiness não usa relatório antigo.

---

## 6. Sprint 3 — Contrato Semântico

### 6.1. Objetivo da Sprint

Eliminar ambiguidade entre os artefatos gerados e criar rastreabilidade completa entre gravação bruta, semântica, compilação e execução.

---

### Épico 3.1 — Contrato Oficial de Artefatos

#### História 3.1.1 — Documentar contrato dos artefatos

**Como** time TestForge,  
**quero** definir claramente o papel de cada arquivo,  
**para** evitar confusão operacional e bugs de contagem.

**Contrato proposto:**

```text
raw_events.jsonl:
  Tudo que o recorder capturou.

steps.jsonl:
  Asserts manuais, comandos auxiliares e legado.

semantic_steps.jsonl:
  Saída normalizada, auditável e executável.

test_data.json:
  Massa externa extraída ou informada.

field_value_map.json:
  Mapa campo-valor-intenção-fonte.

recording_metadata.json:
  Identidade, status, histórico e flags.

readiness_report.json/md:
  Decisão de prontidão.
```

**Critérios de aceite:**

- Documento em `docs/contrato-artefatos.md`.
- README aponta para esse contrato.
- Logs usam a mesma terminologia.

---

#### História 3.1.2 — Gerar `semantic_steps.jsonl` sempre

**Como** QA/dev,  
**quero** auditar os steps normalizados,  
**para** entender exatamente o que será compilado.

**Tarefas técnicas:**

- `compile` sempre gera `semantic_steps.jsonl`.
- Cada step contém:
  - `step_id`;
  - `action`;
  - `target`;
  - `value`;
  - `source_event_ids`;
  - `source`;
  - `skip_reason`, se aplicável;
  - `blocking`;
  - `depends_on`.

**Critérios de aceite:**

- `semantic_steps.jsonl` existe em toda compilação.
- Steps sintéticos são distinguíveis de eventos reais.
- QA consegue auditar por que um step existe.

---

#### História 3.1.3 — Corrigir contadores no log

**Como** QA,  
**quero** entender o que foi gravado, normalizado e executado,  
**para** confiar no TestForge.

**Tarefas técnicas:**

- Corrigir contagem de eventos brutos para ler `raw_events.jsonl`, não `steps.jsonl`.
- Exibir:

```text
Eventos brutos capturados: N
Steps semânticos gerados: M
Asserts manuais: K
Steps compactados: C
Steps ignorados: I
```

**Critérios de aceite:**

- Não aparece mais “Eventos brutos: 0” quando há raw events.
- Se N e M diferirem, o log explica por quê.

---

### Épico 3.2 — Navegação e Postback

#### História 3.2.1 — Evitar `goto()` excessivo

**Como** QA,  
**quero** que o script preserve o fluxo gravado,  
**para** não resetar estado no meio do teste.

**Tarefas técnicas:**

- `goto` apenas no início do script.
- Eventos de navegação posteriores são consequência de ação anterior.
- Marcar step com `causes_navigation=true` quando aplicável.

**Critérios de aceite:**

- Script gerado tem no máximo um `page.goto(BASE_URL)`.
- Navegações intermediárias usam espera ou consequência, não novo `goto` arbitrário.

---

#### História 3.2.2 — Classificar postback como consequência

**Como** TestForge,  
**quero** distinguir submit/postback de navegação isolada,  
**para** modelar corretamente páginas ASP/legadas.

**Tarefas técnicas:**

- Detectar POST/navigation após select/click/submit.
- Associar navegação ao step anterior.
- Registrar `postback_detected=true`.

**Critérios de aceite:**

- Select que provoca reload continua sendo um `select_option` com consequência.
- Não gera step de navegação solto e confuso.

---

## 7. Sprint 4 — Compilação e Execução Confiáveis

### 7.1. Objetivo da Sprint

Garantir que a intenção semântica gere script Playwright correto, compatível com o tipo de elemento e com assertions robustas.

---

### Épico 4.1 — Geração Correta por Tipo de Elemento

#### História 4.1.1 — Inferência centralizada de ação Playwright

**Como** desenvolvedor,  
**quero** uma função única de inferência de ação,  
**para** evitar inconsistências entre normalizer, compiler e runner.

**Mapeamento mínimo:**

```text
input[type=text]      -> fill
input[type=password]  -> fill
textarea              -> fill
select                -> select_option
checkbox              -> check/uncheck
radio                 -> check
button                -> click
a[href]               -> click + navigation se aplicável
input[type=file]      -> set_input_files
contenteditable       -> fill/content_edit
```

**Critérios de aceite:**

- Normalizer, compiler e runner usam a mesma semântica.
- Ação incompatível com tag gera erro de validação antes da execução.

---

#### História 4.1.2 — Validar script gerado

**Como** QA,  
**quero** que o script gerado seja validado,  
**para** não descobrir erro em runtime.

**Tarefas técnicas:**

- Rodar `compile(code, path, "exec")`.
- Validar se há selector vazio.
- Validar se action é compatível com tag.
- Bloquear script com problemas estruturais.

**Critérios de aceite:**

- Script inválido não é emitido como sucesso.
- Relatório indica step causador.

---

### Épico 4.2 — Assertions Robustas

#### História 4.2.1 — Evitar CSS estrutural em assert

**Como** QA,  
**quero** assertions por texto, role ou região,  
**para** reduzir fragilidade.

**Tarefas técnicas:**

- Penalizar CSS longo para assert.
- Preferir:
  - `get_by_text`;
  - `get_by_role`;
  - `body contains text`;
  - região estável.

**Critérios de aceite:**

- Assert não usa cadeia CSS profunda como primeira opção.
- Mudança visual pequena não quebra assert.

---

#### História 4.2.2 — Remover valores dinâmicos de seletores de resultado

**Como** QA,  
**quero** reexecutar com massa diferente,  
**para** não quebrar por valor monetário gravado.

**Tarefas técnicas:**

- Detectar padrões monetários, datas e números dinâmicos em texto de resultado.
- Gerar assert por texto base:

```text
Valor mínimo de entrada
Valor máximo de financiamento
```

- Não usar o valor exato como selector principal.

**Critérios de aceite:**

- Resultado `R$ 13.514,64` gravado não impede execução com `R$ 42.000,00`.
- Assert continua validando a presença do item de negócio.

---

## 8. Sprint 5 — Métricas, Readiness e Relatórios

### 8.1. Objetivo da Sprint

Tornar o resultado da execução confiável, compreensível e mensurável.

---

### Épico 5.1 — Execução Incremental e Bloqueios

#### História 5.1.1 — Steps dependentes bloqueados após falha crítica

**Como** QA,  
**quero** que falha em UF bloqueie Edifício/Data,  
**para** evitar cascata de falhas enganosas.

**Tarefas técnicas:**

- Adicionar `blocking=true` em steps críticos.
- Inferir dependências simples:
  - Edifício depende de UF;
  - Data depende de Edifício;
  - Botão depende de campos obrigatórios.
- Marcar dependentes como `blocked_by_previous_failure`.

**Critérios de aceite:**

- Falha raiz aparece separada das cascatas.
- Métricas não contam cascata como bugs independentes.

---

#### História 5.1.2 — Steps pulados explicados

**Como** QA,  
**quero** ver todo step pulado com motivo,  
**para** auditar a execução.

**Tarefas técnicas:**

- Registrar `skip_reason` no semantic step.
- Logar:

```text
Step 15: skipped — duplicate_fill_compacted
Step 16: skipped — blocked_by_previous_failure
```

**Critérios de aceite:**

- Numeração não “some”.
- Relatório completo mostra todos os steps.

---

### Épico 5.2 — Métricas Confiáveis

#### História 5.2.1 — Separar métricas de healing

**Como** time TestForge,  
**quero** métricas consistentes,  
**para** avaliar o produto com honestidade.

**Métricas mínimas:**

```text
falhas_detectadas
healings_tentados
healings_aplicados
healings_validados
healings_rejeitados
oracles_passed
oracles_failed
blocked_steps
skipped_steps
```

**Critérios de aceite:**

- Resumo do terminal bate com JSON.
- Healing só é “validado” se oracle/postcondition aprovar.
- Falso healing é separado de falha comum.

---

#### História 5.2.2 — Relatório completo sem truncamento

**Como** desenvolvedor,  
**quero** ver candidatos, erros e healing completos em arquivo,  
**para** depurar sem depender do terminal.

**Tarefas técnicas:**

- Terminal mostra resumo curto.
- `execution_report.json` salva detalhes completos.
- `healing_report.md` mostra diagnóstico legível.

**Critérios de aceite:**

- Lista completa de candidatos é salva.
- Erro completo não é truncado no JSON.
- Relatório informa selector original, selector usado e selector curado.

---

### Épico 5.3 — Readiness Gate Confiável

#### História 5.3.1 — Readiness usa completude atualizada

**Como** QA,  
**quero** que valores informados sejam considerados,  
**para** evitar falso fail.

**Tarefas técnicas:**

- Recalcular completude antes do gate.
- Se execução incremental não rodou, reportar `steps_not_executed`, não `steps_failed`.
- Diferenciar:
  - completude falhou;
  - execução não feita;
  - execução feita e falhou.

**Critérios de aceite:**

- Readiness não mostra “Steps: 0 ok, 0 falha” como se fosse execução falha.
- Valores `user_supplied_cli` aparecem como resolvidos.

---

#### História 5.3.2 — Status coerente da gravação

**Como** TestForge,  
**quero** status consistentes,  
**para** controlar compile e envio ao time.

**Estados mínimos:**

```text
completed_raw
intent_complete
incomplete_intent
needs_review
ready_for_team
```

**Critérios de aceite:**

- Compile real bloqueia `incomplete_intent`.
- `compile --check` sempre roda.
- Metadata tem histórico com motivo e timestamp.

---

## 9. Sprint 6 — Limpeza, Documentação e Piloto

### 9.1. Objetivo da Sprint

Limpar complexidade residual, documentar o fluxo real e preparar o TestForge para uso por QAs.

---

### Épico 6.1 — Qualidade de Locators

#### História 6.1.1 — Penalizar texto genérico

**Como** TestForge,  
**quero** evitar candidatos como `text=Selecione`,  
**para** reduzir falso healing e seleção errada.

**Tarefas técnicas:**

- Criar lista de textos genéricos:

```text
Selecione
OK
Cancelar
Sim
Não
Página inicial
Calcular sem escopo
```

- Penalizar score sem descartar completamente.
- Permitir uso apenas com escopo/contexto.

**Critérios de aceite:**

- `text=Selecione` nunca é candidato principal para UF.
- Relatório explica penalidade.

---

#### História 6.1.2 — Rejeitar bounding box zero

**Como** TestForge,  
**quero** ignorar alvo não acionável,  
**para** evitar steps inválidos.

**Tarefas técnicas:**

- Validar área > 0.
- Se alvo for filho invisível, subir para ancestral acionável.
- Se não encontrar, marcar `needs_review`.

**Critérios de aceite:**

- Nenhum step principal usa elemento com width/height zero.
- Bounding box suspeito aparece em relatório de qualidade.

---

### Épico 6.2 — DX e Empacotamento

#### História 6.2.1 — URL com `&` no PowerShell

**Como** QA em Windows,  
**quero** alerta para URL truncada ou sem aspas,  
**para** evitar comandos quebrados.

**Critérios de aceite:**

- CLI detecta URL suspeita.
- Mensagem orienta usar aspas.
- Tutorial tem exemplo PowerShell.

---

#### História 6.2.2 — Dependências completas

**Como** desenvolvedor,  
**quero** instalação limpa funcionando,  
**para** evitar erro de dependência.

**Critérios de aceite:**

- `httpx` declarado em requirements/pyproject.
- Ambiente limpo executa `python -m testforge.cli.app --help`.
- Teste automatizado valida imports principais.

---

### Épico 6.3 — Documentação do Piloto

#### História 6.3.1 — Atualizar tutorial sem CDP

**Como** QA,  
**quero** comandos simples e estáveis,  
**para** gravar sem confusão.

**Conteúdo mínimo:**

```powershell
python -m testforge.cli.app record --browser chrome --complete "URL" --name nome
python -m testforge.cli.app compile --check nome
python -m testforge.cli.app compile nome --data
```

**Critérios de aceite:**

- Tutorial não usa CDP como recomendação.
- Explica o que fazer se campo não for capturado.
- Explica quais artefatos enviar ao time.

---

#### História 6.3.2 — Checklist operacional do piloto

**Como** time TestForge,  
**quero** checklist antes/depois da gravação,  
**para** padronizar coleta com 5 a 10 QAs.

**Checklist proposto:**

```text
Antes:
1. Ativar .venv.
2. Confirmar que python -m testforge.cli.app --help funciona.
3. Escolher Chrome ou Edge.
4. Definir nome único da gravação.

Durante:
5. Rodar record com --complete.
6. Gravar fluxo curto e objetivo.
7. Finalizar com Shift+S.
8. Informar valores pendentes, se solicitado.

Depois:
9. Rodar compile --check.
10. Conferir completeness/readiness report.
11. Zipar pasta recordings/<id>.
12. Enviar artefatos ao repositório/pasta combinada.
```

**Critérios de aceite:**

- QA consegue seguir sem ajuda de dev.
- Checklist cabe em uma página.
- Artefatos enviados são suficientes para análise.

---

## 10. Mapeamento dos Bugs para Sprints

| Bug | Tema | Sprint |
|---|---|---|
| BUG-001 | `<select>` vira `input` / falta `select_option` | Sprint 2 |
| BUG-002 | DOM snapshots vazios | Sprint 1 |
| BUG-003 | Contagem divergente | Sprint 3 |
| BUG-004 | `event_id` reinicia | Sprint 1 |
| BUG-005 | Sessões anexadas | Sprint 1 |
| BUG-006 | Browser/CDP | Sprint 0, removido do piloto |
| BUG-007 | Flick/reload visual | Sprint 0 e Sprint 1 |
| BUG-008 | Digitação vira muitos fills | Sprint 2 |
| BUG-009 | `goto()` excessivo | Sprint 3 |
| BUG-010 | Healer sugere texto genérico | Sprint 6 |
| BUG-011 | Métricas inconsistentes | Sprint 5 |
| BUG-012 | Assertions frágeis | Sprint 4 |
| BUG-013 | Bounding box zero | Sprint 6 |
| BUG-014 | `httpx` ausente | Sprint 6 |
| BUG-015 | URL com `&` no PowerShell | Sprint 6 |
| BUG-016 | Logs truncados | Sprint 5 |
| BUG-017 | Steps pulados sem explicação | Sprint 5 |
| BUG-018 | Sem `semantic_steps.jsonl` auditável | Sprint 3 |
| BUG-019 | Falha em cascata | Sprint 5 |
| BUG-020 | Contrato instável entre artefatos | Sprint 3 |

---

## 11. Ordem Recomendada de Implementação

### Bloco A — Parar o flick e simplificar piloto

1. Remover CDP do fluxo principal.
2. Desabilitar screenshot por evento.
3. Não alterar viewport em gravação headed.
4. Criar `viewport_trace.jsonl`.
5. Validar gravação SIMAX sem página diminuir/voltar.

### Bloco B — Capturar campos básicos

6. Persistir eventos antes de reload.
7. Capturar `select` com valor/texto/options.
8. Normalizer gera `select_option`.
9. Compiler emite `page.select_option`.
10. Compactar fills sequenciais.

### Bloco C — Corrigir CLI e completude

11. URL obrigatória.
12. `compile --check` não bloqueado.
13. `--complete` recalcula completude.
14. Readiness usa relatório atualizado.
15. Mensagens orientam `python -m`, não `testforge.exe`.

### Bloco D — Contrato e auditoria

16. Gerar `semantic_steps.jsonl` sempre.
17. Corrigir contadores.
18. Documentar contrato de artefatos.
19. Explicar steps compactados/pulados.

### Bloco E — Preparar piloto

20. Atualizar tutorial sem CDP.
21. Criar checklist do QA.
22. Definir pacote de artefatos a enviar.
23. Gerar relatório consolidado após piloto.

---

## 12. Definição de Pronto para Enviar Amanhã

O TestForge estará pronto para a bateria inicial de gravação se os seguintes testes passarem:

### CT-PILOTO-01 — Gravar SIMAX sem flick

**Comando:**

```powershell
python -m testforge.cli.app record --browser chrome --complete "https://simax.caixa/simax/" --name simax_piloto_001
```

**Aceite:**

- página não diminui e volta a cada interação;
- gravação finaliza com Shift+S;
- metadata registra `evidence_level=light`.

---

### CT-PILOTO-02 — Capturar select UF

**Aceite:**

- `raw_events.jsonl` ou `field_value_map.json` contém `select`, `name/id` e valor;
- `semantic_steps.jsonl` contém `select_option`.

---

### CT-PILOTO-03 — Corrigir campo pendente via CLI

**Aceite:**

- CLI pergunta valor pendente;
- valor informado aparece em `field_value_map.json`;
- completude é recalculada;
- status não volta indevidamente para `incomplete_intent`.

---

### CT-PILOTO-04 — `compile --check` funciona em gravação incompleta

**Comando:**

```powershell
python -m testforge.cli.app compile --check simax_piloto_001
```

**Aceite:**

- comando gera relatório;
- não bloqueia por status;
- não depende de `testforge.exe`.

---

### CT-PILOTO-05 — Compilar script auditável

**Comando:**

```powershell
python -m testforge.cli.app compile simax_piloto_001 --data
```

**Aceite:**

- script gerado compila sem SyntaxError;
- `semantic_steps.jsonl` existe;
- select vira `select_option`;
- `test_data.json` é gerado quando aplicável.

---

## 13. Riscos e Mitigações

### Risco 1 — Flick persistir mesmo sem screenshot por evento

**Mitigação:** usar `viewport_trace.jsonl` para identificar fase. Se viewport não mudar, investigar CSS/layout da aplicação ou operação de flush/event listener.

### Risco 2 — Chrome/Edge normal bloqueado por política corporativa

**Mitigação:** documentar como limitação operacional. CDP pode ser mantido como fallback experimental, mas não deve ser default do piloto.

### Risco 3 — Select com postback ainda perder evento

**Mitigação:** persistir evento no `sessionStorage` antes da navegação e usar final state/form values como fallback.

### Risco 4 — Readiness reprovar por não executar incrementalmente

**Mitigação:** diferenciar `not_executed` de `failed`. Não marcar como `ready_for_team` sem execução, mas também não chamar isso de falha falsa.

### Risco 5 — QA enviar artefato incompleto

**Mitigação:** checklist operacional e relatório de completude simples, com status e próximos passos.

---

## 14. Conclusão

O foco imediato deve ser estabilizar o núcleo básico do TestForge:

```text
gravar sem interferir
capturar campos básicos
preservar eventos
normalizar intenção
compilar ação correta
gerar relatório honesto
```

A remoção do CDP do fluxo principal e a redução de evidência intrusiva são decisões importantes para reduzir variáveis. A partir daí, as sprints organizam a correção dos bugs conhecidos de forma incremental, testável e alinhada ao objetivo do piloto com QAs.
