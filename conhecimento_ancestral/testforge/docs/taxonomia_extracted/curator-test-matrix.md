# TESTFORGE — Curator Test Matrix

**Objetivo:** matriz mínima de testes automatizados por ID taxonômico, priorizando P0 no MVP.

## Mapeamento Família → ID Taxonômico

| Família Descritiva | ID | Agente Especialista |
|---|---|---|
| Seletores frágeis | FAM-01 | SelectorAgent |
| Timing e assincronismo | FAM-02 | TimingAgent |
| Contexto e escopo | FAM-03 | ContextAgent |
| Estado da aplicação | FAM-04 | StateAgent |
| DOM dinâmico | FAM-05 | TimingAgent (fundido) |
| Input e interação especializada | FAM-06 | InputAgent |
| Asserts e validações | FAM-07 | InputAgent (fundido) |
| Recorder, overlay e checkpoints manuais | FAM-08 | — (layer 2) |
| Execução, evidência e observabilidade | FAM-09 | — (layer 2) |
| Upload e download de arquivos | FAM-10 | InputAgent (fundido) |
| Limites técnicos e casos não automatizáveis | FAM-11 | — (manual) |

| ID | Família | Caso | Prioridade | Tipo mínimo de teste | Fixture/cenário sugerido | Aceite mínimo |
|---|---|---|---|---|---|---|
| SEL-001 | Seletores frágeis | ID JSF dinâmico | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-002 | Seletores frágeis | ID com índice de tabela | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-003 | Seletores frágeis | widgetVar instável | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-004 | Seletores frágeis | XPath absoluto | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-005 | Seletores frágeis | CSS baseado em classe volátil | P1 | Automatizado recomendado | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-006 | Seletores frágeis | Elemento sem ID | P1 | Automatizado recomendado | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-007 | Seletores frágeis | Elemento fora do formulário | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-008 | Seletores frágeis | Locator por posição | P1 | Automatizado recomendado | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-009 | Seletores frágeis | Texto duplicado | P0 | Automatizado obrigatório | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| SEL-010 | Seletores frágeis | Label não associado via for | P1 | Automatizado recomendado | DOM sintético com seletor frágil e alternativa semântica | Classifica ID, aplica política e registra evidência/resultado |
| TIM-001 | Timing e assincronismo | Ação antes do re-render JSF | P0 | Automatizado obrigatório | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-002 | Timing e assincronismo | ViewState inválido | P0 | Automatizado obrigatório | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-003 | Timing e assincronismo | Callback jQuery sem evento DOM claro | P1 | Automatizado recomendado | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-004 | Timing e assincronismo | Change detection assíncrono | P1 | Automatizado recomendado | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-005 | Timing e assincronismo | waitForTimeout gravado | P0 | Automatizado obrigatório | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-006 | Timing e assincronismo | Debounce em autocomplete | P1 | Automatizado recomendado | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| TIM-007 | Timing e assincronismo | Navegação parcial sem page load | P1 | Automatizado recomendado | Página/fixture com alteração assíncrona controlada | Classifica ID, aplica política e registra evidência/resultado |
| CTX-001 | Contexto e escopo | Iframe same-origin | P0 | Automatizado obrigatório | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-002 | Contexto e escopo | Iframe cross-origin | P0 | Automatizado obrigatório | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-003 | Contexto e escopo | Shadow DOM aberto | P1 | Automatizado recomendado | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-004 | Contexto e escopo | Shadow DOM fechado | P2 | Especializado/manual assistido | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-005 | Contexto e escopo | Popup/nova aba | P0 | Automatizado obrigatório | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-006 | Contexto e escopo | Modal/dialog fora do escopo | P0 | Automatizado obrigatório | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| CTX-007 | Contexto e escopo | Frame recarregado | P1 | Automatizado recomendado | Página com frame/modal/shadow/popup conforme o caso | Classifica ID, aplica política e registra evidência/resultado |
| STA-001 | Estado da aplicação | Sessão expirada | P0 | Automatizado obrigatório | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| STA-002 | Estado da aplicação | Overlay bloqueando clique | P0 | Automatizado obrigatório | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| STA-003 | Estado da aplicação | Dados sujos | P1 | Automatizado recomendado | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| STA-004 | Estado da aplicação | Alert/confirm/prompt nativo | P0 | Automatizado obrigatório | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| STA-005 | Estado da aplicação | Permissão insuficiente | P1 | Automatizado recomendado | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| STA-006 | Estado da aplicação | Ambiente indisponível/intermitente | P1 | Automatizado recomendado | Cenário com estado de sessão, overlay, dialog ou indisponibilidade | Classifica ID, aplica política e registra evidência/resultado |
| DOM-001 | DOM dinâmico | Element handle cacheado | P0 | Automatizado obrigatório | DOM que re-renderiza, reordena ou virtualiza elementos | Classifica ID, aplica política e registra evidência/resultado |
| DOM-002 | DOM dinâmico | Lista reordenada | P0 | Automatizado obrigatório | DOM que re-renderiza, reordena ou virtualiza elementos | Classifica ID, aplica política e registra evidência/resultado |
| DOM-003 | DOM dinâmico | Re-render substitui nó | P0 | Automatizado obrigatório | DOM que re-renderiza, reordena ou virtualiza elementos | Classifica ID, aplica política e registra evidência/resultado |
| DOM-004 | DOM dinâmico | Virtualização de lista | P2 | Especializado/manual assistido | DOM que re-renderiza, reordena ou virtualiza elementos | Classifica ID, aplica política e registra evidência/resultado |
| DOM-005 | DOM dinâmico | Lazy loading visual | P1 | Automatizado recomendado | DOM que re-renderiza, reordena ou virtualiza elementos | Classifica ID, aplica política e registra evidência/resultado |
| INP-001 | Input e interação especializada | Upload PrimeFaces | P0 | Automatizado obrigatório | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-002 | Input e interação especializada | Upload HTML padrão | P0 | Automatizado obrigatório | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-003 | Input e interação especializada | Download disparado por clique | P0 | Automatizado obrigatório | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-004 | Input e interação especializada | Download AJAX/Blob | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-005 | Input e interação especializada | Drag-and-drop | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-006 | Input e interação especializada | Rich text editor via iframe | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-007 | Input e interação especializada | Máscara de input | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-008 | Input e interação especializada | CAPTCHA | P0 | Automatizado obrigatório | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-009 | Input e interação especializada | Seleção de data em calendário | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| INP-010 | Input e interação especializada | Combobox customizado | P1 | Automatizado recomendado | Fixture de input especializado/upload/download | Classifica ID, aplica política e registra evidência/resultado |
| FILE-001 | Upload e download de arquivos | Arquivo local inexistente na execução | P0 | Automatizado obrigatório | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| FILE-002 | Upload e download de arquivos | Upload com validação de extensão | P1 | Automatizado recomendado | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| FILE-003 | Upload e download de arquivos | Upload com limite de tamanho | P1 | Automatizado recomendado | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| FILE-004 | Upload e download de arquivos | Download com nome dinâmico | P1 | Automatizado recomendado | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| FILE-005 | Upload e download de arquivos | Download precisa de autenticação | P0 | Automatizado obrigatório | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| FILE-006 | Upload e download de arquivos | Download bloqueado por popup/aba | P1 | Automatizado recomendado | Fixture de arquivo versionado e validação de artefato | Classifica ID, aplica política e registra evidência/resultado |
| AST-001 | Asserts e validações | Assert informado antes da gravação | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-002 | Asserts e validações | Assert informado durante a gravação | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-003 | Asserts e validações | Assert informado depois da gravação | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-004 | Asserts e validações | Assert de texto visível | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-005 | Asserts e validações | Assert de URL/rota | P1 | Automatizado recomendado | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-006 | Asserts e validações | Assert de arquivo baixado | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-007 | Asserts e validações | Assert de estado visual | P1 | Automatizado recomendado | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-008 | Asserts e validações | Assert ambíguo | P0 | Automatizado obrigatório | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-009 | Asserts e validações | Assert de tabela/lista | P1 | Automatizado recomendado | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| AST-010 | Asserts e validações | Assert negativo | P1 | Automatizado recomendado | Evento de assert antes/durante/depois ou assert ambíguo | Classifica ID, aplica política e registra evidência/resultado |
| REC-001 | Recorder, overlay e checkpoints manuais | Gravação incompleta | P0 | Automatizado obrigatório | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| REC-002 | Recorder, overlay e checkpoints manuais | Overlay captura intenção do usuário | P0 | Automatizado obrigatório | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| REC-003 | Recorder, overlay e checkpoints manuais | Usuário pausa gravação | P1 | Automatizado recomendado | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| REC-004 | Recorder, overlay e checkpoints manuais | Navegação manual fora do fluxo | P1 | Automatizado recomendado | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| REC-005 | Recorder, overlay e checkpoints manuais | Recon/fingerprint inicial | P0 | Automatizado obrigatório | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| REC-006 | Recorder, overlay e checkpoints manuais | Evento bloqueado por política do browser/app | P1 | Automatizado recomendado | Sessão de gravação com overlay/checkpoint/fingerprint | Classifica ID, aplica política e registra evidência/resultado |
| OBS-001 | Execução, evidência e observabilidade | Falha sem screenshot/trace | P0 | Automatizado obrigatório | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| OBS-002 | Execução, evidência e observabilidade | Console error relevante | P1 | Automatizado recomendado | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| OBS-003 | Execução, evidência e observabilidade | Erro de rede relevante | P1 | Automatizado recomendado | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| OBS-004 | Execução, evidência e observabilidade | Healing aplicado sem rastreabilidade | P0 | Automatizado obrigatório | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| OBS-005 | Execução, evidência e observabilidade | Rejeição repetida do mesmo patch | P0 | Automatizado obrigatório | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| OBS-006 | Execução, evidência e observabilidade | Flakiness não determinística | P0 | Automatizado obrigatório | Execução com erro controlado e evidências esperadas | Classifica ID, aplica política e registra evidência/resultado |
| LIM-001 | Limites técnicos e casos não automatizáveis com segurança | CAPTCHA/desafio humano | P0 | Automatizado obrigatório | Cenário de limite técnico/segurança com checkpoint manual | Classifica ID, aplica política e registra evidência/resultado |
| LIM-002 | Limites técnicos e casos não automatizáveis com segurança | Cross-origin inacessível | P0 | Automatizado obrigatório | Cenário de limite técnico/segurança com checkpoint manual | Classifica ID, aplica política e registra evidência/resultado |
| LIM-003 | Limites técnicos e casos não automatizáveis com segurança | Dado sensível mascarado | P0 | Automatizado obrigatório | Cenário de limite técnico/segurança com checkpoint manual | Classifica ID, aplica política e registra evidência/resultado |
| LIM-004 | Limites técnicos e casos não automatizáveis com segurança | Operação irreversível | P0 | Automatizado obrigatório | Cenário de limite técnico/segurança com checkpoint manual | Classifica ID, aplica política e registra evidência/resultado |
| LIM-005 | Limites técnicos e casos não automatizáveis com segurança | Dependência externa instável | P2 | Especializado/manual assistido | Cenário de limite técnico/segurança com checkpoint manual | Classifica ID, aplica política e registra evidência/resultado |
