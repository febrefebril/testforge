# TESTFORGE — healing-strategies.md

**Projeto:** TestForge / Agente Curador de Scripts  
**Artefato:** Contrato implementável das estratégias de healing  
**Versão:** 1.0  
**Base:** Taxonomia Implementável de Casos Conhecidos — v1.0  
**Finalidade:** Definir o contrato técnico, os critérios de uso, entradas, saídas, pré-condições, pós-condições, evidências e regras de validação de cada estratégia utilizada pelo Curador do TestForge.

---

## 1. Objetivo

Este documento especifica o contrato implementável das estratégias de healing e tratamento usadas pelo Agente Curador do TestForge.

A taxonomia define **o que foi detectado**.  
Este documento define **como cada estratégia deve agir**.

Cada estratégia deve ser implementada como uma unidade rastreável, auditável e validável, capaz de:

1. Receber evidências da gravação, execução ou curadoria.
2. Avaliar se é aplicável ao caso detectado.
3. Propor uma alteração ou decisão segura.
4. Registrar justificativa vinculada a um ID taxonômico.
5. Gerar patch, metadado, checkpoint ou estado final.
6. Permitir validação pelo `PatchValidator`, `ImplementationAuditor` ou mecanismo equivalente.

---

## 2. Princípios de Implementação

### 2.1 Nenhuma estratégia deve inventar evidência

Uma estratégia só pode produzir locator, assert, wait, patch ou checkpoint quando houver evidência mínima suficiente.

Se a evidência for insuficiente, a estratégia deve retornar:

- `MANUAL_REQUIRED`, quando houver necessidade explícita de decisão humana; ou
- `UNRESOLVED`, quando não for possível resolver com segurança.

### 2.2 Toda alteração deve ser rastreável

Qualquer patch aplicado ao script final deve referenciar:

- ID taxonômico;
- estratégia utilizada;
- evidência usada;
- trecho alterado;
- justificativa;
- resultado da validação.

### 2.3 Estratégias não substituem validação

Uma estratégia pode propor healing, mas não deve considerar o caso resolvido sozinha.

A resolução depende de validação por execução, auditoria ou regra objetiva definida no caso taxonômico.

### 2.4 Segurança prevalece sobre automação

Nos seguintes casos, a estratégia deve preferir checkpoint manual ou não resolução segura:

- CAPTCHA;
- iframe cross-origin inacessível;
- Shadow DOM fechado;
- operação irreversível;
- dado sensível não mascarado;
- assert ambíguo;
- ausência de evidência mínima;
- risco de alterar comportamento de negócio.

---

## 3. Modelo Geral de Contrato

Todas as estratégias devem seguir este contrato conceitual:

```yaml
strategy_id: nome_da_estrategia
description: descrição objetiva da estratégia
applicable_taxonomy_ids:
  - SEL-001
  - TIM-001
inputs:
  required:
    - evidence_bundle
    - current_step
    - taxonomy_case
  optional:
    - dom_snapshot
    - network_trace
    - console_logs
    - user_annotations
    - previous_attempts
preconditions:
  - condição necessária para aplicar a estratégia
outputs:
  success:
    - patch_proposal
    - confidence_score
    - evidence_references
  partial:
    - partial_patch
    - warning
  failure:
    - rejection_reason
    - recommended_next_strategy
result_states:
  success: RESOLVED
  partial: PARTIALLY_RESOLVED
  manual: MANUAL_REQUIRED
  failure: UNRESOLVED
validation:
  - regra objetiva de validação
observability:
  - logs obrigatórios
  - evidências anexadas
risk_policy:
  - limites e bloqueios
```

---

## 4. Estrutura Recomendada de Interface

A implementação pode adaptar nomes e tipos, mas deve preservar a semântica abaixo.

```python
from dataclasses import dataclass
from typing import Any, Literal

ResultState = Literal[
    "RESOLVED",
    "PARTIALLY_RESOLVED",
    "MANUAL_REQUIRED",
    "UNRESOLVED",
    "REJECTED",
]

@dataclass
class StrategyContext:
    taxonomy_id: str
    family: str
    current_step: dict[str, Any]
    recorded_action: dict[str, Any] | None
    dom_snapshot: dict[str, Any] | None
    accessibility_snapshot: dict[str, Any] | None
    network_trace: list[dict[str, Any]]
    console_logs: list[dict[str, Any]]
    user_annotations: list[dict[str, Any]]
    execution_error: dict[str, Any] | None
    previous_attempts: list[dict[str, Any]]

@dataclass
class StrategyResult:
    strategy_id: str
    taxonomy_id: str
    state: ResultState
    confidence: float
    patch: dict[str, Any] | None
    evidence: list[dict[str, Any]]
    warnings: list[str]
    next_strategy: str | None
    rationale: str

class HealingStrategy:
    strategy_id: str

    def can_apply(self, context: StrategyContext) -> bool:
        raise NotImplementedError

    def apply(self, context: StrategyContext) -> StrategyResult:
        raise NotImplementedError
```

---

## 5. Estratégias

---

# 5.1 `label_proximity`

## Finalidade

Inferir um locator resiliente a partir da proximidade entre um rótulo visual e o campo, botão ou componente associado.

## Casos taxonômicos relacionados

- `SEL-002` — ID com índice de tabela
- `SEL-009` — Texto duplicado
- `SEL-010` — Label não associado via `for`
- `AST-009` — Assert de tabela/lista

## Quando aplicar

Aplicar quando:

- o elemento não possui ID estável;
- o label existe visualmente, mas não está semanticamente associado;
- há múltiplos textos iguais e o escopo precisa ser reduzido;
- o elemento correto pode ser inferido por proximidade estrutural, espacial ou hierárquica.

## Entradas mínimas

- DOM snapshot;
- texto do label ou texto próximo;
- ação gravada ou assert pretendido;
- posição estrutural do elemento no DOM;
- candidatos próximos.

## Saída esperada

Locator Playwright contextualizado por label, container, linha ou escopo.

Exemplo:

```python
page.get_by_text("CPF").locator(".. ").get_by_role("textbox")
```

Preferencialmente, quando possível:

```python
page.get_by_label("CPF")
```

Ou, para tabela:

```python
page.get_by_role("row", name="João Silva").get_by_role("button", name="Editar")
```

## Critérios de sucesso

- O locator retorna match único; ou
- O escopo do locator é explícito e justificado;
- A ação ocorre no elemento correto;
- Não há dependência de índice absoluto sem justificativa.

## Regras de rejeição

Rejeitar se:

- houver mais de um candidato indistinguível;
- o label for ambíguo;
- a proximidade não puder ser comprovada;
- a estratégia depender apenas de coordenadas absolutas.

## Estado em falha

- `MANUAL_REQUIRED`, se a intenção do usuário for necessária.
- `UNRESOLVED`, se houver evidência insuficiente.

---

# 5.2 `text_content_match`

## Finalidade

Gerar locators ou asserts baseados em texto visível, conteúdo textual ou mensagens de negócio.

## Casos taxonômicos relacionados

- `SEL-001`
- `SEL-004`
- `SEL-009`
- `AST-004`
- `AST-009`
- `AST-010`

## Quando aplicar

Aplicar quando:

- o texto visível é a evidência mais estável;
- a validação esperada é textual;
- o elemento pode ser identificado por mensagem, título, célula, opção ou conteúdo.

## Entradas mínimas

- texto alvo;
- escopo da tela, modal, frame ou container;
- tipo de assert ou ação;
- snapshot textual.

## Saída esperada

Locator ou assert textual.

```python
expect(page.get_by_text("Operação realizada com sucesso")).to_be_visible()
```

Para textos variáveis:

```python
expect(page.get_by_text(re.compile(r"Protocolo .* gerado"))).to_be_visible()
```

## Critérios de sucesso

- Texto encontrado no escopo correto;
- Assert não depende de texto dinâmico completo quando houver padrão variável;
- Duplicidade tratada por escopo.

## Regras de rejeição

Rejeitar se:

- o texto for genérico demais, como “OK”, “Sim”, “Avançar”, sem escopo;
- houver múltiplos matches sem desambiguação;
- o texto for apenas placeholder temporário, skeleton ou loading.

---

# 5.3 `aria_role_strategy`

## Finalidade

Converter interações e asserts para locators baseados em acessibilidade, usando roles, nomes acessíveis e estados ARIA.

## Casos taxonômicos relacionados

- `SEL-003`
- `SEL-005`
- `SEL-006`
- `SEL-007`
- `SEL-008`
- `CTX-006`
- `INP-010`
- `AST-007`

## Quando aplicar

Aplicar quando:

- o componente possui role acessível;
- há nome acessível confiável;
- classes ou IDs são instáveis;
- o componente é customizado, mas expõe semântica ARIA.

## Entradas mínimas

- accessibility snapshot;
- role do elemento;
- nome acessível;
- estado esperado, quando aplicável.

## Saída esperada

```python
page.get_by_role("button", name="Salvar").click()
```

```python
expect(page.get_by_role("button", name="Enviar")).to_be_enabled()
```

## Critérios de sucesso

- Locator por role retorna elemento correto;
- Nome acessível é estável;
- Estado ARIA é validável.

## Regras de rejeição

Rejeitar se:

- o role for genérico sem nome acessível;
- o nome acessível mudar conforme dados voláteis;
- o componente não expuser semântica confiável.

---

# 5.4 `semantic_locator_conversion`

## Finalidade

Substituir seletores frágeis por locators Playwright semânticos e resilientes.

## Casos taxonômicos relacionados

- `SEL-001`
- `SEL-004`
- `SEL-008`
- `DOM-002`

## Quando aplicar

Aplicar quando o script contém:

- XPath absoluto;
- CSS estrutural frágil;
- `.nth()` sem justificativa;
- ID dinâmico;
- índice de tabela;
- seletor dependente de estrutura volátil.

## Entradas mínimas

- seletor original;
- DOM snapshot;
- accessibility snapshot;
- ação pretendida;
- candidatos equivalentes.

## Saída esperada

Substituição do seletor por locator semântico.

Antes:

```python
page.locator("/html/body/div[2]/form/table/tbody/tr[3]/td[5]/button").click()
```

Depois:

```python
page.get_by_role("row", name="Contrato 12345").get_by_role("button", name="Editar").click()
```

## Critérios de sucesso

- XPath absoluto removido;
- `.nth()` removido ou documentado;
- locator passa em execuções repetidas;
- alteração vinculada ao ID taxonômico.

## Regras de rejeição

Rejeitar se a conversão alterar a intenção da ação ou não houver evidência do elemento correto.

---

# 5.5 `primefaces_registry_scan`

## Finalidade

Usar informações do ecossistema PrimeFaces para identificar componentes, mas sem gerar dependência frágil de `widgetVar` quando isso puder variar.

## Casos taxonômicos relacionados

- `SEL-001`
- `SEL-003`
- `SEL-007`
- `CTX-006`
- `INP-001`

## Quando aplicar

Aplicar quando:

- houver JSF/PrimeFaces detectado;
- o script usar `PF('...')` diretamente;
- componentes PrimeFaces estiverem encapsulados;
- modal, tabela, autocomplete ou upload dependerem da estrutura PrimeFaces.

## Entradas mínimas

- fingerprint tecnológico;
- DOM snapshot;
- evidência de PrimeFaces;
- seletor/widget original;
- componente visual correspondente.

## Saída esperada

Locator semântico independente de `widgetVar`, ou metadado auxiliar de diagnóstico.

## Critérios de sucesso

- Script final não depende exclusivamente de `PF('widgetVar')`;
- Componente é localizado por intenção visível ou semântica;
- Quando `widgetVar` for mantido, deve haver justificativa técnica.

## Regras de rejeição

Rejeitar se o registry for usado para fabricar relação não comprovada entre widget e elemento.

---

# 5.6 `frame_reacquire`

## Finalidade

Reobter frame ou frameLocator após carregamento, recarregamento, detach/attach ou mudança de contexto.

## Casos taxonômicos relacionados

- `CTX-001`
- `CTX-005`
- `CTX-007`
- `INP-006`

## Quando aplicar

Aplicar quando:

- elemento está dentro de iframe same-origin;
- frame foi recarregado;
- handle antigo falhou;
- editor rico usa iframe;
- nova página ou popup exige troca de contexto.

## Entradas mínimas

- lista de frames;
- URL/name/title do frame, se disponível;
- seletor ou evidência do elemento interno;
- erro de execução, se houver.

## Saída esperada

```python
frame = page.frame_locator("iframe[title='Editor']")
frame.get_by_role("textbox").fill("Texto")
```

Ou, para popup:

```python
with page.expect_popup() as popup_info:
    page.get_by_role("link", name="Abrir detalhe").click()
new_page = popup_info.value
```

## Critérios de sucesso

- Nenhum frame handle obsoleto é reutilizado;
- A ação ocorre no contexto correto;
- Cross-origin inacessível não é tratado como same-origin.

## Regras de rejeição

Rejeitar se:

- o frame for cross-origin inacessível;
- não houver forma segura de identificar o frame;
- a estratégia tentar inspecionar DOM bloqueado por política do browser.

---

# 5.7 `shadow_pierce`

## Finalidade

Permitir localização de elementos dentro de Shadow DOM aberto quando suportado pelo mecanismo de teste.

## Casos taxonômicos relacionados

- `CTX-003`
- `CTX-004`

## Quando aplicar

Aplicar quando:

- componente usa Shadow DOM aberto;
- o elemento alvo está dentro de shadow root acessível;
- Playwright consegue atravessar a árvore de forma suportada.

## Entradas mínimas

- evidência de shadow root;
- tipo: aberto ou fechado;
- elemento alvo;
- seletor semântico possível.

## Saída esperada

Locator compatível com Playwright para Shadow DOM aberto.

## Critérios de sucesso

- Elemento localizado dentro do shadow root aberto;
- Não há tentativa de inspecionar shadow root fechado.

## Regras de rejeição

Se o Shadow DOM for fechado, retornar `MANUAL_REQUIRED` ou `UNRESOLVED` com justificativa.

---

# 5.8 `network_idle_wait`

## Finalidade

Inserir espera baseada em atividade de rede quando uma ação dispara carregamentos assíncronos relevantes.

## Casos taxonômicos relacionados

- `TIM-001`
- `TIM-003`
- `TIM-005`
- `TIM-007`
- `DOM-005`

## Quando aplicar

Aplicar quando:

- ação dispara XHR/fetch/AJAX;
- há atualização de tela após resposta;
- `waitForTimeout` foi usado como workaround;
- o próximo step depende da conclusão de rede.

## Entradas mínimas

- network trace;
- ação anterior;
- próximo elemento/estado esperado;
- evidência de requisição relevante.

## Saída esperada

Espera semântica combinando rede e condição observável.

```python
with page.expect_response(lambda r: "/consulta" in r.url and r.status == 200):
    page.get_by_role("button", name="Pesquisar").click()

expect(page.get_by_text("Resultado da pesquisa")).to_be_visible()
```

## Critérios de sucesso

- Remove sleep fixo;
- Aguarda resposta ou estabilidade relevante;
- Próximo step encontra estado atualizado.

## Regras de rejeição

Rejeitar se:

- a rede não tiver correlação com a mudança observável;
- `networkidle` for usado como substituto genérico sem condição de negócio.

---

# 5.9 `response_intercept`

## Finalidade

Correlacionar ações da UI com respostas HTTP/API para waits, asserts, diagnóstico ou validação de artefatos.

## Casos taxonômicos relacionados

- `TIM-003`
- `INP-004`
- `OBS-003`
- `AST-006`

## Quando aplicar

Aplicar quando:

- a mudança relevante vem de XHR/fetch;
- download é gerado por Blob ou resposta assíncrona;
- falha pode ser explicada por HTTP 4xx/5xx;
- assert de negócio depende de resposta.

## Entradas mínimas

- network trace;
- endpoint candidato;
- ação correlacionada;
- status code;
- headers relevantes, quando disponíveis.

## Saída esperada

Wait, assert ou diagnóstico baseado em resposta.

```python
with page.expect_response(lambda r: "/api/contratos" in r.url and r.status == 200):
    page.get_by_role("button", name="Consultar").click()
```

## Critérios de sucesso

- Resposta correlacionada à ação;
- Status esperado validado;
- Falhas HTTP são classificadas como rede/app, não como problema de locator.

## Regras de rejeição

Rejeitar se o endpoint não puder ser correlacionado com o step.

---

# 5.10 `dom_stabilization`

## Finalidade

Aguardar estabilização de DOM após re-render, AJAX, troca parcial de tela ou change detection.

## Casos taxonômicos relacionados

- `TIM-001`
- `TIM-004`
- `TIM-007`
- `DOM-003`
- `DOM-005`

## Quando aplicar

Aplicar quando:

- o DOM é substituído após ação;
- elemento fica detached;
- assert lê valor antigo;
- tela usa skeleton/loading;
- SPA troca componente sem reload completo.

## Entradas mínimas

- DOM snapshot antes/depois;
- ação disparadora;
- condição final esperada;
- seletor/estado marcador de prontidão.

## Saída esperada

Wait por condição de UI estável.

```python
page.get_by_role("button", name="Salvar").click()
expect(page.get_by_text("Salvo com sucesso")).to_be_visible()
```

Ou:

```python
page.wait_for_function("""
() => !document.querySelector('.loading,.spinner,.skeleton')
""")
```

## Critérios de sucesso

- Próxima ação ocorre após o estado final;
- Não há uso de timeout fixo como solução principal;
- Elementos são rebuscados após re-render.

## Regras de rejeição

Rejeitar se a condição de estabilidade for genérica demais ou não relacionada ao fluxo.

---

# 5.11 `overlay_dismiss`

## Finalidade

Detectar e remover overlays, bloqueadores visuais ou modais que interceptam cliques.

## Casos taxonômicos relacionados

- `STA-002`
- `CTX-006`
- `SEL-007`

## Quando aplicar

Aplicar quando:

- erro indica elemento coberto;
- overlay intercepta pointer events;
- modal está visível;
- tela possui bloqueador de carregamento.

## Entradas mínimas

- erro Playwright;
- DOM snapshot;
- overlay candidato;
- ação bloqueada.

## Saída esperada

Tratamento antes da ação alvo.

```python
expect(page.locator(".ui-blockui,.modal-backdrop,.loading-overlay")).to_be_hidden()
page.get_by_role("button", name="Confirmar").click()
```

Ou:

```python
page.keyboard.press("Escape")
```

Somente quando houver evidência de que ESC é comportamento esperado.

## Critérios de sucesso

- Overlay desaparece;
- Clique ocorre no elemento alvo;
- Não há clique forçado sem justificativa.

## Regras de rejeição

Rejeitar se a estratégia precisar usar `force=True` sem evidência suficiente.

---

# 5.12 `re_auth_hook`

## Finalidade

Isolar e acionar fluxo de autenticação ou reautenticação quando sessão expira.

## Casos taxonômicos relacionados

- `STA-001`
- `FILE-005`

## Quando aplicar

Aplicar quando:

- URL redireciona para login;
- texto indica sessão expirada;
- download falha por ausência de sessão;
- perfil autenticado não está disponível.

## Entradas mínimas

- URL atual;
- mensagem visível;
- estado de sessão;
- política de autenticação do ambiente de teste.

## Saída esperada

Chamada a fixture/hook de autenticação, sem persistir credenciais em claro.

```python
auth.ensure_authenticated(page)
```

## Critérios de sucesso

- Teste retorna ao ponto esperado;
- Credenciais não são gravadas no script;
- Sessão é tratada por fixture segura.

## Regras de rejeição

Rejeitar se exigir captura de senha, token ou segredo em claro.

---

# 5.13 `llm_healer` (antigo `llm_selector_inference`)

## Finalidade

Usar inferência assistida por LLM com prompt enxuto (~500 tok) para sugerir locator, assert ou cura quando heurísticas determinísticas e agentes especialistas não forem suficientes.

Este componente é a Layer 3b do pipeline de cura. Ele recebe um payload já estruturado pelo **Evidence Collector (Layer 3a)**, eliminando a necessidade de contexto completo bruto (~2000 tok).

## Casos taxonômicos relacionados

- `SEL-001`
- `SEL-002`
- `SEL-009`
- `AST-003`

## Quando aplicar

Aplicar apenas como fallback, quando:

- Layers 1 e 2 falharam;
- Evidence Collector produziu payload estruturado suficiente;
- a inferência pode ser validada objetivamente;
- não há risco de inventar intenção.

## Entradas mínimas

- **Payload do Evidence Collector (obrigatório):**
  - DOM snapshot sanitizado;
  - Screenshot (base64, opcional);
  - Console errors;
  - Network state (últimas N requisições);
  - Contexto dos steps anteriores;
  - Erro original + failure_signature;
- ação pretendida;
- candidatos (se houver);
- restrições de segurança.

## Saída esperada

Proposta estruturada de cura com:
```yaml
cure_proposal:
  taxonomy_id: SEL-004
  family: FAM-01
  strategy: semantic_locator_conversion
  new_locator: "page.get_by_role('button', name='Salvar')"
  confidence: 0.87
  rationale: "XPath absoluto quebrou; ARIA name 'Salvar' estável"
```

A proposta é então validada pelo **Curador Automático (Layer 3c)** — que executa o step, verifica o resultado e, se aprovado, registra a cura no catálogo como `learned`.

## Critérios de sucesso

- Prompt < 600 tokens (vs ~2000 tok do modelo anterior);
- Sugestão validada por execução pelo Curador Automático;
- Evidência anexada;
- Patch aprovado pelo validador;
- Não há dado sensível exposto ao modelo.

## Regras de rejeição

Rejeitar se:

- a LLM inventar elemento, intenção ou assert;
- a confiança for baixa;
- o DOM contiver dado sensível não mascarado;
- não houver validação objetiva;
- o Evidence Collector não forneceu payload suficiente.

---

# 5.14 `download_event_capture`

## Finalidade

Capturar, parametrizar e validar downloads disparados pela aplicação.

## Casos taxonômicos relacionados

- `INP-003`
- `INP-004`
- `FILE-004`
- `FILE-005`
- `FILE-006`
- `AST-006`

## Quando aplicar

Aplicar quando:

- ação gera arquivo;
- download precisa ser validado;
- nome do arquivo é dinâmico;
- download depende de sessão;
- arquivo abre em popup, aba ou viewer.

## Entradas mínimas

- ação disparadora;
- evento download ou resposta de rede;
- metadados esperados do arquivo;
- regra de validação.

## Saída esperada

```python
with page.expect_download() as download_info:
    page.get_by_role("button", name="Exportar").click()

download = download_info.value
assert re.match(r"relatorio-.*\.pdf", download.suggested_filename)
```

## Critérios de sucesso

- Download capturado;
- Nome, tipo, tamanho, hash ou conteúdo validado conforme regra;
- Artefato salvo em diretório controlado de evidências.

## Regras de rejeição

Rejeitar se o teste apenas clicar no botão sem validar o artefato quando o download for o resultado esperado.

---

# 5.15 `upload_payload_binding`

## Finalidade

Transformar uploads gravados em referências portáveis, versionáveis e parametrizáveis.

## Casos taxonômicos relacionados

- `INP-001`
- `INP-002`
- `FILE-001`
- `FILE-002`
- `FILE-003`

## Quando aplicar

Aplicar quando:

- gravação contém caminho absoluto local;
- upload depende de fixture;
- componente encapsula `input[type=file]`;
- arquivo possui restrição de extensão, tipo ou tamanho.

## Entradas mínimas

- caminho gravado;
- metadados do arquivo;
- componente de upload;
- política de massa de teste.

## Saída esperada

```python
fixture_file = test_data.path("uploads/documento_valido.pdf")
page.set_input_files("input[type='file']", fixture_file)
```

## Critérios de sucesso

- Caminho absoluto removido;
- Fixture versionada ou parametrizada;
- Upload confirmado pela UI ou resposta;
- Restrições do arquivo registradas.

## Regras de rejeição

Rejeitar se:

- arquivo local não existir;
- arquivo contiver dado sensível não autorizado;
- não houver fixture equivalente.

---

# 5.16 `assert_overlay_capture`

## Finalidade

Capturar e estruturar asserts informados pelo usuário antes, durante ou depois da gravação.

## Casos taxonômicos relacionados

- `AST-001`
- `AST-002`
- `AST-003`
- `AST-008`
- `REC-002`

## Quando aplicar

Aplicar quando:

- usuário declara objetivo antes da gravação;
- usuário marca um elemento no overlay durante a gravação;
- usuário complementa validações após a gravação;
- assert precisa ser vinculado a um step, tela ou estado.

## Entradas mínimas

- anotação do usuário;
- timestamp;
- step vinculado;
- DOM/accessibility snapshot;
- intenção do assert.

## Saída esperada

Metadado estruturado de assert.

```yaml
assertion:
  source: overlay
  timing: during_recording
  step_id: STEP-008
  intent: validar mensagem de sucesso
  target:
    role: status
    text: Operação realizada com sucesso
  suggested_assert:
    type: visible_text
```

## Critérios de sucesso

- Assert aparece no script final no ponto adequado;
- A intenção do usuário é preservada;
- Assert ambíguo não é inventado.

## Regras de rejeição

Se o usuário disser apenas “verificar se deu certo” sem alvo ou condição objetiva, retornar `MANUAL_REQUIRED` e sugerir opções de assert.

---

# 5.17 `manual_checkpoint`

## Finalidade

Registrar ponto de intervenção humana quando a automação segura não é possível ou não deve prosseguir sem decisão explícita.

## Casos taxonômicos relacionados

- `CTX-002`
- `CTX-004`
- `INP-008`
- `LIM-001`
- `LIM-002`
- `LIM-004`
- `AST-008`
- `REC-001`
- `REC-004`

## Quando aplicar

Aplicar quando:

- há CAPTCHA;
- iframe cross-origin é inacessível;
- Shadow DOM é fechado;
- operação é irreversível;
- assert é ambíguo;
- fluxo foi interrompido;
- decisão humana é necessária.

## Entradas mínimas

- motivo do checkpoint;
- evidência;
- step atual;
- ação bloqueada;
- instrução esperada do usuário.

## Saída esperada

Checkpoint explícito no script, metadado ou relatório.

```yaml
checkpoint:
  state: MANUAL_REQUIRED
  taxonomy_id: LIM-004
  reason: Operação irreversível detectada
  required_user_decision: Confirmar se o fluxo pode prosseguir em ambiente sandbox
```

## Critérios de sucesso

- O curador não prossegue de forma insegura;
- O relatório explica a pendência;
- O ponto de retomada é claro.

## Regras de rejeição

Não usar checkpoint manual como substituto para falhas simples que possuem estratégia segura P0.

---

## 6. Estratégias Complementares Recomendadas

A taxonomia atual lista as estratégias principais conhecidas. Para implementação do Curador, recomenda-se também formalizar as estratégias complementares abaixo, pois aparecem implicitamente nos casos.

---

# 6.1 `precondition_validation`

## Finalidade

Validar se o estado inicial da aplicação permite executar o teste.

## Casos relacionados

- `STA-003`
- `STA-005`
- `STA-006`

## Resultado esperado

- Pré-condição explícita;
- Setup/teardown quando aplicável;
- Skip justificado ou `MANUAL_REQUIRED` quando depender de perfil/ambiente.

---

# 6.2 `dialog_handler`

## Finalidade

Tratar alertas, confirms e prompts nativos do browser.

## Casos relacionados

- `STA-004`

## Resultado esperado

Handler explícito de diálogo com política configurável.

```python
page.on("dialog", lambda dialog: dialog.accept())
```

A política `accept` ou `dismiss` deve vir de evidência, configuração ou intenção do teste.

---

# 6.3 `artifact_evidence_capture`

## Finalidade

Garantir coleta de evidências em falhas, execuções e healing.

## Casos relacionados

- `OBS-001`
- `OBS-002`
- `OBS-003`
- `OBS-004`

## Resultado esperado

- Screenshot;
- Trace;
- Console logs;
- Network/HAR, se configurado;
- DOM snapshot;
- Patch diff;
- ID taxonômico.

---

# 6.4 `patch_rejection_policy`

## Finalidade

Evitar loops de healing quando o mesmo patch é rejeitado repetidamente.

## Casos relacionados

- `OBS-005`

## Regra recomendada

Após 3 rejeições do mesmo patch, com a mesma assinatura de falha, marcar como:

```yaml
state: UNRESOLVED
reason: Patch rejeitado repetidamente pelo validador
```

---

# 6.5 `flakiness_promotion_policy`

## Finalidade

Definir quando um script pode ser promovido como estável.

## Casos relacionados

- `OBS-006`

## Regra recomendada

Promover somente após 3 execuções limpas consecutivas, sem healing adicional e sem falhas intermitentes.

---

# 6.6 `sensitive_data_guard`

## Finalidade

Evitar persistência ou exposição de dados sensíveis em scripts, logs, snapshots, prompts ou relatórios.

## Casos relacionados

- `LIM-003`

## Resultado esperado

- Mascaramento;
- Tokenização;
- Fixtures seguras;
- Bloqueio de envio de dados sensíveis à LLM;
- Relatório sem segredo em claro.

---

## 7. Ordem Recomendada de Aplicação das Estratégias

A ordem abaixo reduz risco de patch incorreto e favorece estratégias determinísticas antes de inferência.

```text
1. manual_checkpoint, quando houver risco bloqueante evidente
2. re_auth_hook, quando houver sessão expirada
3. artifact_evidence_capture, para preservar diagnóstico
4. frame_reacquire / shadow_pierce, quando houver mudança de contexto
5. overlay_dismiss, quando houver bloqueio visual
6. network_idle_wait / response_intercept / dom_stabilization, quando houver assincronismo
7. semantic_locator_conversion
8. aria_role_strategy
9. label_proximity
10. text_content_match
11. primefaces_registry_scan, quando PrimeFaces for detectado
12. upload_payload_binding / download_event_capture, para artefatos
13. assert_overlay_capture, para validações declaradas pelo usuário
14. evidence_collector, estrutura payload para LLM (layer 3a)
15. llm_healer, prompt enxuto + payload estruturado (layer 3b)
16. curador_automatico, valida execução e cataloga (layer 3c)
17. patch_rejection_policy, quando houver rejeições repetidas
18. flakiness_promotion_policy, antes da promoção final
```

Observação: essa ordem pode ser ajustada por família, mas qualquer alteração deve ser justificada por ADR ou decisão técnica rastreável.

---

## 8. Matriz Estratégia x Família

| Estratégia | Seletores | Timing | Contexto | Estado | DOM | Input | Arquivos | Asserts | Recorder | Observabilidade | Limites |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `label_proximity` | Sim | Não | Parcial | Não | Parcial | Parcial | Não | Sim | Não | Não | Não |
| `text_content_match` | Sim | Parcial | Parcial | Parcial | Parcial | Não | Não | Sim | Não | Não | Não |
| `aria_role_strategy` | Sim | Não | Parcial | Parcial | Parcial | Sim | Não | Sim | Não | Não | Não |
| `semantic_locator_conversion` | Sim | Não | Parcial | Não | Sim | Parcial | Não | Não | Não | Sim | Não |
| `primefaces_registry_scan` | Sim | Parcial | Sim | Parcial | Sim | Sim | Parcial | Não | Sim | Não | Não |
| `frame_reacquire` | Não | Parcial | Sim | Não | Sim | Sim | Não | Parcial | Não | Não | Sim |
| `shadow_pierce` | Não | Não | Sim | Não | Sim | Parcial | Não | Parcial | Não | Não | Sim |
| `network_idle_wait` | Não | Sim | Não | Parcial | Sim | Parcial | Parcial | Parcial | Não | Sim | Não |
| `response_intercept` | Não | Sim | Não | Parcial | Parcial | Parcial | Sim | Sim | Não | Sim | Parcial |
| `dom_stabilization` | Não | Sim | Parcial | Parcial | Sim | Parcial | Não | Sim | Não | Sim | Não |
| `overlay_dismiss` | Parcial | Parcial | Sim | Sim | Parcial | Parcial | Não | Não | Não | Parcial | Não |
| `re_auth_hook` | Não | Parcial | Não | Sim | Não | Não | Sim | Não | Não | Sim | Parcial |
| `llm_selector_inference` | Sim | Não | Parcial | Não | Parcial | Parcial | Não | Parcial | Não | Sim | Não |
| `download_event_capture` | Não | Parcial | Parcial | Parcial | Não | Sim | Sim | Sim | Não | Sim | Não |
| `upload_payload_binding` | Não | Não | Parcial | Parcial | Não | Sim | Sim | Não | Não | Sim | Sim |
| `assert_overlay_capture` | Não | Parcial | Parcial | Não | Parcial | Parcial | Sim | Sim | Sim | Sim | Sim |
| `evidence_collector` | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| `llm_healer` | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| `curador_automatico` | Não | Não | Não | Não | Não | Não | Não | Não | Sim | Sim | Não |
| `manual_checkpoint` | Não | Não | Sim | Sim | Parcial | Sim | Parcial | Sim | Sim | Sim | Sim |

---

## 9. Modelo de Registro de Aplicação da Estratégia

Cada aplicação de estratégia deve gerar um registro auditável.

```yaml
healing_application:
  id: HLG-0001
  taxonomy_id: SEL-001
  strategy_id: semantic_locator_conversion
  source_step_id: STEP-004
  original_code: |
    page.locator("#form:j_idt123").click()
  proposed_code: |
    page.get_by_role("button", name="Consultar").click()
  evidence:
    - type: dom_snapshot
      ref: evidence/dom/STEP-004-before.json
    - type: accessibility_snapshot
      ref: evidence/a11y/STEP-004.json
    - type: execution_error
      message: Element not found for selector #form:j_idt123
  rationale: >
    O seletor original usa ID JSF dinâmico. O snapshot de acessibilidade
    mostra botão com nome acessível Consultar. A estratégia converteu o
    seletor para locator semântico Playwright.
  confidence: 0.91
  validation:
    status: passed
    clean_runs: 3
  result_state: RESOLVED
```

---

## 10. Regras para PatchValidator

O `PatchValidator` deve validar, no mínimo:

1. O patch referencia um ID taxonômico existente.
2. A estratégia usada é permitida para o ID ou possui justificativa.
3. A evidência mínima exigida pela estratégia está presente.
4. O patch não introduz segredo em claro.
5. O patch não usa `waitForTimeout` como solução principal.
6. O patch não usa `force=True` sem justificativa explícita.
7. O patch não fabrica assert ambíguo.
8. O patch não tenta automatizar CAPTCHA, cross-origin inacessível ou operação irreversível.
9. O script executa com sucesso conforme critério do caso.
10. O mesmo patch não foi rejeitado 3 vezes para a mesma assinatura.

---

## 11. Regras para ImplementationAuditor

O `ImplementationAuditor` deve verificar:

1. Todo healing tem trilha de auditoria.
2. Todo patch tem diff e justificativa.
3. Toda decisão manual possui motivo e ponto de retomada.
4. Toda estratégia aplicada possui evidência.
5. Todo uso de LLM possui dados sanitizados.
6. Todo arquivo de upload/download é tratado como artefato controlado.
7. Todo assert tem origem: usuário, regra explícita ou evidência objetiva.
8. Toda promoção final respeita política de estabilidade.

---

## 12. Critérios Globais de Aceite deste Artefato

Este contrato será considerado implementável quando:

1. Cada estratégia possuir função ou classe própria.
2. Cada estratégia implementar `can_apply` e `apply`, ou contrato equivalente.
3. Cada resultado possuir `state`, `confidence`, `evidence`, `rationale` e `taxonomy_id`.
4. Nenhuma estratégia alterar script sem registrar evidência.
5. Estratégias determinísticas forem tentadas antes de inferência por LLM.
6. Casos de risco forem tratados por checkpoint manual ou não resolução segura.
7. PatchValidator rejeitar alterações sem evidência suficiente.
8. ImplementationAuditor conseguir reconstruir o motivo de cada alteração.

---

## 13. Backlog Técnico Derivado

### P0

- Implementar interface base `HealingStrategy`.
- Implementar `StrategyContext` e `StrategyResult`.
- Implementar registro auditável de aplicação de estratégia.
- Implementar `semantic_locator_conversion`.
- Implementar `network_idle_wait`.
- Implementar `dom_stabilization`.
- Implementar `frame_reacquire`.
- Implementar `overlay_dismiss`.
- Implementar `download_event_capture`.
- Implementar `upload_payload_binding`.
- Implementar `assert_overlay_capture`.
- Implementar `manual_checkpoint`.
- Implementar `patch_rejection_policy`.
- Implementar integração com `PatchValidator`.

### P1

- Implementar `label_proximity`.
- Implementar `text_content_match`.
- Implementar `aria_role_strategy`.
- Implementar `response_intercept`.
- Implementar `primefaces_registry_scan`.
- Implementar `dialog_handler`.
- Implementar `artifact_evidence_capture` completo.
- Implementar `flakiness_promotion_policy`.

### P2

- Implementar `shadow_pierce` avançado.
- Implementar `llm_selector_inference` com sanitização forte.
- Implementar análise avançada de virtualização de listas.
- Implementar políticas específicas por framework detectado.

---

## 14. Observação para SpecKit

Este documento deve ser usado preferencialmente na fase de planejamento técnico (`/speckit.plan`), pois define contratos de implementação, componentes, validação e políticas de execução.

A especificação funcional (`/speckit.specify`) deve referenciar este artefato apenas como requisito de comportamento esperado, sem prescrever detalhes internos de implementação.

---

## 15. Resumo Executivo

O arquivo `healing-strategies.md` transforma a taxonomia em contratos executáveis para o Curador do TestForge.

Ele garante que cada estratégia de healing:

- tenha responsabilidade clara;
- seja aplicável apenas quando houver evidência;
- produza saída auditável;
- respeite limites técnicos e de segurança;
- possa ser validada automaticamente;
- mantenha rastreabilidade com os IDs taxonômicos.

Com isso, o TestForge evita correções opacas, locators inventados, asserts ambíguos e loops de healing, preservando o princípio central do projeto: **automação robusta, explicável e segura**.
