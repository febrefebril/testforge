# Glossário TestForge

> Termos técnicos explicados em linguagem simples para analistas QA.

---

## A

### Assert (Verificação)
Ponto de checagem automático dentro de um teste. O TestForge compara o valor esperado com o valor real encontrado na tela. Exemplo: verificar se o botão "Salvar" está visível, ou se uma mensagem de sucesso aparece após o envio.

---

## B

### Blind Spot (Ponto Cego)
Situação onde o TestForge não consegue identificar automaticamente o que está acontecendo na tela. Pode ser um elemento renderizado de forma incomum, um iframe, ou uma animação que o mecanismo de inferência não reconhece. O QA precisa intervir manualmente nesses pontos.

---

## C

### CDP (Chrome DevTools Protocol)
Protocolo de comunicação com o navegador Chrome. O TestForge usa CDP para se conectar ao navegador, capturar eventos (cliques, digitações, navegações) e injetar o overlay de gravação. É a camada de transporte entre o TestForge e o browser.

### Compiler
Motor que transforma um `SemanticTestCase` (arquivo `.testforge.json`) em um script executável (Playwright ou Selenium). O compilador resolve healing layers, gera seletores robustos e produz o código final que roda no pipeline.

### ComponentHandler
Plugin ou módulo que ensina o TestForge a lidar com um tipo específico de componente UI (ex: dropdown customizado, datepicker, tabela com paginação). Cada ComponentHandler sabe como extrair valores, aplicar asserts e simular interações naquele tipo de componente.

### Curador (Curator)
Modo de operação do TestForge onde um QA humano revisa e refina os `SemanticTestCases` gerados automaticamente. O curador preenche campos faltantes, ajusta asserts, resolve blind spots e decide se o teste está pronto para compilação. É a etapa de garantia de qualidade sobre o teste gerado.

---

## D

### Diagnostic Mode (Modo Diagnóstico)
Modo de execução que gera logs detalhados sobre cada passo do teste. Mostra qual seletor foi usado, se houve healing aplicado, tempos de espera e falhas. Útil para depurar testes que quebram no pipeline mas funcionavam localmente.

---

## F

### Field Value (Valor de Campo)
Dado concreto que o QA associa a um campo do `SemanticTestCase`. Exemplo: no campo "email", o field value pode ser `teste@exemplo.com`. Valores podem ser estáticos (fixos) ou parametrizados (variáveis de ambiente).

### Fingerprint (Impressão Digital)
Assinatura única de um elemento da interface, calculada a partir de múltiplos atributos (texto, posição relativa, atributos DOM, contexto semântico). Usada pelo mecanismo de self-healing para reencontrar elementos mesmo quando atributos superficiais (ID, classe CSS) mudam.

---

## G

### Gravação (Recording)
Processo de capturar a interação do QA com a aplicação web. O TestForge observa cada clique, digitação e navegação, e gera automaticamente um `SemanticTestCase` com passos, asserts sugeridos e metadados. É o ponto de partida do fluxo de criação de testes.

---

## I

### Intent (Intenção)
Descrição de alto nível do que um passo de teste pretende fazer. Em vez de "clicar no botão com id=btn-123", a intent diz "clicar no botão de salvar". Essa abstração permite que o teste sobreviva a mudanças na UI — o self-healing usa a intent para reencontrar o botão mesmo que o ID mude.

---

## L

### L0, L1, L2, L3 (Healing Layers — Camadas de Cura)
Estratégia em quatro níveis para auto-reparo de seletores quebrados:

| Layer | Descrição | Exemplo |
|-------|-----------|---------|
| **L0** | Seletor exato ensinado pelo QA | `#save-button` |
| **L1** | Fingerprint do elemento | Hash dos atributos + posição |
| **L2** | Intent semântica + busca no DOM | "botão com texto Salvar" |
| **L3** | Fallback por similaridade visual/heurística | Elemento mais próximo da posição original |

O motor tenta L0 primeiro. Se falhar, escala para L1, depois L2, depois L3. Cada camada é mais cara computacionalmente, porém mais resiliente.

### Locator
Referência técnica que identifica um elemento na página. Pode ser um seletor CSS, XPath, ou um descritor semântico. Diferente do Selector, o Locator é a representação interna que o Compiler usa para gerar código.

---

## M

### MIS (Mecanismo de Inferência Semântica)
Cérebro do TestForge. Analisa o DOM da página, os eventos capturados e o contexto para inferir a intenção por trás de cada ação do QA. O MIS decide automaticamente o que é um clique, um preenchimento, uma navegação, e sugere onde colocar asserts. É o que elimina a necessidade de o QA escrever código.

---

## N

### Normalizer
Componente que padroniza os dados brutos capturados durante a gravação. Converte eventos de baixo nível do CDP em uma estrutura limpa e consistente que o MIS consegue processar. Remove ruído, agrupa eventos relacionados e resolve ambiguidades de timing.

---

## O

### Overlay
Camada visual semi-transparente que aparece sobre a aplicação durante a gravação. Mostra ao QA quais elementos estão sendo capturados, permite adicionar asserts com um clique, e indica o status da gravação (gravando, pausado). É a interface entre o QA e o motor de gravação.

---

## P

### PII (Personal Identifiable Information)
Dados pessoais identificáveis: CPF, e-mail, telefone, nome completo, endereço. O TestForge detecta automaticamente quando um field value contém PII e emite um alerta no relatório de completude. O alerta não bloqueia a publicação, mas exige que o QA confirme estar ciente.

### Pipeline
Fluxo automatizado que executa testes em série. No contexto do TestForge: `gravação → curadoria → compilação → execução → relatório`. Pode ser integrado a CI/CD (GitHub Actions, Jenkins, GitLab CI).

### Pilot Mode (Modo Piloto)
Modo de gravação assistida onde o TestForge sugere proativamente asserts e intents enquanto o QA interage com a aplicação. Balões de dica aparecem no overlay perguntando "quer verificar este campo?" ou "isto é um submit?". Ideal para QAs iniciantes ou fluxos complexos.

---

## R

### Readiness Gate
Verificação automática que avalia se um `SemanticTestCase` está pronto para compilação. O gate checa: todos os campos obrigatórios preenchidos? Blind spots resolvidos? PII sinalizado? O resultado é `READY` (pode compilar), `REVIEW` (precisa de curadoria) ou `FAIL` (problemas bloqueantes).

---

## S

### Selector
Estratégia que o TestForge usa para localizar um elemento na página. Pode ser um seletor CSS, um XPath, um seletor por texto, ou um seletor semântico. O motor de healing gerencia múltiplos seletores alternativos para cada elemento.

### Self-healing (Auto-cura)
Capacidade do TestForge de reparar automaticamente um teste quebrado por mudanças na UI. Se um botão mudou de ID ou posição, o motor de healing tenta reencontrá-lo usando fingerprints (L1), intents (L2) ou heurísticas (L3). O QA é notificado sobre o reparo aplicado.

### SemanticTestCase
Formato de arquivo (`.testforge.json`) que representa um caso de teste de forma declarativa, sem código. Contém: passos com intents, asserts com condiciones, field values, fingerprints, e metadados de healing. É o artefato central do TestForge — gerado pela gravação, refinado pelo curador, consumido pelo compilador.

### semantic_steps.jsonl
Arquivo de log bruto gerado durante a gravação. Contém uma linha JSON por evento capturado (navegação, clique, digitação, scroll). É a matéria-prima que o Normalizer e o MIS processam para produzir o `SemanticTestCase`. Útil para debug de problemas de gravação.

---

## Ver também

- [Guia do Usuário](../USER-GUIDE/)
- [Workflow do QA](../TUTORIAIS/qa-workflow.md)
- [Arquitetura](../ARQUITETURA/)
