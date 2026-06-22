# TESTFORGE
## Agente Curador de Scripts  

### Capítulo 1  
**Taxonomia de Falhas — JSF, jQuery, AJAX e Frameworks Mobile**  

Versão 1.0  
Iteração 1 de 4  

> **Nota de alinhamento (Jun/2026):** Esta versão documenta 6 famílias de falhas.
> A taxonomia oficial evoluiu para **11 famílias (FAM-01 a FAM-11)** no
> [`taxonomy.cases.yaml`](../taxonomia_extracted/taxonomy.cases.yaml),
> com 70+ casos e IDs taxonômicos (SEL-001, TIM-006, etc.).
> As 5 famílias adicionais são: **Asserts (FAM-07)**, **Recorder (FAM-08)**,
> **Observabilidade (FAM-09)**, **Arquivos (FAM-10)** e **Limites técnicos (FAM-11)**.
> Vide [`taxonomy-registry.yaml`](../taxonomia_extracted/taxonomy-registry.yaml)
> para o registro completo com estados e estratégias.  

---

## 1. Introdução e Propósito da Taxonomia

Este capítulo estabelece a base especificativa do Agente Curador de Scripts do TestForge. A taxonomia aqui descrita não é apenas um catálogo de problemas — ela é a especificação funcional do curador. Cada categoria de falha mapeada corresponde diretamente a um conjunto de comportamentos que o agente deve ser capaz de detectar, classificar e resolver.

O curador opera no ponto mais crítico do pipeline TestForge: recebe gravações brutas do Smart Recorder e deve transformá-las em casos de teste estáveis e reutilizáveis. Para isso, precisa lidar com a realidade heterogênea da stack tecnológica da empresa, que combina tecnologias com comportamentos de DOM radicalmente diferentes entre si.

### Princípios que guiam a taxonomia:

- Toda falha que o curador deve tratar precisa ter entrada, saída e critério de sucesso definidos antes de qualquer linha de código  
- A prioridade (P0/P1/P2) reflete o impacto direto na taxa de falsos negativos do pipeline de testes  
- Cada categoria gera pelo menos um caso de teste automatizado do próprio curador  
- A taxonomia é versionável — novos padrões descobertos em produção devem ser incorporados  

---

## 2. Mapa Tecnológico da Empresa

Antes de detalhar as falhas, é necessário compreender o ambiente onde o curador vai operar.

### 2.1 Stack Frontend Identificada

| Tecnologia                 | Geração de IDs                                      | Comportamento AJAX                          | Risco Principal |
|--------------------------|-----------------------------------------------------|---------------------------------------------|----------------|
| JSF / PrimeFaces         | IDs dinâmicos (ex: j_idt342:tabela:0:btn)            | f:ajax com ViewState                        | Seletores quebram |
| jQuery / jQuery UI       | IDs estáticos com elementos injetados               | $.ajax / callbacks                          | Overlays fora do contexto |
| Angular                  | IDs ausentes; uso de data-*                         | HttpClient assíncrono                       | Encapsulamento |
| Legacy JSP + JS          | IDs misturados                                     | XMLHttpRequest manual                       | Timing imprevisível |
| Ionic / Cordova          | IDs baseados em rotas                              | Plugins assíncronos                         | Webview híbrido |

---

## 3. Taxonomia Completa de Falhas

As falhas estão organizadas em seis famílias.

---

### 3.1 Família 1 — Seletores Frágeis

Principais causas de falhas em automação.

| Categoria | Tipo de Falha | Exemplo | Estratégia | Prioridade |
|----------|--------------|--------|-----------|-----------|
| JSF      | ID dinâmico  | j_idt342:tabela:0 | Fallback por texto/aria | P0 |
| JSF      | widgetVar instável | PF('wgt') | Scan registry PrimeFaces | P0 |
| jQuery   | Elemento fora do form | dialogs | Usar role ARIA | P0 |
| Angular  | Sem ID      | componentes | data-testid / texto | P1 |
| Geral    | XPath absoluto | /html/body/... | Converter para locator semântico | P0 |

---

### 3.2 Família 2 — Timing e Assincronismo

Substituir waits fixos por estratégias inteligentes.

| Categoria | Falha | Estratégia |
|----------|------|-----------|
| JSF AJAX | Executar antes do re-render | wait network idle |
| JSF      | ViewState inválido | nunca capturar manualmente |
| jQuery   | Callback sem evento DOM | interceptação de rede |
| Angular  | Change detection async | waitForFunction |
| Geral    | waitForTimeout | usar waits baseados em DOM |

---

### 3.3 Família 3 — Contexto e Escopo

Problemas de iframe, shadow DOM e contexto.

- Detectar e operar no frame correto  
- Re-adquirir referências após reload  
- Suportar shadow DOM (Playwright >>)  
- Manipular popups e novas abas  

---

### 3.4 Família 4 — Estado da Aplicação

Falhas relacionadas ao estado da aplicação.

- Sessão expirada → re-auth automático  
- Overlay bloqueando clique → dismiss  
- Dados sujos → validação de pré-condição  
- Alert nativo → handler global  

---

### 3.5 Família 5 — DOM Dinâmico

Problemas causados por re-renderização.

- Nunca cachear elementos  
- Rebuscar locators sempre  
- Usar seletores por conteúdo, não índice  
- Aguardar estabilidade do DOM  

---

### 3.6 Família 6 — Input e Interação Especializada

Casos especiais de interação.

- Upload de arquivos (PrimeFaces)  
- Drag-and-drop (jQuery UI)  
- Autocomplete com debounce  
- Rich text editors via iframe  
- CAPTCHA → intervenção manual  

---

## 4. Catálogo de Estratégias de Healing

Principais estratégias:

- **label_proximity** → baseado em label  
- **text_content_match** → texto visível  
- **aria_role_strategy** → atributos ARIA  
- **shadow_pierce** → acessar shadow DOM  
- **frame_reacquire** → reacquirir frames  
- **network_idle_wait** → aguardar requisições  
- **response_intercept** → interceptar API  
- **dom_stabilization** → aguardar estabilidade  
- **overlay_dismiss** → fechar overlays  
- **re_auth_hook** → reautenticação automática  
- **llm_selector_inference** → fallback com LLM  

---

## 5. Hierarquia de Decisão do Curador

Fluxo de recuperação:

1. Identificar a família da falha  
2. Mapear tecnologia  
3. Aplicar estratégia específica  
4. Tentar fallback  
5. Usar LLM se necessário  
6. Marcar como UNRESOLVED se falhar  
7. Registrar healing  
8. Gerar relatório  

---

## 6. Priorização por Fase

| Fase | Foco | Resultado Esperado |
|------|------|------------------|
| Fase 1 | Seletores + Timing | 95% recuperação JSF |
| Fase 2 | Contexto + Estado | suporte a iframes/dialogs |
| Fase 3 | DOM dinâmico | pipeline completo |
| Fase 4 | LLM + Mobile | <5% falhas |

---

## 7. Resumo e Próximos Passos

- 6 famílias de falhas definidas  
- 50+ cenários mapeados  
- 13 estratégias catalogadas  

### Próximos capítulos:

- Capítulo 2 → Log de observabilidade  
- Capítulo 3 → Harness de testes  
- Capítulo 4 → Arquitetura do curador  

---