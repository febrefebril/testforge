Gmail	André Perotti <andre.pnetto@gmail.com>
bugs para concertar
Andre Perotti Netto <andre.netto@caixa.gov.br>	15 de junho de 2026 às 22:16
Para: André Perotti <andre.pnetto@gmail.com>

E-mail classificado como #PUBLICO

1. Bug crítico: geração errada de seletores para <select>

No fluxo do SIMAX, a gravação mostra que os campos UF, Edifício e Data são elementos <select>, com nomes como lstUf, lstEdificio e lstData, mas o script gerado procura seletores do tipo label:has-text("UF") + input, ou seja, ele tenta localizar um <input> que não existe. Isso explica as falhas repetidas em label:has-text("UF") + input, label:has-text("Edifício") + input e label:has-text("Data") + input. [caixa-my.s...epoint.com]

Bug: o compilador está inferindo o tipo de elemento errado.

Correção esperada: quando o alvo gravado for tag: "select", o script não deve gerar click() nem fill(), mas sim select_option() usando preferencialmente name, id ou label confiável.

Exemplo esperado:

Python

page.select_option('select[name="lstUf"]', 'MT')

page.select_option('select[name="lstEdificio"]', '<valor_do_edificio>')

page.select_option('select[name="lstData"]', '2026-06-19')

Mostrar mais linhas
2. Bug crítico: ações erradas para elementos <select>

Mesmo quando o gravador identifica corretamente um <select>, a execução tenta tratar a interação como click ou fill, o que não representa a intenção real do usuário. No Playwright, select deve ser manipulado com select_option, principalmente quando o valor selecionado aparece no evento gravado. [caixa-my.s...epoint.com]

Bug: o compilador não possui uma regra de transformação por tipo de elemento.

Regra correta:

Elemento gravado
	

Ação gravada
	

Ação Playwright esperada

input[type=text]
	

fill
	

locator.fill(value)

button
	

click
	

locator.click()

select
	

click/fill/change
	

locator.select_option(value)

radio
	

click
	

locator.check()

checkbox
	

click
	

locator.check() ou uncheck()

a[href]
	

click
	

locator.click() + espera de navegação quando aplicável
3. Bug crítico: snapshots de DOM vazios

O arquivo consolidado mostra diversos arquivos dom_snapshots/*.html com 0 bytes, inclusive nos fluxos calcular_poder_compra, login_gas_povo, consulta-cpf e simax_agenda_massagem. Sem snapshots reais de DOM, o TestForge perde uma das fontes mais importantes para gerar seletores robustos, diagnosticar falhas e aplicar self-healing com evidência. [caixa-my.s...epoint.com]

Bug: o DOMSnapshotCollector está criando os arquivos, mas não está persistindo o conteúdo do DOM.

Impacto: o healer e o compilador ficam dependentes apenas do evento bruto, texto e atributos parciais.

Correção esperada: garantir que cada evento relevante salve page.content() ou snapshot sanitizado não vazio, com validação explícita:

Python

html = await page.content()

if not html.strip():

registrar_alerta("DOM snapshot vazio", event_id)

else:

salvar_snapshot(event_id, html)

Mostrar mais linhas
4. Bug crítico: contagem de passos inconsistente

Há inconsistência clara entre o que o gravador informa, o que existe nos arquivos e o que o runner executa. Em calcular_poder_compra, o terminal informa ✓ 1 passos gravados, mas o compile gera SemanticTestCase: 15 steps e o runner carrega 15 passos da gravacao. No arquivo consolidado, steps.jsonl contém basicamente assert final, enquanto raw_events.jsonl contém diversos eventos de navegação/click/fill. [caixa-my.s...epoint.com]

Bug: existem pelo menos três contadores diferentes e desalinhados:

    contador exibido ao gravar;
    quantidade de eventos brutos;
    quantidade de steps semânticos compilados/executados.

Correção esperada: separar explicitamente no log:

Plain Text

Eventos brutos capturados: 14

Steps semânticos gerados: 15

Asserts manuais: 1

Steps executáveis: 15

Steps ignorados/filtrados: N

Mostrar mais linhas

Do jeito atual, o usuário acredita que gravou só 1 passo, mas o TestForge compila e executa 15.
5. Bug crítico: event_id reinicia e mistura sessões dentro da mesma gravação

No fluxo login_gas_povo, o raw_events.jsonl contém múltiplos eventos com event_id: evt_0001, em momentos diferentes e para URLs diferentes, incluindo navegação para Teams, depois para Login CAIXA e depois para a tela de autenticação. O mesmo padrão aparece no SIMAX, onde novas navegações reiniciam a sequência de eventos. [caixa-my.s...epoint.com]

Bug: o identificador do evento não é global dentro da sessão de gravação.

Impacto: screenshots, DOM snapshots e eventos podem se sobrescrever ou ficar ambíguos.

Correção esperada: event_id deve ser monotônico por recording_id, nunca reiniciar após navegação. Se houver subfluxos, usar session_id, page_id ou navigation_id, mas preservar evt_0001, evt_0002, evt_0003 de forma única.
6. Bug crítico: múltiplas sessões parecem ser anexadas no mesmo raw_events.jsonl

No login_gas_povo, aparecem eventos de uma tentativa com Teams, outra com URL incompleta do Login CAIXA e outra com fluxo real de autenticação, mas todos acabam no mesmo conjunto de gravação. Isso gera um script enorme, com passos de fluxos diferentes misturados. [caixa-my.s...epoint.com]

Bug: o gravador não isola corretamente uma sessão nova quando o usuário reinicia o comando com o mesmo --name.

Correção esperada: ao iniciar record --name X, o TestForge deveria oferecer uma dessas estratégias:

Plain Text

recordings/X já existe.

Opções:

1. sobrescrever

2. criar X_2

3. anexar intencionalmente

Mostrar mais linhas

Como o Copilot não deve depender de confirmação nesse fluxo de CLI, eu recomendaria como padrão seguro: criar nova pasta com sufixo incremental e nunca anexar silenciosamente.
7. Bug crítico: captura de digitação caractere por caractere

No fluxo login_gas_povo, o runner executa muitos fill sequenciais para o mesmo campo CPF, com valores incrementais e depois regressivos, como se cada tecla virasse um step executável. Isso infla o script, polui a execução e dificulta healing/oracle. [caixa-my.s...epoint.com]

Bug: o gravador está persistindo eventos intermediários de input como passos finais.

Correção esperada: implementar compactação/debounce de fill por campo. Para o mesmo seletor, dentro de uma janela curta de digitação, manter apenas o valor final estável.

Exemplo de regra:

Plain Text

input CPF:

fill "4"

fill "40"

fill "407"

...

fill valor_final

 

=> gerar apenas:

fill CPF com valor_final

Mostrar mais linhas

Também recomendo mascarar ou tokenizar valores sensíveis no artefato sem impedir o teste. Como você já decidiu anteriormente, no MVP podemos começar apenas com alerta de presença de dado sensível, não mascaramento automático.
8. Bug crítico: comando com URL contendo & quebra no PowerShell

O comando com URL longa do Login CAIXA foi quebrado pelo PowerShell porque & é interpretado como operador, criando vários BackgroundJob. Isso não é exatamente bug interno do runner, mas é um bug de experiência/robustez da CLI, porque o TestForge aceita URL como argumento e deveria orientar ou proteger o usuário contra esse caso comum. [caixa-my.s...epoint.com]

Bug de DX/CLI: ausência de validação e mensagem amigável para URL não escapada.

Correção esperada: documentação e validação no CLI:

PowerShell

python -m testforge.cli.app record --name login_gas_povo https://logindes.caixa.gov.br/auth/realms/...

Mostrar mais linhas

Além disso, o CLI poderia detectar quando recebeu uma URL truncada, por exemplo terminando em ?client_id=..., e alertar:

Plain Text

A URL parece conter parâmetros. No PowerShell, envolva a URL entre aspas.

Mostrar mais linhas
9. Bug crítico: navegador Playwright bloqueado no ambiente corporativo sem fallback

Você relatou que, no trabalho, o navegador Playwright é bloqueado. Isso impede o uso do TestForge no ambiente real da CAIXA. Como o objetivo do TestForge é gravar e executar fluxos reais em sistemas internos, a ausência de fallback para o navegador padrão do notebook deve ser considerada bug de compatibilidade corporativa. [caixa-my.s...epoint.com]

Bug: TestForge depende rigidamente do browser gerenciado pelo Playwright.

Correção esperada: criar estratégia de fallback em camadas:

    tentar Playwright Chromium padrão;
    tentar channel="msedge" ou Chrome/Edge instalado;
    tentar conexão CDP com navegador já aberto;
    em modo gravação, permitir “recorder externo” via extensão/injeção JS quando Playwright não puder iniciar.

Exemplo conceitual:

Python

browser = await chromium.launch(channel="msedge", headless=False)

Mostrar mais linhas

Ou, para navegador já aberto com depuração remota:

Python

browser = await chromium.connect_over_cdp(http://127.0.0.1:9222)

Mostrar mais linhas
10. Bug crítico: tela piscando/recarregando no SIMAX durante gravação

No SIMAX, você relatou que toda vez que clica em algo a tela “pisca”, inviabilizando a gravação. O arquivo mostra várias requisições repetidas para novo_agendamento.asp, incluindo POSTs e recarregamentos sucessivos, o que combina com perda de estado visual e re-render/navegação a cada interação. [caixa-my.s...epoint.com]

Bug: o gravador provavelmente está interferindo no fluxo, ou o compilador/runner está tratando interações de formulário como navegações completas desnecessárias.

Correção esperada: o recorder precisa distinguir:

    clique simples;
    submit real;
    POST/navegação;
    alteração de <select> que dispara reload;
    interação causada pelo overlay.

Para o SIMAX, o TestForge também precisa de uma estratégia especial para páginas ASP clássicas com formulário/postback.
11. Bug alto: navegações goto() excessivas no script gerado

A análise do arquivo aponta que há vários page.goto(BASE_URL) no meio dos scripts. Isso tende a apagar estado, recomeçar fluxo, quebrar formulários e gerar divergência entre a gravação e a execução. [caixa-my.s...epoint.com]

Bug: o compilador transforma eventos de navegação em goto() repetidos sem considerar se a navegação foi consequência de uma ação anterior.

Correção esperada: o script deve iniciar com goto(BASE_URL) uma vez e, depois, usar expect_navigation, wait_for_url ou wait_for_load_state apenas quando uma ação realmente causar navegação.

Exemplo:

Python

await page.goto(BASE_URL)

 

async with page.expect_navigation():

await page.locator("text=Novo agendamento").click()

Mostrar mais linhas
12. Bug alto: seletores por texto genérico demais

O healer está sugerindo candidatos como text=Selecione ou [aria-label='Página inicial'], mesmo quando a ação original era selecionar UF, Edifício, Data ou botão Calcular. Esses candidatos são semanticamente fracos e podem gerar falso healing. [caixa-my.s...epoint.com]

Bug: o ranking de candidatos está priorizando texto visível genérico sem validar tipo, intenção e contexto.

Correção esperada: o ranking deve penalizar fortemente:

    texto genérico: Selecione, Página inicial, Calcular sem escopo;
    candidatos com tag incompatível;
    candidatos fora da região/fieldset original;
    candidatos sem relação com label/name/id do evento original.

13. Bug alto: métricas de healing incorretas ou enganosas

No log, mesmo com múltiplos steps falhando, as métricas mostram Total healings: 1, True heals: 1, False heals: 0, Precision: 100%, e depois o resumo diz 4 falhas, 4 curados ou 5 falhas, 5 curados. Isso é inconsistente e perigoso para avaliar qualidade do self-healing. [caixa-my.s...epoint.com]

Bug: as métricas globais e o resumo por execução estão usando bases de contagem diferentes.

Correção esperada: separar métricas por:

Plain Text

falhas_detectadas

healings_tentados

healings_aplicados

healings_validados

healings_rejeitados

fallbacks_sem_execução

oracles_passed

oracles_failed

Mostrar mais linhas

Hoje, “curado” parece estar sendo usado mesmo quando o candidato sugerido não necessariamente substituiu corretamente o step original.
14. Bug alto: assertions finais frágeis e acopladas ao DOM completo

As assertions finais usam seletores CSS longos e frágeis, como cadeias completas saindo de app-root > app-calculadora > div..., ou seletores como #tblLista tbody > tr > td. Isso quebra facilmente com qualquer alteração visual, layout, classe gerada ou componente intermediário. [caixa-my.s...epoint.com]

Bug: o gerador de assertions está escolhendo seletor estrutural frágil em vez de seletor semântico.

Correção esperada: assert por texto, role, região ou dado de negócio.

Exemplos melhores:

Python

await expect(page.get_by_text("Valor mínimo de entrada")).to_be_visible()

await expect(page.get_by_text("Reservar")).to_be_visible()

Mostrar mais linhas
15. Bug alto: script gerado contém steps que não representam intenção do usuário

Nos fluxos do simulador habitacional, ações em calendário geram seletores como :has-text("1970"), :has-text("JUN"), :has-text("3"), e alguns elementos possuem bounding_box com x=0, y=0, width=0, height=0. Isso indica que o gravador capturou elementos não acionáveis ou fora da tela. [caixa-my.s...epoint.com]

Bug: o recorder aceita como alvo elementos sem actionability real.

Correção esperada: antes de persistir o alvo principal, validar:

Plain Text

visível

habilitado

bounding box com área > 0

não coberto por overlay

estável por alguns ms

Mostrar mais linhas

Se falhar, gravar o ancestral acionável correto.
16. Bug médio: dependência httpx ausente no requirements

Você precisou instalar httpx e colocar no requirements. Isso é bug de empacotamento/dependência: se o código importa httpx, ele deve estar declarado nas dependências do projeto. [caixa-my.s...epoint.com]

Correção esperada: adicionar no requirements.txt, pyproject.toml ou equivalente:

Plain Text

httpx>=0.27

Mostrar mais linhas

E incluir teste de instalação limpa:

PowerShell

python -m venv .venv-clean

.\.venv-clean\Scripts\pip install -r requirements.txt

python -m testforge.cli.app --help

Mostrar mais linhas
17. Bug médio: logs truncados e pouco diagnósticos

Os erros aparecem truncados em vários pontos, por exemplo candidates: [:h..., o que dificulta entender por que o seletor falhou e quais candidatos foram considerados. Isso prejudica muito o debug do TestForge. [caixa-my.s...epoint.com]

Bug: logger CLI corta informação relevante sem salvar relatório completo.

Correção esperada: terminal mostra resumo, mas grava relatório completo em arquivo:

Plain Text

runs/<recording_id>/<timestamp>/execution_report.json

runs/<recording_id>/<timestamp>/healing_report.md

Mostrar mais linhas
18. Bug médio: ausência de classificação explícita do que foi ignorado

No SIMAX, há steps numerados pulando, por exemplo aparecem Step 14, depois Step 17, depois Step 19, indicando que alguns steps foram ignorados, filtrados ou não renderizados no log. O usuário não consegue saber se o TestForge pulou de propósito ou se houve erro de contagem. [caixa-my.s...epoint.com]

Bug: steps omitidos não são explicados.

Correção esperada: sempre registrar:

Plain Text

Step 15: skipped — motivo

Step 16: skipped — evento duplicado compactado

Mostrar mais linhas
19. Bug médio: compile aceita gravação com dados insuficientes

Mesmo com steps.jsonl contendo apenas assert final em alguns fluxos, o compile gera scripts com muitos steps a partir de raw_events.jsonl. Isso pode ser correto como estratégia, mas hoje parece opaco e causa confusão. [caixa-my.s...epoint.com]

Bug: não existe contrato claro entre raw_events.jsonl, steps.jsonl e semantic_tests.

Correção esperada: documentar e validar:

    raw_events.jsonl: tudo que foi capturado;
    steps.jsonl: passos manuais/curados/asserts;
    semantic_steps.jsonl: saída compilada;
    script .py: renderização executável.

O compile deveria gerar também o semantic_steps.jsonl para auditoria.
20. Bug médio: runner continua após falhas críticas de estado

No SIMAX, se a seleção de UF falha, os passos seguintes de Edifício e Data ficam semanticamente comprometidos. Ainda assim, o runner segue e acumula falhas em cascata. [caixa-my.s...epoint.com]

Bug: falta política de dependência entre steps.

Correção esperada: classificar steps como:

Plain Text

blocking: true

depends_on: step_0003

Mostrar mais linhas

Se UF falhar, Edifício/Data não devem ser tratados como falhas independentes do produto; devem ser marcados como blocked_by_previous_failure.
Priorização recomendada
P0 — Corrigir antes de continuar evoluindo o self-healing

    Corrigir <select> para select_option.
    Corrigir snapshots de DOM vazios.
    Corrigir contagem de steps.
    Impedir mistura de sessões no mesmo recording.
    Implementar fallback para browser padrão/Edge corporativo.
    Corrigir tela piscando/reload loop no SIMAX.
    Corrigir métricas de healing inconsistentes.

P1 — Corrigir para tornar os testes confiáveis

    Compactar digitação caractere por caractere.
    Remover goto() excessivo no meio do fluxo.
    Melhorar ranking de candidatos do healer.
    Evitar seletores vazios ou frágeis.
    Criar contrato claro entre raw_events, steps e semantic_steps.

P2 — Melhorias de DX e manutenção

    Adicionar httpx nas dependências.
    Melhorar mensagens da CLI para URLs com & no PowerShell.
    Salvar relatórios completos de execução/healing.
    Explicar steps pulados/compactados no log.

Backlog sugerido de bugs

ID
	

Bug
	

Severidade
	

Critério de aceite

BUG-001
	

<select> vira seletor de <input>
	

P0
	

SIMAX gera select_option() para UF, Edifício e Data

BUG-002
	

DOM snapshots com 0 bytes
	

P0
	

Todo evento relevante salva HTML não vazio ou alerta explícito

BUG-003
	

Contagem divergente entre record/compile/run
	

P0
	

CLI mostra eventos brutos, steps semânticos, asserts e steps executáveis separadamente

BUG-004
	

event_id reinicia após navegação
	

P0
	

Nenhum event_id se repete dentro de um recording

BUG-005
	

Sessões diferentes são anexadas no mesmo recording
	

P0
	

Novo record --name não anexa silenciosamente

BUG-006
	

Browser Playwright bloqueado sem fallback
	

P0
	

TestForge tenta Edge/Chrome instalado ou CDP antes de falhar

BUG-007
	

Tela pisca no SIMAX durante gravação
	

P0
	

Overlay/recorder não provoca reload visual nem interfere no click

BUG-008
	

Digitação vira dezenas de fills
	

P1
	

Campo digitado gera um único fill final por debounce

BUG-009
	

goto() excessivo no script
	

P1
	

Script só usa goto() inicial ou navegação explicitamente causada

BUG-010
	

Healer sugere candidatos genéricos
	

P1
	

Ranking penaliza texto genérico e tag incompatível

BUG-011
	

Métricas de healing inconsistentes
	

P1
	

healings_tentados, aplicados, validados e rejeitados batem com o resumo

BUG-012
	

Assertions frágeis por CSS estrutural
	

P1
	

Assertions preferem texto/role/região/atributos estáveis

BUG-013
	

Elementos com bounding box zero são aceitos
	

P1
	

Recorder rejeita alvo sem actionability

BUG-014
	

httpx ausente nas dependências
	

P2
	

Instalação limpa executa CLI sem ModuleNotFoundError

BUG-015
	

URL com & quebra no PowerShell
	

P2
	

CLI/documentação alerta para aspas e detecta URL truncada

BUG-016
	

Logs truncados demais
	

P2
	

Relatório completo é salvo em arquivo

BUG-017
	

Steps pulados não são explicados
	

P2
	

Todo step omitido aparece como skipped com motivo

BUG-018
	

Compile sem artefato semântico auditável
	

P2
	

semantic_steps.jsonl é gerado junto com o script
Minha leitura final

O maior bug não é simplesmente “o seletor falhou”. O maior bug é que o pipeline record → compile → run → heal → metrics ainda não tem contrato estável. O gravador captura uma coisa, o compilador interpreta outra, o runner executa uma terceira, e as métricas contam uma quarta. Para o TestForge ficar confiável, eu atacaria primeiro os bugs P0 acima antes de investir mais no healer LLM.

Fontes
Forneça seus comentários sobre o BizChat
You said:

Quais estratégias usar para melhorar os seletores no TestForge?
Copilot said:

Copilot

Processamento concluído em 2 etapas

Andre, para melhorar os seletores no TestForge eu não começaria pelo LLM. Eu começaria criando uma camada determinística forte de geração, ranking e validação de locators, porque os problemas que apareceram no SIMAX e no simulador habitacional são majoritariamente de captura/compilação: o gravador reconhece elementos como <select>, mas o script gerado procura <input>; há snapshots de DOM vazios; aparecem candidatos genéricos como text=Selecione; e a contagem/derivação de passos fica desalinhada entre gravação, compilação e execução. [caixa-my.s...epoint.com]

A estratégia que eu recomendo é esta:
1. Criar um “contrato semântico” do elemento gravado

Hoje o TestForge parece capturar eventos, mas ainda não transforma cada evento em uma intenção estável. O primeiro passo é enriquecer o modelo intermediário do elemento.

Cada evento deveria gerar algo como:

JSON

{

"action": "select_option",

"intent": "selecionar UF",

"element":", "element": {

"name": "lstUf",

"label": "UF",

"role": null,

"accessible_name": "UF",

"type": null,

"value": "MT",

"text": "Selecione AL AM CE DF...",

"options": [

{"text": "MT", "value": "MT"},

{"text": "DF", "value": "DF"}

],

"bounding_box": {

"x": 320,

"y": 316,

"width": 87,

"height": 31

}

},

"context": {

"url": https://simax.caixa/simax/novo_agendamento.asp,

"page_title": "SIMAX - Massagem Expressa",

"form_id": null,

"nearby_labels": ["UF", "Edifício", "Data"]

}

}

"tag": "select",

 

Mostrar mais linhas

Isso evita o bug que vimos no SIMAX: o evento real era um <select name="lstUf">, mas o script procurou label:has-text("UF") + input, que não existe. [caixa-my.s...epoint.com]

A regra principal deve ser: o tipo de elemento manda na ação e nos candidatos de locator.
2. Definir uma hierarquia de seletores por qualidade

O TestForge precisa gerar vários candidatos, mas eles devem seguir uma ordem de confiabilidade.
Camada A — seletores semânticos preferenciais

Usar primeiro seletores que representam intenção de usuário:

Python

page.get_by_role("button", name="Próximo")

page.get_by_label("CPF")

page.get_by_placeholder("R$0,00")

page.get_by_text("Valor mínimo de entrada")

Mostrar mais linhas

Essa camada é melhor para aplicações acessíveis, modernas ou com boa marcação.
Camada B — atributos estáveis

Para sistemas legados, como o SIMAX, muitas vezes role e accessible name não serão suficientes. Então entram id, name, for, aria-label, data-*.

Exemplos:

Python

page.locator("#lstUf")

page.locator('select[name="lstUf"]')

page.locator("#lstEdificio")

page.locator('select[name="lstData"]')

Mostrar mais linhas

No caso do SIMAX, essa camada provavelmente deve ter prioridade maior do que get_by_text, porque os campos têm id/name claros e estáveis. [caixa-my.s...epoint.com]
Camada C — seletor por label com escopo

Em vez de gerar:

Python

page.locator('label:has-text("UF") + input')

Mostrar mais linhas

Gerar algo mais defensivo:

Python

container = page.locator("form, main, body")

container.locator('select[name="lstUf"]')

Mostrar mais linhas

Ou, quando não houver name:

Python

page.locator("label", has_text="UF").locator("xpath=following::select[1]")

Mostrar mais linhas

Mas isso deve ser fallback, não primeira escolha.
Camada D — texto visível escopado

Texto puro deve ser usado com cuidado. text=Selecione, por exemplo, é ruim porque aparece em vários selects. Esse foi exatamente um dos sintomas no healing: o curador sugeria textos genéricos como Selecione, que não identificam corretamente o campo de UF, Edifício ou Data. [caixa-my.s...epoint.com]

Melhor:

Python

page.locator("select[name='lstUf']").select_option("MT")

Mostrar mais linhas

Pior:

Python

page.get_by_text("Selecione")

Mostrar mais linhas
Camada E — CSS estrutural como último recurso

Evitar seletores longos do tipo:

Python

#app-root > app-calculadora > div > div > app-resultados-calculadora > ...

Mostrar mais linhas

Eles quebram com qualquer mudança visual.

Usar só como fallback de baixa confiança.
Camada F — coordenadas nunca como seletor principal

Bounding box serve para validar actionability e contexto, mas não deve virar seletor. Se o elemento tem x=0, y=0, width=0, height=0, ele deve ser considerado suspeito e provavelmente não acionável.
3. Corrigir a geração por tipo de elemento

Essa é uma das melhorias mais importantes.

O compilador deve aplicar regras assim:

Python

def infer_playwright_action(event):

tag = event.target.tag

input_type = event.target.attributes.get("type")

action = event.type

 

if tag == "select":

return "select_option"

 

if tag == "input" and input_type in ["checkbox", "radio"]:

return "check"

 

if tag in ["input", "textarea"]:

return "fill"

 

if tag in ["button", "a"] or action == "click":

return "click"

 

return action

Mostrar mais linhas

Para o SIMAX, isso resolveria grande parte das falhas:

Python

page.select_option('select[name="lstUf"]', "MT")

page.select_option('select[name="lstEdificio"]', "<valor>")

page.select_option('select[name="lstData"]', "2026-06-19")

Mostrar mais linhas

Em vez de tentar:

Python

page.click('label:has-text("UF") + input')

Mostrar mais linhas
4. Gerar múltiplos candidatos por elemento

Para cada elemento, o TestForge deve gerar uma lista de candidatos, não um seletor único.

Exemplo para UF no SIMAX:

JSON

[

{

"selector": "#lstUf",

"strategy": "id",

"score_base": 0.95

},

{

"selector": "select[name='lstUf']",

"strategy": "name+tag",

"score_base": 0.93

},

{

"selector": "select.form-select.form-select-sm",

"strategy": "tag+class",

"score_base": 0.40

},

{

"selector": "text=Selecione",

"strategy": "text",

"score_base": 0.10

}

]

Mostrar mais linhas

Repare que text=Selecione não desaparece, mas fica com score baixo.
5. Criar um score de locator com critérios objetivos

Eu usaria um score composto, com pesos explícitos.

Sugestão:

Plain Text

score_total =

0.25 * uniqueness_score +

0.20 * semantic_affinity_score +

0.20 * actionability_score +

0.15 * stability_score +

0.10 * context_score +

0.10 * history_score

Mostrar mais linhas
5.1. Uniqueness score

Mede quantos elementos o seletor encontra.

Python

async def uniqueness_score(page, selector):

count = await page.locator(selector).count()

 

if count == 1:

return 1.0

if count == 0:

return 0.0

if count <= 3:

return 0.4

return 0.1

Mostrar mais linhas
5.2. Semantic affinity score

Compara o candidato com a intenção original.

Exemplo:

    evento original: label UF, name lstUf, tag select;
    candidato: select[name="lstUf"];
    afinidade alta.

Critérios:

Plain Text

+ tag igual

+ id igual

+ name igual

+ label igual ou parecido

+ accessible_name parecido

+ placeholder parecido

+ texto compatível

- texto genérico

- tag incompatível

Mostrar mais linhas
5.3. Actionability score

Antes de aceitar o locator, validar se ele é interagível.

Para click:

Python

locator = page.locator(selector)

await expect(locator).to_be_visible()

await expect(locator).to_be_enabled()

Mostrar mais linhas

Para select:

Python

locator = page.locator(selector)

await expect(locator).to_be_visible()

await locator.select_option(value)

Mostrar mais linhas

Para fill:

Python

locator = page.locator(selector)

await expect(locator).to_be_editable()

await locator.fill(value)

Mostrar mais linhas
5.4. Stability score

Penalizar atributos instáveis:

    classes geradas por framework;
    ids com hash;
    caminhos CSS longos;
    índices nth-child;
    textos dinâmicos;
    valores mascarados;
    datas absolutas quando não forem parte da intenção.

5.5. Context score

O seletor deve estar no mesmo contexto:

    mesmo formulário;
    mesma seção;
    perto da mesma label;
    mesmo modal;
    mesma tabela;
    mesma rota;
    mesmo frame, quando houver iframe.

5.6. History score

Se um locator já funcionou várias vezes para a mesma intenção, aumentar score.

Exemplo:

JSON

{

"intent": "selecionar UF no SIMAX",

"best_selector": "select[name='lstUf']",

"success_count": 12,

"failure_count": 0,

"last_success_at": "2026-06-15T17:50:00Z"

}

Mostrar mais linhas
6. Penalizar fortemente candidatos genéricos

O TestForge precisa de uma lista de textos e padrões genéricos para penalização.

Exemplos:

Plain Text

Selecione

OK

Cancelar

Avançar

Próximo

Pesquisar

Calcular

Página inicial

Sim

Não

Mostrar mais linhas

Não significa que esses textos nunca possam ser usados. Significa que eles precisam de escopo.

Ruim:

Python

page.get_by_text("Calcular").click()

Mostrar mais linhas

Melhor:

Python

page.get_by_role("button", name=re.compile("Calcular")).click()

Mostrar mais linhas

Ainda melhor, se houver contexto:

Python

form.locator("button", has_text="Calcular").click()

Mostrar mais linhas
7. Resolver selects como uma classe especial de problema

Para sistemas internos/legados, select é frequente. Eu criaria uma estratégia própria.
Durante a gravação

Capturar:

JSON

{

"tag": "select",

"id": "lstUf",

"name": "lstUf",

"label": "UF",

"value_before": "0",

"value_after": "MT",

"selected_text": "MT",

"options": [

{"value": "0", "text": "Selecione"},

{"value": "MT", "text": "MT"}

]

}

Mostrar mais linhas
Durante a compilação

Gerar:

Python

page.locator('select[name="lstUf"]').select_option("MT")

Mostrar mais linhas
Durante o healing

Se value não existir mais, tentar por texto:

Python

page.locator('select[name="lstUf"]').select_option(label="MT")

Mostrar mais linhas

Se o select mudou de name, procurar por label:

Python

page.locator("label", has_text="UF").locator("xpath=following::select[1]")

Mostrar mais linhas
8. Melhorar asserts com seletores orientados a resultado

Assertions devem ser diferentes de ações.

Para ação, buscamos o elemento interativo.

Para assert, buscamos evidência de resultado.

No simulador habitacional, em vez de assert com CSS estrutural enorme, usar algo como:

Python

await expect(page.get_by_text("Valor mínimo de entrada")).to_be_visible()

Mostrar mais linhas

Ou:

Python

await expect(page.locator("body")).to_contain_text("Valor mínimo de entrada")

Mostrar mais linhas

No SIMAX:

Python

await expect(page.get_by_text("Reservar")).to_be_visible()

Mostrar mais linhas

Se houver tabela:

Python

await expect(page.locator("#tblLista")).to_contain_text("Reservar")

Mostrar mais linhas

Isso reduz fragilidade.
9. Usar snapshots de DOM como fonte obrigatória para seleção

Como os snapshots aparecem vazios no contexto analisado, o TestForge está perdendo uma fonte central para melhorar os seletores. [caixa-my.s...epoint.com]

Eu colocaria uma regra dura:

Plain Text

Se o snapshot DOM não foi salvo, o evento fica com qualidade reduzida.

Se mais de N snapshots vazios ocorrerem, a gravação deve terminar com warning crítico.

Mostrar mais linhas

Exemplo:

Python

html = await page.content()

 

if not html or len(html.strip()) < 100:

event.quality_flags.append("DOM_SNAPSHOT_EMPTY")

else:

save_dom_snapshot(event_id, html)

Mostrar mais linhas

Depois, na compilação, usar o DOM para:

    localizar label real;
    mapear label[for];
    identificar formulário;
    detectar select;
    calcular unicidade;
    gerar candidatos alternativos.

10. Criar um “Locator Registry”

Em vez de gerar tudo do zero a cada compile, manter um histórico versionado.

Exemplo:

JSON

{

"application": "simax",

"page": "novo_agendamento",

"elements": {

"uf": {

"intent": "Selecionar UF",

"primary": "select[name='lstUf']",

"fallbacks": [

"#lstUf",

"label:has-text('UF') >> xpath=following::select[1]"

],

"action": "select_option",

"last_known_values": ["DF", "MT", "GO"]

},

"edificio": {

"intent": "Selecionar Edifício",

"primary": "select[name='lstEdificio']",

"fallbacks": [

"#lstEdificio"

],

"action": "select_option"

}

}

}

Mostrar mais linhas

Isso cria memória técnica do sistema e reduz dependência de heurística a cada execução.
11. Separar claramente “locator original”, “locator escolhido” e “locator curado”

No relatório de execução, cada step deveria mostrar:

Plain Text

Step 3 — Selecionar UF

Locator gravado: select[name="lstUf"]

Locator usado: select[name="lstUf"]

Ação: select_option("MT")

Status: passed

Mostrar mais linhas

Quando houver healing:

Plain Text

Step 3 — Selecionar UF

Locator gravado: label:has-text("UF") + input

Falha: não encontrado

Candidatos:

1. select[name="lstUf"] — score 0.94 — aprovado

2. #lstUf — score 0.92 — aprovado

3. text=Selecione — score 0.10 — rejeitado

Locator curado: select[name="lstUf"]

Oracle pós-ação: passou

Status: healed_validated

Mostrar mais linhas

Isso também ajuda a corrigir as métricas inconsistentes de healing que apareceram no log. [caixa-my.s...epoint.com]
12. Aplicar compactação antes de gerar seletores

No login, a gravação gerou muitos fill para o mesmo CPF, caractere por caractere. Isso aumenta o número de seletores e multiplica pontos de falha. [caixa-my.s...epoint.com]

Antes de melhorar selectors, o pipeline deve compactar eventos:

Plain Text

fill CPF = "4"

fill CPF = "40"

fill CPF = "407"

...

fill CPF = "407.825.120-00"

 

=> gerar apenas:

fill CPF = "407.825.120-00"

Mostrar mais linhas

Regra:

Python

def compact_fill_events(events):

compacted = []

 

for event in events:

if event.action == "fill" and same_target_as_previous(event):

compacted[-1] = event

else:

compacted.append(event)

 

return compacted

Mostrar mais linhas

Isso melhora seletor, contagem de passos, legibilidade e execução.
13. Estratégia final de geração de locator

Eu implementaria o pipeline assim:

Plain Text

Evento bruto

↓

Normalização do elemento

↓

Inferência da intenção

↓

Geração de candidatos

↓

Score determinístico

↓

Validação no DOM atual

↓

Escolha do locator primário

↓

Persistência no Locator Registry

↓

Geração do script Playwright

Mostrar mais linhas

Pseudocódigo:

Python

def build_locator_for_event(event, dom_snapshot, history):

semantic_element = normalize_event(event)

 

candidates = []

candidates += generate_role_candidates(semantic_element)

candidates += generate_label_candidates(semantic_element)

candidates += generate_attribute_candidates(semantic_element)

candidates += generate_contextual_candidates(semantic_element, dom_snapshot)

candidates += generate_text_candidates(semantic_element)

candidates += generate_css_fallback_candidates(semantic_element)

 

scored = []

 

for candidate in candidates:

score = calculate_locator_score(

candidate=candidate,

event=event,

dom_snapshot=dom_snapshot,

history=history

)

scored.append((candidate, score))

 

scored.sort(key=lambda item: item[1], reverse=True)

 

return scored[0], scored

Mostrar mais linhas
14. Regras práticas para o TestForge

Eu colocaria estas regras como ADR ou especificação do módulo de seletores:

    Nunca gerar input se o elemento gravado era select.
    Nunca usar text=Selecione como locator primário.
    Nunca usar CSS estrutural longo como primeira opção.
    Nunca aceitar elemento com bounding box zero como alvo principal.
    Sempre preferir id, name, label, role e accessible_name.
    Sempre gerar múltiplos candidatos.
    Sempre validar unicidade antes de executar.
    Sempre validar actionability antes da ação.
    Sempre registrar por que o locator foi escolhido.
    Sempre persistir histórico de sucesso/falha do locator.
    Sempre compactar fills sequenciais.
    Sempre separar selector de ação e selector de assert.
    Sempre tratar <select>, radio, checkbox, input, button e link como famílias diferentes.
    Sempre salvar snapshot DOM não vazio ou emitir alerta crítico.
    Sempre usar oracle pós-ação antes de marcar healing como verdadeiro.

Minha recomendação de implementação em blocos
Bloco 1 — Correção determinística dos seletores

Entregável:

    corrigir select → select_option;
    gerar candidatos por id, name, label, role;
    bloquear selector vazio;
    bloquear tag incompatível.

Bloco 2 — Ranking e validação

Entregável:

    uniqueness score;
    actionability score;
    penalização de texto genérico;
    relatório de candidatos.

Bloco 3 — Locator Registry

Entregável:

    salvar locator escolhido;
    salvar histórico de sucesso/falha;
    reusar melhor locator em execuções futuras.

Bloco 4 — Healing determinístico

Entregável:

    quando locator falhar, testar fallbacks determinísticos;
    só escalar para LLM se os candidatos determinísticos falharem;
    validar com oracle pós-ação.

Bloco 5 — LLM como curador, não como primeira solução

Entregável:

    LLM recebe evento, DOM, candidatos e histórico;
    LLM apenas reordena/explica/sugere;
    decisão final passa pelo validador determinístico.

Conclusão

A melhor estratégia para melhorar os seletores no TestForge é tratar locator como um artefato versionável e validável, não como string gerada no momento. O TestForge precisa sair de:

Plain Text

evento → selector textual frágil → execução

Mostrar mais linhas

para:

Plain Text

evento → intenção semântica → candidatos → score → validação → histórico → execução

Mostrar mais linhas

Se fizermos isso, o SIMAX deixa de quebrar por label + input, o simulador habitacional deixa de depender de CSS estrutural e o healer passa a atuar em cima de evidência real, não de tentativa e erro.

 
