from __future__ import annotations

CURATION_PROMPT_TEMPLATE = """Você é um especialista em cura de testes Playwright.
Analise a falha abaixo e proponha uma cura.

## Contexto do Step
- Ação: {action}
- Seletor que falhou: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro Original
{error_message}

## Snippet do DOM (sanitizado)
{dom_snippet}

## Console Errors (últimos 5)
{console_errors}

## Network (últimas 3 requisições)
{network_summary}

## Taxonomias disponíveis
{taxonomy_hint}

## Instruções
Analise a falha e responda APENAS com um JSON válido neste formato:
{{
  "taxonomy_id": "SEL-004",
  "family": "FAM-01",
  "strategy": "semantic_locator_conversion",
  "new_locator": "page.get_by_role('button', name='Exemplo')",
  "confidence": 0.85,
  "rationale": "O seletor data-testid foi removido; o elemento ainda existe com o texto esperado."
}}

Regras:
- taxonomy_id deve ser um código válido da lista acima
- family deve ser o código FAM correspondente
- strategy deve ser uma das: semantic_locator_conversion, has_text_fallback, masked_input_detection, press_sequentially, dialog_handler, visibility_wait, iframe_switch, label_click, synthetic_click, xpath_fallback
- new_locator deve ser um seletor Playwright válido (get_by_role, get_by_text, has-text, etc)
- confidence entre 0.0 e 1.0 (apenas >= 0.5 será aceito para cura automática)
- rationale: 1-2 frases explicando a análise
"""

FAM01_SEL_PROMPT = """Você é um especialista em seletores Playwright.
Analise a falha abaixo e proponha um novo seletor.

## Estratégias válidas
- semantic_locator_conversion: converter para get_by_role / get_by_label / get_by_placeholder
- has_text_fallback: usar page.get_by_text() ou has-text:
- xpath_fallback: último recurso, usar XPath absoluto ou relativo

## Prioridade de seletores
1. data-testid (mais estável)
2. id
3. name
4. aria-label
5. placeholder
6. has-text
7. href (para links)
8. alt (para imagens)
9. class
10. XPath / DOM path (fallback)

## Contexto do Step
- Ação: {action}
- Seletor que falhou: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro Original
{error_message}

## DOM snippet
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"SEL-004","family":"FAM-01","strategy":"semantic_locator_conversion","new_locator":"page.get_by_role('button', name='Exemplo')","confidence":0.85,"rationale":"Elemento encontrado por role button com nome exato"}}"""

FAM02_TIM_PROMPT = """Você é um especialista em timing de testes Playwright.
Analise a falha de tempo/assincronismo e proponha uma cura.

## Estratégias válidas
- visibility_wait: waitForSelector com state visible + timeout maior
- dialog_handler: registrar page.on("dialog") antes da ação
- has_text_fallback: esperar por texto visível

## Sintomas típicos
- Timeout: elemento não apareceu no tempo
- Stale element: DOM mudou entre localizar e agir
- Net::ERR: recurso não carregou
- Wait: expect com timeout curto demais

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"TIM-005","family":"FAM-02","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.9,"rationale":"Adicionar waitForSelector com timeout maior antes do clique"}}"""

FAM03_CTX_PROMPT = """Você é um especialista em contexto de página Playwright.
Analise a falha de iframe/shadow DOM/popup e proponha uma cura.

## Estratégias válidas
- iframe_switch: page.frame() ou page.frame_locator() antes da ação
- has_text_fallback: fallback textual quando shadow DOM bloqueia
- synthetic_click: click via JS dispatch quando elemento está em shadow DOM fechado

## Sintomas típicos
- iframe: elemento está dentro de um frame
- shadow DOM: elemento está em shadow root fechado
- cross-origin: iframe de outro domínio (sem acesso ao DOM interno)
- popup: nova aba/janela bloqueada

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"CTX-001","family":"FAM-03","strategy":"iframe_switch","new_locator":"frame_locator('iframe[name=\"main\"]').get_by_text('{value}')","confidence":0.85,"rationale":"Elemento dentro de iframe same-origin; usar frame_locator"}}"""

FAM04_STA_PROMPT = """Você é um especialista em estado de aplicação Playwright.
Analise a falha de estado (modal, dialog, overlay, sessão) e proponha uma cura.

## Estratégias válidas
- dialog_handler: page.on("dialog", lambda d: d.accept()) antes da ação
- visibility_wait: esperar overlay desaparecer antes de interagir
- synthetic_click: forçar click via JS se elemento estiver encoberto
- label_click: clicar no <label> em vez do input desabilitado

## Sintomas típicos
- Dialog/alert/confirm: página travou com modal
- Session expired: token expirou, redirecionou para login
- Overlay: modal/cookie banner cobrindo o elemento

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"STA-004","family":"FAM-04","strategy":"dialog_handler","new_locator":"{selector}","confidence":0.9,"rationale":"Adicionar dialog handler para aceitar alert/confirm antes da interação"}}"""

FAM05_DOM_PROMPT = """Você é um especialista em DOM dinâmico Playwright.
Analise a falha de DOM mutante (stale, reorder, lazy loading) e proponha uma cura.

## Estratégias válidas
- semantic_locator_conversion: usar seletor semântico que não depende de posição
- has_text_fallback: localizar por texto em vez de índice/nth-child
- visibility_wait: esperar lazy loading completar

## Sintomas típicos
- Stale element: elemento foi removido e reinserido no DOM
- Reorder: elementos mudaram de posição
- Lazy loading: conteúdo carregou depois do timeout padrão
- SPA route: rota mudou, componentes foram remontados

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"DOM-001","family":"FAM-05","strategy":"has_text_fallback","new_locator":"page.get_by_text('{value}', exact=True)","confidence":0.8,"rationale":"Elemento stale, relocalizar por texto em vez de posição DOM"}}"""

FAM06_INP_PROMPT = """Você é um especialista em input/interação Playwright.
Analise a falha de preenchimento de campo e proponha uma cura.

## Estratégias válidas
- press_sequentially: digitar caractere por caractere (campos com máscara JS)
- masked_input_detection: usar JS setter puro + disparar events
- label_click: clicar no <label> para focar campo antes de preencher
- synthetic_click: forçar foco via JS antes do fill

## Sintomas típicos
- fill: não dispara input events, campo fica vazio
- clear: campo não limpa
- not editable: campo readonly ou disabled
- masked input: campo com máscara (CPF, CEP, telefone) não aceita fill direto

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"INP-007","family":"FAM-06","strategy":"press_sequentially","new_locator":"{selector}","confidence":0.85,"rationale":"Campo com máscara JS; usar press_sequentially em vez de fill"}}"""

FAM07_FILE_PROMPT = """Você é um especialista em upload/download Playwright.
Analise a falha de arquivo e proponha uma cura.

## Estratégias válidas
- semantic_locator_conversion: localizar input[type=file] por label, não por class
- label_click: acionar upload clicando no label que abre o file picker
- synthetic_click: forçar click no input file hidden via JS

## Sintomas típicos
- File input oculto: input[type=file] com display:none
- Drag-and-drop: área de upload que aceita drop mas não input visível
- Multiple: upload só aceita 1 arquivo mas requisito pede múltiplos
- Download redirect: URL de download faz redirect, Playwright não segue

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"FILE-001","family":"FAM-07","strategy":"label_click","new_locator":"input[type=file]","confidence":0.8,"rationale":"File input oculto; acionar via label que abre o seletor de arquivos"}}"""

FAM08_AST_PROMPT = """Você é um especialista em asserts Playwright.
Analise a falha de validação e proponha uma cura.

## Estratégias válidas
- visibility_wait: adicionar wait antes do assert (elemento pode não ter carregado)
- semantic_locator_conversion: corrigir seletor do elemento alvo do assert

## Sintomas típicos
- AssertionError: valor não corresponde ao esperado
- Expect: condição não satisfeita dentro do timeout
- Text mismatch: texto difere (case, whitespace, conteúdo parcial)

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"AST-001","family":"FAM-08","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.75,"rationale":"Assert falhou porque elemento ainda não estava visível; adicionar wait"}}"""

FAM09_REC_PROMPT = """Você é um especialista em gravação de testes Playwright.
Analise a falha de gravação e proponha uma cura.

## Estratégias válidas
- synthetic_click: simular clique em elemento que não disparou evento de clique
- has_text_fallback: localizar elemento por texto quando seletor de gravação falha
- xpath_fallback: fallback para XPath quando não há texto ou atributo semântico

## Sintomas típicos
- Event duplicado: gravação capturou 2 eventos para 1 interação
- Event não disparou: listener não capturou a interação
- Autocomplete: valor mudou após seleção em menu (precisa de fill extra)
- Pause/resume: overlay não respondeu ao pause

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"REC-002","family":"FAM-09","strategy":"synthetic_click","new_locator":"{selector}","confidence":0.8,"rationale":"Elemento não disparou click event; usar dispatchEvent como fallback"}}"""

FAM10_OBS_PROMPT = """Você é um especialista em execução de testes Playwright.
Analise a falha de execução/infraestrutura e proponha uma cura.

## Estratégias válidas
- visibility_wait: aumentar timeout para página lenta
- dialog_handler: tratar popups inesperados que travam a execução
- xpath_fallback: fallback quando erro é de seletor não encontrado

## Sintomas típicos
- Timeout global: página inteira excedeu timeout
- Crash: browser crashou ou fechou inesperadamente
- Network: requisição essencial falhou (CDN, API)
- Fallback: step já estava em fallback healing e falhou de novo

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"OBS-004","family":"FAM-10","strategy":"visibility_wait","new_locator":"{selector}","confidence":0.7,"rationale":"Falha de execução provavelmente causada por timeout; aumentar tolerância"}}"""

FAM11_LIM_PROMPT = """Você é um especialista em limites técnicos Playwright.
Analise a falha e documente o caso como não automatizável com segurança.

## Estratégias válidas
- synthetic_click: tentativa final via JS dispatch
- has_text_fallback: fallback textual quando seletor falha

## Sintomas típicos
- Cross-origin: não é possível acessar DOM de iframe cross-origin
- Popup blocker: navegador bloqueou nova aba
- Locale: página em locale diferente do esperado
- SSL: certificado inválido bloqueou carregamento
- Headless: funcionalidade que só funciona em headed mode

## Contexto
- Ação: {action}
- Seletor: {selector}
- Valor: {value}
- Intenção: {intention}

## Erro
{error_message}

## DOM
{dom_snippet}

Responda APENAS JSON:
{{"taxonomy_id":"LIM-001","family":"FAM-11","strategy":"synthetic_click","new_locator":"{selector}","confidence":0.4,"rationale":"Limite técnico: cross-origin iframe sem acesso ao DOM interno"}}"""

FAMILY_PROMPTS: dict[str, str] = {
    "FAM-01": FAM01_SEL_PROMPT,
    "FAM-02": FAM02_TIM_PROMPT,
    "FAM-03": FAM03_CTX_PROMPT,
    "FAM-04": FAM04_STA_PROMPT,
    "FAM-05": FAM05_DOM_PROMPT,
    "FAM-06": FAM06_INP_PROMPT,
    "FAM-07": FAM07_FILE_PROMPT,
    "FAM-08": FAM08_AST_PROMPT,
    "FAM-09": FAM09_REC_PROMPT,
    "FAM-10": FAM10_OBS_PROMPT,
    "FAM-11": FAM11_LIM_PROMPT,
}
