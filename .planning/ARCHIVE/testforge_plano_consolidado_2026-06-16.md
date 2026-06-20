# TestForge — Plano Consolidado de Implementação

**Data:** 16/06/2026  
**Escopo:** consolidar o que foi planejado hoje para o projeto TestForge, exceto MCP RTC/RQM/RDNG e MCP mestre, que pertencem a outro projeto.  
**Decisão de pipeline:** SpecKit foi removido da pipeline do TestForge neste momento; portanto, não há tarefas de implementação relacionadas a SpecKit neste plano.

---

## 1. Decisões consolidadas

1. A arquitetura complexa será mantida como **mapa estratégico**, para orientar evolução, governança técnica e visão de longo prazo.
2. A arquitetura enxuta será adotada como **caminho de execução**, priorizando entregas pequenas, testáveis e incrementalmente úteis.
3. O TestForge deve estabilizar primeiro o fluxo essencial: **gravar → normalizar → enriquecer semanticamente → gerar script Playwright → executar → coletar evidências → avaliar healing/promoção**.
4. A lista antiga de bugs não será migrada literalmente. Ela será convertida em uma **suíte de regressão por famílias de falha**, com páginas de teste locais, testes automatizados e critérios claros de validação.
5. O MVP deve evitar complexidade prematura: nada de MCP RTC/RQM/RDNG, nada de MCP mestre e nada de SpecKit na pipeline neste momento.
6. Dados sensíveis nas evidências devem inicialmente gerar **alerta**, não mascaramento automático.

---

## 2. Ordem recomendada de implementação

### Fase 0 — Preparação do repositório e linha de base

Objetivo: deixar o projeto executável e mensurável antes de mexer em funcionalidades.

Entregas:
- Repositório limpo e executável em ambiente local.
- Comandos documentados para instalar, rodar CLI, executar testes e gerar gravações.
- Estrutura de pastas estabilizada para `recordings/`, `semantic_tests/`, `bug_lab/`, `tests/` e `docs/`.
- Script de consolidação de arquivos das pastas `recordings` e `semantic_tests` em documento único, quando necessário para análise por LLM.

Critérios de aceite:
- `pip install -e .` funciona.
- `python -m testforge.cli.app --help` funciona.
- A suíte mínima de testes executa sem erro estrutural.
- Existe README curto com comandos básicos.

---

### Fase 1 — Bug Lab / Ambiente de regressão reprodutível

Objetivo: criar páginas locais e testes que reproduzam os bugs relevantes antes de alterar a implementação.

Entregas:
- Pasta `bug_lab/pages/` com uma página por família de bug.
- Pasta `bug_lab/tests/` com testes Playwright/pytest para cada cenário.
- README por bug contendo sintoma, causa provável, comando de reprodução, comando de validação e critério de encerramento.
- Fixtures para upload de arquivo.

Famílias iniciais de bug:
1. Seletores vazios ou inválidos.
2. Seletores frágeis e pouco semânticos.
3. Falta de assertions intermediárias e oráculos pós-ação.
4. Duplicidade de passos e cliques desnecessários.
5. Perda/inconsistência entre gravação bruta e teste semântico.
6. Upload de arquivos com múltiplos inputs.
7. Finalização de gravação quando há prompt de arquivo pendente.
8. Select/options jQuery não capturados corretamente.
9. Texto com aspas/BADSTRING em seletores CSS/has-text.
10. Botões com `mat-icon` contaminando o accessible name.
11. Datepicker sem validação adequada.
12. Encoding inconsistente.
13. Uso excessivo de `try/except` sem logging útil.
14. Permissões do navegador e falhas operacionais de execução.

Critérios de aceite:
- Cada bug/família tem página mínima determinística.
- Cada bug/família tem teste que falha antes da correção, quando aplicável.
- Cada bug/família tem evidência automática: saída pytest, screenshot, log, gravação ou script gerado.
- O Bug Lab roda localmente sem depender de sistemas internos.

---

### Fase 2 — Gravador estável e rastreável

Objetivo: estabilizar a entrada do pipeline: a gravação bruta.

Entregas:
- Gravador Playwright com CLI clara.
- Salvamento confiável da gravação mesmo em encerramento controlado.
- Tratamento robusto de upload de arquivos.
- Diferenciação de múltiplos inputs `type=file` na mesma página.
- Captura de eventos relevantes sem cliques redundantes.
- Registro de metadados: URL inicial, timestamp, nome da gravação, browser, flags usadas e eventos capturados.

Histórias:

#### História 2.1 — Iniciar gravação via CLI
Como QA/desenvolvedor, quero iniciar uma gravação informando nome e URL, para capturar uma jornada manual reproduzível.

Critérios de aceite:
- O comando aceita nome, URL, modo headed/debug e ignore-ssl.
- A gravação cria arquivo em `recordings/`.
- A URL inicial nunca pode ser vazia.

#### História 2.2 — Finalizar gravação de forma segura
Como usuário do TestForge, quero finalizar a gravação mesmo quando houver interação pendente, para não perder o trabalho já gravado.

Critérios de aceite:
- Atalho de finalização salva estado parcial válido.
- Fechamento do navegador não perde gravação já capturada.
- Logs indicam se a gravação foi completa, parcial ou interrompida.

#### História 2.3 — Tratar upload de arquivos
Como QA, quero que uploads sejam gravados como `set_input_files`, para que o script gerado execute sem abrir janela nativa de upload.

Critérios de aceite:
- Não gerar `fill("C:\\fakepath\\...")` como ação principal de upload.
- Usar fixtures locais para arquivos de teste.
- Remover cliques redundantes que abrem seletor nativo durante replay.

#### História 2.4 — Diferenciar múltiplos inputs de arquivo
Como QA, quero que inputs de arquivo diferentes recebam seletores distintos, para gravar páginas com vários anexos.

Critérios de aceite:
- O candidato de locator diferencia posição, label associado, container, aria-label ou contexto próximo.
- O script gerado não usa sempre `input[type="file"]` genérico quando há múltiplos inputs.

---

### Fase 3 — Modelo intermediário semântico

Objetivo: transformar a gravação bruta em uma representação semântica estável, auditável e adequada para geração de código.

Entregas:
- `SemanticTestCase` com preconditions, steps, assertions, metadata e evidências.
- Normalizador entre eventos brutos e passos semânticos.
- Regras para deduplicar ações inúteis.
- Preservação da rastreabilidade entre evento bruto, step semântico e linha do script final.

Histórias:

#### História 3.1 — Normalizar eventos brutos
Como desenvolvedor, quero converter eventos brutos em passos semânticos, para gerar testes mais estáveis.

Critérios de aceite:
- Cada step semântico referencia o evento bruto de origem.
- Eventos redundantes são marcados ou removidos com justificativa.
- `initial_url` é obrigatório.

#### História 3.2 — Remover ações redundantes
Como QA, quero eliminar cliques e fills desnecessários, para reduzir falso erro durante replay.

Critérios de aceite:
- Cliques anteriores ao `set_input_files` que apenas abrem janela nativa são removidos.
- Duplicidades consecutivas são detectadas.
- O normalizador registra motivo da remoção.

#### História 3.3 — Preservar assertions e hints
Como QA, quero que hints de validação virem assertions intermediárias, para aumentar a confiabilidade do teste.

Critérios de aceite:
- Hints são convertidos em `expect()` quando possível.
- Quando não for possível, o step fica marcado como pendente de curadoria.

---

### Fase 4 — Geração e ranking de locators

Objetivo: criar candidatos de seletores automaticamente, pontuar robustez e escolher locators confiáveis com fallback determinístico.

Camadas recomendadas de seletores:
1. `data-testid`/atributos estáveis explícitos.
2. `get_by_role(role, name=...)` com accessible name limpo.
3. `get_by_label`, `get_by_placeholder`, `get_by_text` quando fizer sentido.
4. ID estável.
5. CSS contextual curto.
6. XPath/domPath apenas como último recurso.

Penalidades comuns:
- Seletor vazio.
- CSS genérico demais.
- XPath absoluto.
- Texto longo, truncado ou com aspas sem escape.
- Accessible name contaminado por ícones.
- Índices frágeis (`nth`) sem contexto.
- Locator não único.
- Locator que não está visível, habilitado ou acionável.

Histórias:

#### História 4.1 — Gerar candidatos estruturados
Como desenvolvedor, quero gerar candidatos de locator com dados estruturados, para evitar parsing frágil de string.

Critérios de aceite:
- Candidato contém `strategy`, `value`, `playwright_expr`, `score` e `reason`.
- Estratégia `role` preserva role e name separadamente.
- `playwright_expr` pode ser usado diretamente pelo compilador.

#### História 4.2 — Calcular score de locator
Como TestForge, quero pontuar locators, para escolher o mais robusto.

Critérios de aceite:
- Score considera unicidade, actionability, estabilidade, semântica e penalidades.
- Locators vazios recebem score zero e são rejeitados.
- O motivo da pontuação é persistido.

#### História 4.3 — Validar uniqueness e actionability
Como QA, quero validar que o locator aponta para um único elemento acionável, para evitar testes instáveis.

Critérios de aceite:
- `count() == 1` para locator principal, salvo exceções justificadas.
- Elemento precisa estar visível, habilitado e pronto para ação.
- Falhas de actionability entram na taxonomia.

#### História 4.4 — Limpar accessible name com mat-icon
Como QA, quero remover ruído de ícones do nome acessível, para que botões Angular Material sejam gravados corretamente.

Critérios de aceite:
- `file_upload Carregar` vira `Carregar` quando `file_upload` vier de ícone.
- A limpeza é testada no Bug Lab.

#### História 4.5 — Escapar textos usados em seletores
Como desenvolvedor, quero escapar strings usadas em seletores, para evitar erros como BADSTRING.

Critérios de aceite:
- Textos com aspas, acentos e caracteres especiais são tratados.
- Quando o texto for inseguro para CSS, usar API Playwright mais adequada.

---

### Fase 5 — Compilador Playwright Python

Objetivo: gerar scripts executáveis, legíveis e rastreáveis a partir do modelo semântico.

Histórias:

#### História 5.1 — Corrigir geração de comandos Playwright
Como QA, quero que cada step gere código Playwright válido, para executar o teste sem ajuste manual.

Critérios de aceite:
- `fill` e `click` usam `playwright_expr` do locator selecionado.
- Não há comandos soltos como `.fill(...)` sem objeto locator.
- O script gerado passa em validação sintática.

#### História 5.2 — Validar URL inicial antes de gerar script
Como TestForge, quero impedir `page.goto('')`, para evitar falhas falsas no início do teste.

Critérios de aceite:
- `initial_url` ausente gera erro claro antes da compilação.
- O erro aponta para a gravação/semantic test problemático.

#### História 5.3 — Gerar asserts intermediários
Como QA, quero que o script contenha validações após ações importantes, para detectar falso healing.

Critérios de aceite:
- Assertions derivadas de hints são emitidas como `expect()`.
- Assertions têm comentário/rastreabilidade para o step semântico.

---

### Fase 6 — Runner, fallback determinístico e self-healing controlado

Objetivo: executar scripts com fallback determinístico e registrar quando houve tentativa de healing.

Histórias:

#### História 6.1 — Executar fallback sem parsing frágil
Como desenvolvedor, quero que o runner use candidatos estruturados, para evitar falhas internas no fallback.

Critérios de aceite:
- Runner não depende de split frágil de strings como `button[name='Salvar']`.
- O fallback tenta candidatos ordenados por score.
- Cada tentativa registra sucesso, falha e razão.

#### História 6.2 — Implementar shadow mode
Como time do TestForge, quero rodar healing em modo observação, para medir precisão sem alterar resultado automaticamente.

Critérios de aceite:
- O sistema registra o que teria sido curado.
- O teste original continua sendo a referência.
- Métricas separam verdadeiro positivo, falso healing e falso negativo.

#### História 6.3 — Criar oráculo pós-ação
Como QA, quero validar se a ação curada produziu o efeito esperado, para evitar falso healing.

Critérios de aceite:
- Após ação, verificar mudança esperada de DOM, URL, texto, estado, rede ou assertion.
- Ausência de evidência pós-ação impede promoção automática.

---

### Fase 7 — EvidenceCollector e SQLite

Objetivo: registrar evidências técnicas suficientes para auditoria, depuração e promoção de locators/healing.

Histórias:

#### História 7.1 — Coletar evidências de execução
Como QA, quero screenshots, logs e dados estruturados, para revisar falhas e decisões de healing.

Critérios de aceite:
- Cada execução gera registro no SQLite.
- Evidências incluem step, locator, candidato, score, resultado e artefatos.
- Dados sensíveis geram alerta, não mascaramento automático neste momento.

#### História 7.2 — Persistir histórico de sucesso de locators
Como TestForge, quero lembrar quais locators funcionaram, para melhorar ranking futuro.

Critérios de aceite:
- Histórico por aplicação/página/elemento é persistido.
- Sucessos aumentam confiança futura.
- Falhas reduzem confiança ou geram alerta de instabilidade.

#### História 7.3 — Criar consultas operacionais
Como time, quero listar casos pendentes de revisão, para fazer curadoria dos healings.

Critérios de aceite:
- Query lista healings pendentes.
- Query lista falsos healings.
- Query lista locators instáveis.

---

### Fase 8 — Promotion Gate

Objetivo: promover automaticamente apenas correções de locator/healing com evidência suficiente.

Histórias:

#### História 8.1 — Definir critérios de promoção
Como time, quero critérios objetivos para promover healing, para evitar instabilidade.

Critérios de aceite:
- Promoção exige sucesso repetido, unicidade, actionability e oráculo pós-ação positivo.
- Casos duvidosos ficam pendentes de revisão.
- Cada decisão registra justificativa.

#### História 8.2 — Revisar evidências antes da promoção
Como curador, quero revisar casos pendentes, para aprovar ou rejeitar healings.

Critérios de aceite:
- Existe lista de pendências.
- Aprovação/rejeição altera status no SQLite.
- Histórico da decisão é mantido.

---

### Fase 9 — Taxonomia de falhas e métricas

Objetivo: classificar falhas de forma consistente e medir se o TestForge está melhorando.

Famílias de falhas:
- Locator vazio/inválido.
- Locator frágil.
- Locator não único.
- Elemento não acionável.
- Timing/espera insuficiente.
- Estado inicial inválido.
- Navegação inesperada.
- Upload/arquivo.
- Select/combobox/date picker.
- Texto/encoding/escape.
- Assertion ausente/fraca.
- Falso healing.
- Erro interno do TestForge.

Histórias:

#### História 9.1 — Classificar falhas automaticamente
Como TestForge, quero atribuir família de falha a cada erro, para orientar correção e métricas.

Critérios de aceite:
- Falhas conhecidas são classificadas.
- Falhas desconhecidas entram como `unknown` com evidência.
- A classificação aparece nos relatórios.

#### História 9.2 — Corrigir métricas do EvidenceStore
Como time, quero métricas confiáveis por aplicação, para avaliar progresso.

Critérios de aceite:
- Filtros SQL por aplicação funcionam.
- Métricas de reviewed, false_heals e true_positives são consistentes.
- Testes cobrem cenários com e sem filtro.

---

### Fase 10 — Documentação enxuta e governança sem SpecKit

Objetivo: atualizar a documentação para refletir a arquitetura enxuta como execução e a complexa como visão estratégica, sem incluir SpecKit na pipeline.

Entregas:
- `docs/visao.md`
- `docs/arquitetura-enxuta.md`
- `docs/mapa-estrategico.md`
- `docs/fluxo-pipeline.md`
- `docs/bug-lab.md`
- `docs/promotion-gate.md`
- `docs/taxonomia-falhas.md`
- `docs/decisoes/ADR-0001-arquitetura-enxuta-como-execucao.md`
- `docs/decisoes/ADR-0002-speckit-fora-da-pipeline-neste-momento.md`

Critérios de aceite:
- A documentação não instrui uso de SpecKit no fluxo atual.
- A documentação deixa claro o que pertence e o que não pertence ao TestForge.
- A ordem de implementação está explícita.

---

## 3. Backlog consolidado por épicos

### Épico 1 — Fundação e linha de base executável
Objetivo: garantir que o projeto rode e tenha estrutura mínima de desenvolvimento.

Histórias:
- H1.1 Configurar ambiente local e comandos básicos.
- H1.2 Organizar estrutura de pastas do projeto.
- H1.3 Criar README operacional.
- H1.4 Criar script de consolidação de artefatos para análise por LLM.

### Épico 2 — Bug Lab e regressão por famílias de falha
Objetivo: transformar bugs atuais/históricos em cenários reprodutíveis.

Histórias:
- H2.1 Criar estrutura `bug_lab/`.
- H2.2 Criar template de página de bug.
- H2.3 Criar template de teste de bug.
- H2.4 Implementar cenários de upload.
- H2.5 Implementar cenários de select/jQuery.
- H2.6 Implementar cenários de mat-icon.
- H2.7 Implementar cenários de BADSTRING/texto com escape.
- H2.8 Implementar cenários de selector vazio/frágil.

### Épico 3 — Gravador
Objetivo: capturar jornadas manuais com confiabilidade.

Histórias:
- H3.1 Iniciar gravação via CLI.
- H3.2 Salvar gravação bruta com metadados.
- H3.3 Finalizar gravação com segurança.
- H3.4 Tratar upload de arquivos.
- H3.5 Diferenciar múltiplos file inputs.
- H3.6 Evitar eventos redundantes.

### Épico 4 — Modelo semântico
Objetivo: converter eventos brutos em teste semântico.

Histórias:
- H4.1 Criar/estabilizar `SemanticTestCase`.
- H4.2 Normalizar eventos.
- H4.3 Deduplicar ações.
- H4.4 Preservar rastreabilidade.
- H4.5 Criar assertions intermediárias.

### Épico 5 — Locator Engine
Objetivo: gerar, pontuar e validar locators robustos.

Histórias:
- H5.1 Gerar candidatos por múltiplas estratégias.
- H5.2 Pontuar locators.
- H5.3 Validar uniqueness.
- H5.4 Validar actionability.
- H5.5 Penalizar seletores frágeis.
- H5.6 Corrigir mat-icon/acessible name.
- H5.7 Tratar BADSTRING/escape.

### Épico 6 — Compilador Playwright
Objetivo: gerar scripts executáveis e rastreáveis.

Histórias:
- H6.1 Usar `playwright_expr` no compilador.
- H6.2 Validar `initial_url`.
- H6.3 Emitir ações `click`, `fill`, `select_option`, `set_input_files` corretamente.
- H6.4 Emitir assertions.
- H6.5 Validar sintaxe do script gerado.

### Épico 7 — Runner e fallback determinístico
Objetivo: executar scripts com fallback controlado e observável.

Histórias:
- H7.1 Ordenar candidatos por score.
- H7.2 Remover parsing frágil de locator.
- H7.3 Executar fallback determinístico.
- H7.4 Registrar tentativa de fallback.
- H7.5 Rodar em shadow mode.

### Épico 8 — EvidenceCollector e persistência
Objetivo: coletar evidências auditáveis e métricas úteis.

Histórias:
- H8.1 Criar schema SQLite.
- H8.2 Registrar execução por step.
- H8.3 Salvar screenshots/logs/artefatos.
- H8.4 Alertar presença de dados sensíveis.
- H8.5 Persistir histórico de locators.
- H8.6 Criar queries operacionais.

### Épico 9 — Promotion Gate
Objetivo: decidir quando um healing pode ser promovido.

Histórias:
- H9.1 Definir critérios de promoção.
- H9.2 Implementar status de revisão.
- H9.3 Criar lista de pendências.
- H9.4 Aprovar/rejeitar healing.
- H9.5 Registrar decisão e justificativa.

### Épico 10 — Taxonomia, métricas e documentação
Objetivo: classificar falhas, medir evolução e documentar o plano.

Histórias:
- H10.1 Criar taxonomia operacional.
- H10.2 Classificar falhas automaticamente.
- H10.3 Corrigir métricas do EvidenceStore.
- H10.4 Documentar arquitetura enxuta.
- H10.5 Documentar mapa estratégico.
- H10.6 Criar ADRs sem SpecKit na pipeline.

---

## 4. Prompt Pack para LLM

### Prompt 0 — Regras globais do projeto

```text
Você é uma LLM desenvolvedora atuando no projeto TestForge.

Contexto:
- O TestForge grava interações web e gera scripts Playwright Python.
- A arquitetura complexa é o mapa estratégico.
- A arquitetura enxuta é o caminho de execução.
- SpecKit não faz parte da pipeline neste momento.
- MCP RTC/RQM/RDNG e MCP mestre pertencem a outro projeto e não devem ser implementados aqui.
- O foco é entregar valor incremental, testável e com evidências.

Regras:
1. Não crie dependências desnecessárias.
2. Não implemente MCP.
3. Não implemente integração com RTC/RQM/RDNG.
4. Não adicione SpecKit à pipeline.
5. Sempre crie ou atualize testes automatizados.
6. Sempre registre evidências de execução quando a funcionalidade envolver gravação, geração, runner, healing ou promotion gate.
7. Dados sensíveis devem gerar alerta, não mascaramento automático neste momento.
8. Prefira solução simples e determinística antes de IA/LLM.
9. Toda mudança deve preservar rastreabilidade entre gravação bruta, modelo semântico, script gerado e evidência.
```

### Prompt 1 — Fundação do projeto

```text
Implemente a fundação executável do TestForge.

Tarefas:
1. Verifique a estrutura atual do projeto.
2. Garanta que `pip install -e .` funcione.
3. Garanta que `python -m testforge.cli.app --help` funcione.
4. Crie ou atualize README com comandos básicos.
5. Organize pastas: recordings/, semantic_tests/, bug_lab/, tests/, docs/.
6. Adicione teste mínimo de sanidade.

Critérios de aceite:
- Ambiente instala sem erro.
- CLI responde.
- Testes mínimos passam.
- README contém comandos de instalação, gravação, execução e teste.
```

### Prompt 2 — Bug Lab base

```text
Crie a estrutura base do Bug Lab do TestForge.

Tarefas:
1. Criar `bug_lab/pages/`, `bug_lab/tests/`, `bug_lab/fixtures/`.
2. Criar README principal do Bug Lab.
3. Criar template de página de bug.
4. Criar template de teste pytest/Playwright.
5. Criar fixtures simples para upload.

Critérios de aceite:
- É possível adicionar um bug novo seguindo o template.
- O README explica o ciclo: reproduzir, verificar, corrigir, validar novamente.
- Existe pelo menos um teste demonstrativo rodando contra página local.
```

### Prompt 3 — Criar página de teste para cada bug

```text
Você receberá a descrição de um bug do TestForge.

Para esse bug, crie:
1. `bug_lab/pages/bug_xxx_nome_curto/index.html`
2. `bug_lab/pages/bug_xxx_nome_curto/README.md`
3. `bug_lab/tests/test_bug_xxx_nome_curto.py`

A página deve reproduzir o comportamento mínimo do bug.
O teste deve verificar se o bug ainda acontece.
Se a correção já existir, o teste deve passar.
Se a correção não existir, o teste deve falhar de forma clara.

Não use sistemas internos reais.
Não use frameworks externos salvo necessidade justificada.
Prefira HTML/JS puro e comportamento determinístico.
```

### Prompt 4 — Gravador estável

```text
Estabilize o gravador do TestForge.

Tarefas:
1. Garantir CLI para iniciar gravação com nome e URL.
2. Salvar arquivo bruto em `recordings/`.
3. Registrar metadados obrigatórios.
4. Tratar finalização segura.
5. Tratar upload de arquivos com `set_input_files`.
6. Evitar cliques redundantes associados ao upload.
7. Diferenciar múltiplos inputs type=file.

Critérios de aceite:
- Uma gravação simples gera arquivo válido.
- Fechar/finalizar gravação não perde dados já capturados.
- Upload é representado de forma executável.
- Há testes automatizados cobrindo os cenários do Bug Lab.
```

### Prompt 5 — Modelo semântico

```text
Implemente ou estabilize o modelo intermediário semântico do TestForge.

Tarefas:
1. Definir `SemanticTestCase` com preconditions, steps, assertions e metadata.
2. Converter gravação bruta em steps semânticos.
3. Exigir `initial_url`.
4. Deduplicar ações redundantes.
5. Preservar rastreabilidade com eventos brutos.
6. Converter hints de validação em assertions quando possível.

Critérios de aceite:
- Todo step semântico tem origem rastreável.
- Não há teste semântico com URL inicial vazia.
- Ações redundantes são removidas ou justificadas.
- Assertions intermediárias são preservadas.
```

### Prompt 6 — Locator Engine

```text
Implemente a engine de locators do TestForge.

Tarefas:
1. Gerar candidatos por data-testid, role/name, label, placeholder, texto, id, CSS contextual e fallback.
2. Criar estrutura `LocatorCandidate` com dados estruturados.
3. Calcular score de robustez.
4. Validar uniqueness.
5. Validar actionability.
6. Penalizar seletores frágeis.
7. Corrigir accessible name contaminado por mat-icon.
8. Tratar textos com aspas/caracteres especiais sem gerar BADSTRING.

Critérios de aceite:
- Locator vazio é rejeitado.
- Candidato principal e fallback são gerados.
- Score e reason são persistidos.
- Testes cobrem mat-icon, BADSTRING, múltiplos file inputs e seletores frágeis.
```

### Prompt 7 — Compilador Playwright

```text
Corrija e estabilize o compilador Playwright Python do TestForge.

Tarefas:
1. Usar `playwright_expr` do locator selecionado para gerar comandos.
2. Nunca gerar `.fill()` ou `.click()` sem locator.
3. Validar `initial_url` antes de `page.goto`.
4. Gerar `set_input_files` para upload.
5. Gerar `select_option` quando aplicável.
6. Gerar assertions intermediárias.
7. Validar sintaxe do Python gerado.

Critérios de aceite:
- Script gerado é sintaticamente válido.
- Script executa contra páginas do Bug Lab.
- Não há `page.goto('')`.
- Não há seletores vazios.
```

### Prompt 8 — Runner, fallback e shadow mode

```text
Implemente o runner com fallback determinístico e shadow mode.

Tarefas:
1. Executar candidatos em ordem de score.
2. Remover parsing textual frágil de locators.
3. Registrar cada tentativa de fallback.
4. Implementar shadow mode sem alterar automaticamente o resultado final.
5. Criar oráculo pós-ação para validar healing.

Critérios de aceite:
- Fallback usa dados estruturados.
- Toda tentativa gera evidência.
- Shadow mode informa o que teria sido curado.
- Healing sem oráculo positivo não é promovido.
```

### Prompt 9 — EvidenceCollector

```text
Implemente o EvidenceCollector com persistência SQLite.

Tarefas:
1. Criar schema SQLite para execuções, steps, locators, evidências e decisões.
2. Registrar screenshots, logs e artefatos quando disponíveis.
3. Registrar score, reason, estratégia e resultado do locator.
4. Alertar presença de dados sensíveis, sem mascarar automaticamente.
5. Criar queries para pendências, falsos healings e locators instáveis.

Critérios de aceite:
- Cada execução gera registro consultável.
- Cada step relevante gera evidência.
- Dados sensíveis são sinalizados por alerta.
- Queries operacionais funcionam.
```

### Prompt 10 — Promotion Gate

```text
Implemente o Promotion Gate do TestForge.

Tarefas:
1. Definir critérios objetivos de promoção.
2. Criar status: pending_review, approved, rejected, promoted.
3. Exigir evidência de sucesso repetido, uniqueness, actionability e oráculo pós-ação.
4. Criar fluxo de revisão manual.
5. Registrar justificativa da decisão.

Critérios de aceite:
- Healing duvidoso fica pendente.
- Healing aprovado possui evidências suficientes.
- Rejeições ficam registradas com motivo.
- Métricas distinguem true positive e false healing.
```

### Prompt 11 — Taxonomia e métricas

```text
Implemente a taxonomia de falhas e métricas do TestForge.

Tarefas:
1. Criar enum/catálogo de famílias de falha.
2. Classificar erros conhecidos automaticamente.
3. Registrar falhas unknown com evidência.
4. Corrigir métricas do EvidenceStore.
5. Criar testes para métricas com e sem filtro por aplicação.

Critérios de aceite:
- Toda falha tem categoria.
- Métricas são consistentes.
- SQL por aplicação funciona.
- Relatório mostra evolução de estabilidade.
```

### Prompt 12 — Documentação final sem SpecKit

```text
Atualize a documentação do TestForge.

Tarefas:
1. Criar `docs/visao.md`.
2. Criar `docs/arquitetura-enxuta.md`.
3. Criar `docs/mapa-estrategico.md`.
4. Criar `docs/fluxo-pipeline.md`.
5. Criar `docs/bug-lab.md`.
6. Criar `docs/promotion-gate.md`.
7. Criar `docs/taxonomia-falhas.md`.
8. Criar ADR informando que a arquitetura enxuta é o caminho de execução.
9. Criar ADR informando que SpecKit está fora da pipeline neste momento.

Critérios de aceite:
- A documentação não inclui MCP RTC/RQM/RDNG.
- A documentação não inclui MCP mestre.
- A documentação não instrui uso de SpecKit na pipeline atual.
- A ordem de implementação está clara.
```

---

## 5. Primeiro pacote recomendado para começar

Para dar o próximo passo com maior chance de sucesso, comece nesta ordem curta:

1. Fundação executável.
2. Bug Lab base.
3. Páginas para os bugs P1: seletor vazio, seletor frágil, assertions ausentes, upload, mat-icon e BADSTRING.
4. Gravador estável.
5. Modelo semântico.
6. Locator Engine.
7. Compilador Playwright.
8. Runner/fallback/shadow mode.
9. EvidenceCollector.
10. Promotion Gate.
11. Taxonomia/métricas.
12. Documentação final.

Essa ordem reduz risco porque cria primeiro o laboratório de regressão e só depois muda o motor do TestForge.
