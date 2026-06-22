# TESTFORGE — Taxonomia Implementável de Casos Conhecidos

**Projeto:** TestForge / Agente Curador de Scripts  
**Artefato:** Taxonomia implementável para detecção, classificação, healing e geração de testes  
**Versão:** 1.0  
**Base:** Capítulo 1 — Taxonomia de Falhas JSF, jQuery, AJAX e Frameworks Mobile

---

## 1. Objetivo

Esta taxonomia transforma os casos conhecidos de falha em um catálogo implementável para o Agente Curador do TestForge.

Cada caso define:

- **ID taxonômico**: identificador estável para implementação, testes e rastreabilidade.
- **Família**: agrupamento funcional da falha.
- **Tecnologia afetada**: stack ou contexto onde o caso ocorre.
- **Sintoma observável**: como a falha aparece na gravação, execução ou curadoria.
- **Causa provável**: origem técnica mais comum.
- **Detecção mínima**: sinais que o curador deve usar para classificar o caso.
- **Estratégia principal**: healing ou tratamento preferencial.
- **Fallbacks**: alternativas em ordem de tentativa.
- **Saída esperada**: resultado que o curador deve produzir.
- **Critério de sucesso**: regra objetiva para considerar o caso resolvido.
- **Prioridade**: P0, P1 ou P2.

---

## 2. Convenções de Implementação

### 2.1 Prioridade

| Prioridade | Significado |
|---|---|
| P0 | Deve ser tratado no MVP; afeta diretamente a estabilidade básica dos scripts. |
| P1 | Deve ser tratado após estabilização do núcleo; comum, mas pode ter workaround manual. |
| P2 | Tratamento avançado, especializado ou dependente de contexto. |

### 2.2 Estados de Resultado

| Estado | Significado |
|---|---|
| RESOLVED | O curador classificou e aplicou uma correção validada. |
| PARTIALLY_RESOLVED | O curador aplicou correção, mas deixou ressalvas ou dependência manual. |
| MANUAL_REQUIRED | O caso exige intervenção humana explícita. |
| UNRESOLVED | O curador não conseguiu resolver com segurança. |
| REJECTED | A correção proposta foi rejeitada pelo validador. |

### 2.3 Estratégias conhecidas

- `label_proximity`
- `text_content_match`
- `aria_role_strategy`
- `semantic_locator_conversion`
- `primefaces_registry_scan`
- `frame_reacquire`
- `shadow_pierce`
- `network_idle_wait`
- `response_intercept`
- `dom_stabilization`
- `overlay_dismiss`
- `re_auth_hook`
- `llm_selector_inference`
- `download_event_capture`
- `upload_payload_binding`
- `assert_overlay_capture`
- `manual_checkpoint`

---

## 3. Famílias Taxonômicas

A taxonomia está organizada nas seguintes famílias:

1. Seletores frágeis
2. Timing e assincronismo
3. Contexto e escopo
4. Estado da aplicação
5. DOM dinâmico
6. Input e interação especializada
7. Upload e download de arquivos
8. Asserts e validações
9. Recorder, overlay e checkpoints manuais
10. Execução, evidência e observabilidade
11. Limites técnicos e casos não automatizáveis

---

## 4. Catálogo Implementável

### Família 1 — Seletores Frágeis

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| SEL-001 | ID JSF dinâmico | JSF / PrimeFaces | Locator gravado quebra entre execuções | ID contém padrão `j_idt`, índice variável ou prefixos JSF encadeados | `semantic_locator_conversion` | `label_proximity`, `text_content_match`, `aria_role_strategy`, `llm_selector_inference` | Locator semântico Playwright | Elemento é localizado em 3 execuções limpas | P0 |
| SEL-002 | ID com índice de tabela | JSF / PrimeFaces | Ação aponta para linha errada | Locator contém índice numérico em tabela/lista | `label_proximity` associado à linha | `text_content_match`, filtro por célula, `llm_selector_inference` | Locator contextual por linha | A ação ocorre na linha correta | P0 |
| SEL-003 | `widgetVar` instável | PrimeFaces | Script depende de `PF('x')` que muda | Uso direto de `PF(...)` ou widget sem evidência semântica | `primefaces_registry_scan` | role ARIA, texto visível, label | Locator independente de `widgetVar` | Elemento interage sem depender do nome do widget | P0 |
| SEL-004 | XPath absoluto | Geral | Locator quebra com pequena mudança estrutural | XPath inicia em `/html/body` ou usa cadeia longa de índices | `semantic_locator_conversion` | role, texto, label, CSS estável | Locator Playwright resiliente | XPath absoluto removido | P0 |
| SEL-005 | CSS baseado em classe volátil | Angular / frameworks modernos | Elemento não encontrado após build ou deploy | Classe parece hash, gerada, minificada ou utilitária sem semântica | `aria_role_strategy` | `data-testid`, texto, label | Locator orientado a intenção | Classe volátil não é seletor primário | P1 |
| SEL-006 | Elemento sem ID | Angular / componentes modernos | Recorder gera locator genérico ou por índice | Ausência de ID/name; presença de texto, role ou `data-*` | `aria_role_strategy` | `text_content_match`, `data-testid`, label | Locator semântico | Elemento localizado sem índice absoluto | P1 |
| SEL-007 | Elemento fora do formulário | jQuery UI / dialogs | Botão em modal não é localizado no escopo esperado | Elemento visual está fora do form/árvore original | `aria_role_strategy` global/contextual | dialog role, texto, overlay container | Locator no escopo real do DOM | Clique ocorre no botão visível correto | P0 |
| SEL-008 | Locator por posição | Geral | Ação quebra quando ordem visual muda | Uso de `.nth()` sem justificativa | `semantic_locator_conversion` | filtro por texto, label, role | Locator contextual | `.nth()` removido ou justificado | P1 |
| SEL-009 | Texto duplicado | Geral | Curador escolhe elemento errado com mesmo texto | Múltiplos elementos correspondem ao mesmo texto | `label_proximity` + escopo | role, container, frame, linha de tabela | Locator desambiguado | Match único ou escopo explícito | P0 |
| SEL-010 | Label não associado via `for` | Legado / JSF | Campo não é encontrado por label padrão | Label visual próximo, mas sem associação HTML | `label_proximity` | heurística espacial, placeholder, name | Locator por proximidade | Campo correto localizado | P1 |

---

### Família 2 — Timing e Assincronismo

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| TIM-001 | Ação antes do re-render JSF | JSF AJAX | Clique ou assert ocorre antes da atualização | Requisição AJAX seguida de DOM substituído | `network_idle_wait` + `dom_stabilization` | aguardar seletor alvo, response intercept | Wait semântico inserido | Próxima ação encontra DOM atualizado | P0 |
| TIM-002 | ViewState inválido | JSF | Submissão falha após gravação | Captura ou reutilização explícita de ViewState | Não capturar manualmente ViewState | reexecutar fluxo, aguardar form atualizado | Script sem ViewState hardcoded | Nenhum ViewState fixo no script | P0 |
| TIM-003 | Callback jQuery sem evento DOM claro | jQuery | Teste avança sem mudança visível imediata | XHR/fetch finaliza, mas DOM muda depois | `response_intercept` | waitForFunction, wait por seletor | Wait baseado em resposta ou condição | Condição de negócio observável é satisfeita | P1 |
| TIM-004 | Change detection assíncrono | Angular | Assert lê valor antigo | Presença de Angular e mudanças após microtasks | `waitForFunction` | wait por texto/estado, network idle | Wait por condição da UI | Assert passa sem timeout fixo | P1 |
| TIM-005 | `waitForTimeout` gravado | Geral | Script fica lento ou flaky | Presença de sleeps fixos | Substituir por wait semântico | DOM, rede, seletor, resposta | Timeout fixo removido | Execução estável sem espera arbitrária | P0 |
| TIM-006 | Debounce em autocomplete | Geral / jQuery / Angular | Opções não aparecem no momento do clique | Input seguido de lista assíncrona | Wait por lista/opção | response intercept, waitForFunction | Seleção robusta | Opção correta selecionada | P1 |
| TIM-007 | Navegação parcial sem page load | SPA / AJAX | `waitForLoadState` não resolve o estado real | URL muda ou componente troca sem navegação completa | Wait por marcador de tela | DOM stabilization, rede | Wait de tela pronta | Próxima ação só ocorre com tela estável | P1 |

---

### Família 3 — Contexto e Escopo

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| CTX-001 | Iframe same-origin | Geral | Elemento não encontrado no `page` principal | Elemento existe dentro de frame acessível | `frame_reacquire` | frame por URL, título, nome, seletor | Locator usando `frameLocator` | Ação ocorre dentro do frame correto | P0 |
| CTX-002 | Iframe cross-origin | Geral / portais corporativos | Script não consegue injetar ou inspecionar DOM | Frame bloqueia acesso por origem | `manual_checkpoint` | interação Playwright limitada, contrato externo | Marcação MANUAL_REQUIRED ou estratégia segura | Curador não fabrica seletor inacessível | P0 |
| CTX-003 | Shadow DOM aberto | Web Components | Elemento não localizado por CSS comum | Elemento está sob shadow root aberto | `shadow_pierce` | role/text se suportado | Locator compatível com Playwright | Elemento localizado dentro do shadow DOM | P1 |
| CTX-004 | Shadow DOM fechado | Web Components | Elemento inacessível | Shadow root fechado | `manual_checkpoint` | API pública do componente, contrato de teste | MANUAL_REQUIRED ou UNRESOLVED justificado | Curador não gera locator inválido | P2 |
| CTX-005 | Popup/nova aba | Geral | Ação abre nova página e script continua na antiga | Evento `popup` ou nova página no contexto | Capturar popup/page | esperar URL/título | Script troca contexto | Próxima ação executa na página correta | P0 |
| CTX-006 | Modal/dialog fora do escopo | jQuery UI / PrimeFaces | Botão visível não encontrado | Container do modal fora do componente original | Escopo por dialog/role | overlay container, texto | Locator dentro do modal | Clique no elemento visível correto | P0 |
| CTX-007 | Frame recarregado | Geral | Handle antigo falha após reload | Frame detach/attach entre ações | `frame_reacquire` | aguardar frame por URL/name | Não cachear frame handle | Ação ocorre após reacquisição | P1 |

---

### Família 4 — Estado da Aplicação

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| STA-001 | Sessão expirada | Geral | Redirecionamento para login ou tela de sessão | URL/texto indica expiração/login | `re_auth_hook` | checkpoint manual, fixture de autenticação | Fluxo de reautenticação isolado | Teste retorna ao ponto esperado | P0 |
| STA-002 | Overlay bloqueando clique | JSF / jQuery / Geral | Playwright informa elemento coberto | Overlay visível intercepta pointer events | `overlay_dismiss` | aguardar sumir, ESC, botão fechar | Overlay removido antes do clique | Clique executado no elemento alvo | P0 |
| STA-003 | Dados sujos | Geral | Pré-condição não satisfeita | Tela mostra registro existente, duplicidade ou estado anterior | Validação de pré-condição | setup/teardown, massa dedicada | Script com pré-condição explícita | Teste não depende de estado residual | P1 |
| STA-004 | Alert/confirm/prompt nativo | Geral | Execução trava aguardando diálogo | Evento dialog emitido | Handler global de diálogo | política accept/dismiss configurável | Tratamento explícito de dialog | Execução não trava | P0 |
| STA-005 | Permissão insuficiente | Geral | Botão ausente ou acesso negado | Texto/HTTP/URL indica restrição | Classificação de ambiente/perfil | checkpoint manual, skip justificado | MANUAL_REQUIRED ou UNRESOLVED | Falha classificada corretamente | P1 |
| STA-006 | Ambiente indisponível/intermitente | Geral | Erro HTTP, timeout global, tela de indisponibilidade | HTTP 5xx, DNS, proxy, tela erro | Classificar como falha de ambiente | retry controlado, evidência | Relatório de ambiente | Curador não altera script indevidamente | P1 |

---

### Família 5 — DOM Dinâmico

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| DOM-001 | Element handle cacheado | Geral | Erro de elemento detached/stale | Reuso de handle após ação que altera DOM | Rebuscar locator sempre | locator lazy, reacquire | Script sem cache de elemento | Sem erro detached em reexecução | P0 |
| DOM-002 | Lista reordenada | Geral | Ação em item errado | Seleção por índice em lista dinâmica | Selecionar por conteúdo/chave | filtro por linha, texto, atributo estável | Locator por identidade do item | Item correto é afetado | P0 |
| DOM-003 | Re-render substitui nó | JSF / Angular | Elemento encontrado antes, falha depois | Nó detach após AJAX/change detection | `dom_stabilization` + reacquire | wait por novo seletor | Reaquisição após render | Próxima ação usa nó atual | P0 |
| DOM-004 | Virtualização de lista | Angular / frameworks UI | Item não está no DOM até scroll | Lista renderiza apenas elementos visíveis | Scroll controlado até item | busca incremental, API de filtro | Acesso robusto ao item | Item visível antes da interação | P2 |
| DOM-005 | Lazy loading visual | Geral | Imagem/componente não aparece imediatamente | Placeholder ou skeleton na tela | Wait por conteúdo real | network idle, selector state | Espera por componente pronto | Assert não valida placeholder | P1 |

---

### Família 6 — Input e Interação Especializada

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| INP-001 | Upload PrimeFaces | PrimeFaces | Upload gravado não reproduz | Componente fileUpload ou input file encapsulado | `upload_payload_binding` | localizar input real, fixture de arquivo | Upload parametrizado | Arquivo anexado e UI confirma | P0 |
| INP-002 | Upload HTML padrão | Geral | Caminho local absoluto inválido | `input[type=file]` com path local gravado | Fixture de arquivo | parametrização por massa | Caminho relativo/fixture | Upload funciona em ambiente limpo | P0 |
| INP-003 | Download disparado por clique | Geral | Arquivo baixado não é validado | Evento download após ação | `download_event_capture` | validar nome/tipo/tamanho/hash | Bloco `expect_download` | Download capturado e validado | P0 |
| INP-004 | Download AJAX/Blob | SPA / Angular / JS | Não há navegação nem link direto | Blob, fetch ou object URL | Interceptar resposta/download | validar artefato gerado | Captura por evento/rede | Arquivo validado | P1 |
| INP-005 | Drag-and-drop | jQuery UI / HTML5 | Ação gravada não reproduz movimento | Eventos drag/drop ou componente sortable | Simular drag semântico | mouse events controlados | Interação encapsulada | Item muda para posição esperada | P1 |
| INP-006 | Rich text editor via iframe | Geral | Texto não é preenchido | Editor usa iframe/contenteditable | `frame_reacquire` + contenteditable | API do editor, teclado | Escrita no editor correto | Conteúdo final validado | P1 |
| INP-007 | Máscara de input | Geral | Valor digitado difere do esperado | Campo formata CPF, moeda, data etc. | Preencher como usuário | validar valor normalizado | Input compatível com máscara | Valor aceito pela UI | P1 |
| INP-008 | CAPTCHA | Geral | Fluxo bloqueado | Presença de CAPTCHA/desafio humano | `manual_checkpoint` | bypass de ambiente de teste se existir | MANUAL_REQUIRED | Curador não tenta burlar desafio | P0 |
| INP-009 | Seleção de data em calendário | JSF / jQuery UI / Angular | Data não seleciona por input direto | Datepicker intercepta input | Seleção por componente | preenchimento + blur, teclado | Data selecionada e validada | Campo contém data correta | P1 |
| INP-010 | Combobox customizado | Geral | Select HTML não existe | Role combobox/listbox ou div customizada | `aria_role_strategy` | texto/opção, teclado | Seleção por opção visível | Valor final exibido correto | P1 |

---

### Família 7 — Upload e Download de Arquivos

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| FILE-001 | Arquivo local inexistente na execução | Geral | Upload falha por caminho da máquina do gravador | Path absoluto do usuário na gravação | Converter para fixture versionada | parametrizar massa | Referência portável | Execução funciona em outro ambiente | P0 |
| FILE-002 | Upload com validação de extensão | Geral | Sistema rejeita arquivo | Mensagem de extensão/tipo inválido | Registrar metadados do arquivo | fixture compatível | Massa válida | Upload aceito | P1 |
| FILE-003 | Upload com limite de tamanho | Geral | Rejeição por tamanho | Mensagem de limite ou HTTP erro | Registrar tamanho e política | fixture menor | Massa adequada | Upload aceito ou falha esperada assertada | P1 |
| FILE-004 | Download com nome dinâmico | Geral | Nome muda a cada execução | Nome contém data, protocolo, hash | Validar por padrão/regex | validar tipo e conteúdo | Assert flexível | Download identificado sem nome fixo | P1 |
| FILE-005 | Download precisa de autenticação | Geral | Link direto falha fora da sessão | Download depende da sessão atual | Capturar no contexto autenticado | evento download | Download dentro do fluxo | Arquivo recebido na sessão | P0 |
| FILE-006 | Download bloqueado por popup/aba | Geral | Arquivo abre em nova aba ou viewer | Evento popup ou content-disposition ausente | Capturar popup/download | validar URL/conteúdo | Tratamento de nova aba | Artefato validado | P1 |

---

### Família 8 — Asserts e Validações

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| AST-001 | Assert informado antes da gravação | Recorder/TestForge | Usuário declara objetivo antes do fluxo | Assert associado ao plano inicial | `assert_overlay_capture` | template de assert | Assert planejado | Assert aparece no script final | P0 |
| AST-002 | Assert informado durante a gravação | Recorder/TestForge | Usuário marca elemento/estado no overlay | Evento de overlay com alvo e intenção | `assert_overlay_capture` | snapshot DOM, texto, role | Assert contextual | Assert valida o estado marcado | P0 |
| AST-003 | Assert informado depois da gravação | Curador/TestForge | Usuário complementa validações pós-gravação | Metadado pós-gravação vinculado a step/tela | Vincular assert ao step correto | LLM inference com revisão | Assert pós-processado | Assert inserido no ponto adequado | P0 |
| AST-004 | Assert de texto visível | Geral | Precisa validar mensagem/resultado | Texto alvo definido ou inferível | `text_content_match` | regex, contains, exact | Expect de texto | Texto validado sem seletor frágil | P0 |
| AST-005 | Assert de URL/rota | SPA / Geral | Precisa validar navegação | Mudança de URL/rota | Expect URL/padrão | marcador de tela | Validação de rota | URL corresponde ao padrão esperado | P1 |
| AST-006 | Assert de arquivo baixado | Geral | Precisa validar download | Evento download associado | `download_event_capture` | nome/tipo/tamanho/hash/conteúdo | Expect do artefato | Arquivo correto validado | P0 |
| AST-007 | Assert de estado visual | Geral | Botão habilitado, campo preenchido, item selecionado | Estado DOM/ARIA detectável | role/state assertion | atributo, classe estável | Expect de estado | Estado final correto | P1 |
| AST-008 | Assert ambíguo | Geral | Usuário diz “verificar se deu certo” sem alvo | Intenção sem elemento/condição objetiva | Solicitar/registrar checkpoint manual | sugestão de assert | MANUAL_REQUIRED | Não gerar assert inventado | P0 |
| AST-009 | Assert de tabela/lista | Geral | Precisa validar presença de registro | Tabela/lista com texto/colunas | filtro por linha/célula | texto, chave, regex | Assert por conteúdo | Linha correta validada | P1 |
| AST-010 | Assert negativo | Geral | Validar ausência de erro/item | Intenção de ausência | Expect not visible/not contains | wait controlado | Assert negativo seguro | Ausência confirmada após estabilidade | P1 |

---

### Família 9 — Recorder, Overlay e Checkpoints Manuais

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| REC-001 | Gravação incompleta | Recorder | Fluxo termina sem estado final claro | Sessão encerrada sem assert final | Gerar script parcial com checkpoint | marcar pendências | PARTIALLY_RESOLVED | Script deixa ponto de retomada claro | P0 |
| REC-002 | Overlay captura intenção do usuário | Recorder | Usuário adiciona comentário/assert/dado | Evento do overlay com timestamp/step | Persistir anotação estruturada | vincular por tela/DOM snapshot | Metadado rastreável | Curador usa anotação no script | P0 |
| REC-003 | Usuário pausa gravação | Recorder | Intervalo sem eventos úteis | Evento pause/resume | Ignorar intervalo | registrar checkpoint | Gravação limpa | Sem sleeps artificiais pelo tempo pausado | P1 |
| REC-004 | Navegação manual fora do fluxo | Recorder | Usuário muda URL/aba sem ação clara | Mudança de página sem evento de interação | Classificar como transição manual | checkpoint/observação | Step explícito | Fluxo fica rastreável | P1 |
| REC-005 | Recon/fingerprint inicial | Recorder | Coleta de stack/DOM/ambiente no início | Execução de fingerprint antes/durante gravação | Registrar mapa tecnológico | enriquecer com rede/frames | Contexto para curadoria | Taxonomia usa tecnologia detectada | P0 |
| REC-006 | Evento bloqueado por política do browser/app | Recorder | Evento não capturado ou bloqueado | Falta de evento esperado + mudança visual | Snapshot antes/depois | checkpoint manual | Evento sintético classificado | Curador não inventa causa | P1 |

---

### Família 10 — Execução, Evidência e Observabilidade

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| OBS-001 | Falha sem screenshot/trace | Execução | Erro sem evidência suficiente | Falha Playwright sem artefatos | Coletar screenshot, trace, console, HAR se configurado | snapshot DOM | Evidência anexada | Relatório permite diagnóstico | P0 |
| OBS-002 | Console error relevante | Geral | UI falha por erro JS | Console error durante step | Registrar e correlacionar | anexar stack | Diagnóstico enriquecido | Erro aparece no relatório | P1 |
| OBS-003 | Erro de rede relevante | Geral | Ação falha por HTTP/API | Response 4xx/5xx ou timeout | `response_intercept` | HAR/log de rede | Diagnóstico de rede | Falha classificada como rede/app | P1 |
| OBS-004 | Healing aplicado sem rastreabilidade | Curador | Script muda sem justificar | Patch sem motivo/caso taxonômico | Registrar ID taxonômico e estratégia | diff anotado | Patch auditável | Toda mudança tem causa e evidência | P0 |
| OBS-005 | Rejeição repetida do mesmo patch | Curador | Patch falha repetidamente | Contador de rejeições por assinatura | Marcar UNRESOLVED após limite definido | abrir pendência manual | UNRESOLVED justificado | Loop de healing interrompido | P0 |
| OBS-006 | Flakiness não determinística | Execução | Passa/falha alternadamente | Resultado instável entre rodadas | Rodadas limpas consecutivas antes de promover | classificar flaky | Script só é promovido após estabilidade | Promoção baseada em execução limpa | P0 |

---

### Família 11 — Limites Técnicos e Casos Não Automatizáveis com Segurança

| ID | Caso | Tecnologia | Sintoma observável | Detecção mínima | Estratégia principal | Fallbacks | Saída esperada | Critério de sucesso | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| LIM-001 | CAPTCHA/desafio humano | Geral | Desafio exige validação humana | CAPTCHA visível ou provedor conhecido | `manual_checkpoint` | ambiente de teste com bypass oficial | MANUAL_REQUIRED | Curador não tenta burlar | P0 |
| LIM-002 | Cross-origin inacessível | Browser security | DOM de frame não pode ser inspecionado | Erro de origem/acesso negado | `manual_checkpoint` | interação limitada se possível | MANUAL_REQUIRED/UNRESOLVED | Sem locator fabricado | P0 |
| LIM-003 | Dado sensível mascarado | Geral | Valor não pode ser persistido em claro | Campo marcado sensível ou política detectada | Mascaramento/tokenização | fixture segura | Dado protegido | Relatório não expõe segredo | P0 |
| LIM-004 | Operação irreversível | Sistemas críticos | Fluxo confirma exclusão/envio/contratação | Botão/ação crítica detectada | Checkpoint de confirmação | ambiente sandbox | MANUAL_REQUIRED | Curador exige confirmação explícita | P0 |
| LIM-005 | Dependência externa instável | Integrações | Resultado depende de sistema externo | Erro/timeouts de terceiro | Classificar dependência | mock/stub se permitido | Falha classificada | Não alterar script indevidamente | P2 |

---

## 5. Matriz de Decisão do Curador

Ordem recomendada de decisão:

1. Identificar tecnologia predominante da tela ou componente.
2. Identificar família da falha.
3. Classificar pelo primeiro ID taxonômico compatível.
4. Coletar evidências mínimas.
5. Aplicar estratégia principal.
6. Validar por execução controlada.
7. Se falhar, aplicar fallback na ordem definida.
8. Se houver risco técnico, segurança, CAPTCHA, cross-origin fechado ou assert ambíguo, marcar como `MANUAL_REQUIRED`.
9. Se as tentativas forem rejeitadas pelo validador, marcar como `UNRESOLVED`.
10. Registrar no relatório: ID, causa, estratégia, patch, evidência e resultado.

---

## 6. Modelo de Registro para Implementação

```yaml
id: SEL-001
family: Seletores frágeis
case: ID JSF dinâmico
technologies:
  - JSF
  - PrimeFaces
priority: P0
observable_symptoms:
  - Locator quebra entre execuções
  - ID contém padrão dinâmico
minimum_detection:
  - pattern: "j_idt"
  - selector_has_numeric_index: true
primary_strategy: semantic_locator_conversion
fallback_strategies:
  - label_proximity
  - text_content_match
  - aria_role_strategy
  - llm_selector_inference
expected_output:
  - Playwright locator semântico
success_criteria:
  - Elemento localizado em execuções repetidas
  - Sem uso de XPath absoluto
result_states:
  success: RESOLVED
  failure: UNRESOLVED
```

---

## 7. Critérios Globais de Aceite

A implementação da taxonomia será considerada adequada quando:

1. Todo caso conhecido possuir ID estável.
2. Toda alteração feita pelo curador referenciar um ID taxonômico.
3. Todo ID P0 possuir pelo menos um teste automatizado do curador.
4. Nenhum caso ambíguo gerar assert, locator ou patch inventado sem evidência.
5. Uploads e downloads forem tratados como artefatos versionáveis, parametrizáveis e verificáveis.
6. Asserts puderem ser informados antes, durante ou depois da gravação.
7. Iframes cross-origin, CAPTCHA e operações irreversíveis forem tratados como checkpoints manuais ou casos não resolvidos com justificativa.
8. O relatório final apresentar: falha, evidência, estratégia, patch, validação e estado.

---

## 8. Próximos Artefatos Recomendados

1. `taxonomy.schema.yaml` — schema formal da taxonomia.
2. `taxonomy.cases.yaml` — catálogo consumível pela implementação.
3. `curator-decision-tree.puml` — diagrama da decisão do curador.
4. `healing-strategies.md` — contrato de cada estratégia.
5. `curator-test-matrix.md` — matriz de testes automatizados por ID.
6. `manual-checkpoint-policy.md` — política para casos MANUAL_REQUIRED.
