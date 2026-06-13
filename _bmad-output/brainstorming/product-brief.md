# Product Brief: TestForge

## Resumo Executivo

TestForge e uma ferramenta que grava a intencao do teste direto em paginas web e transforma essa intencao em scripts de teste que rodam ate o fim. Quando um teste quebra — porque um botao mudou de lugar, um ID foi regenerado, um overlay bloqueou o clique — o TestForge se auto-conserta deterministicamente, sem depender de LLM como motor primario de healing.

Quatro tentativas anteriores falharam. Nao por falta de ideias — o conhecimento ancestral tem 60+ artefatos de planejamento, 30 sessoes de teste reais, taxonomias de falha, formulas de scoring com 4 decimais. Falharam porque a equipe construiu a catedral da governanca antes de firmar o alicerce: o recorder. O codigo que funcionava foi descartado. A especificacao substituiu a execucao.

Desta vez e diferente. Temos o recorder funcional. Temos as licoes. Temos a pipeline BMAD→GSD→GIT. Vamos construir o que funciona, validar cedo, iterar rapido.

## O Problema

**Quem sofre:** QAs e desenvolvedores que mantem suites de testes end-to-end em aplicacoes enterprise — sistemas CAIXA com PrimeFaces, Angular, JSF, jQuery UI, Kendo UI.

**A dor real:** Testes E2E quebram constantemente por fragilidade de seletores. Um `#form:j_idt_173:button` gerado pelo JSF muda a cada deploy. O QA perde horas "consertando" testes que nao deveriam quebrar — o comportamento do sistema nao mudou, so o seletor.

**Como lidam hoje:** Atualizam seletores manualmente. Re-gravam testes do zero. Abandonam suites inteiras quando a manutencao fica insustentavel. O custo e silencioso mas real: pipelines lentos, confianca baixa nos testes, regressoes escapam para producao.

**O custo do status quo:** Cada hora gasta consertando seletor e uma hora nao gasta testando funcionalidade nova. A suite de testes vira passivo, nao ativo.

## A Solucao

TestForge grava a **intencao** do teste, nao os seletores. Quando o QA clica em "Salvar", o recorder captura: o papel do elemento (`role=button`), o nome acessivel ("Salvar"), o texto visivel, o contexto (formulario "Cadastro de Cliente"), atributos estaveis. Isso vira um contrato semantico.

Na execucao, o runner tenta o seletor principal. Se falhar, o motor deterministico extrai a pagina atual, gera candidatos ordenados por score (semantico, unicidade, estabilidade), e tenta do mais provavel ao fallback. Se nada funcionar, sobe para o curador LLM — que recebe um pacote de evidencias estruturado, nao um prompt generico.

**O que torna isso diferente das 4 tentativas anteriores:**

1. **Recorder funcional no centro.** Nao vamos redesenhá-lo. O `projeto-anterior/demo/` tem 30 sessoes de teste reais com PrimeFaces, Angular, jQuery UI, Kendo UI. Vamos estende-lo, nao substitui-lo.

2. **Vertical slice primeiro.** Primeiro slice: recorder → script Playwright → runner → healing deterministico basico. So depois: shadow mode, oracle, promotion gate.

3. **MIS como camada fina.** O Modelo Intermediario Semantico captura: acao, alvo semantico, candidatos, contexto. Nao e um mega-schema — e o minimo necessario para o healing funcionar.

4. **LLM como curador, nao motor.** O LLM so entra quando o deterministico falha. E recebe evidencias estruturadas, nao prompts abertos.

## O Que Nos Torna Diferentes

Nao existe ferramenta equivalente no mercado que combine gravacao de intencao + self-healing deterministico para aplicacoes enterprise legadas (JSF, PrimeFaces). Ferramentas como Playwright, Cypress, Selenium gravam seletores — nao intencao. Ferramentas de "self-healing" comerciais usam heurísticas simples ou dependem de contratos de API. Nenhuma resolve o problema de aplicacoes que geram seletores dinamicos no servidor.

Nosso diferencial nao e a ideia — a ideia ja existia nas 4 tentativas. Nosso diferencial e a **execucao**: comecar pelo que funciona, validar com usuarios reais, iterar. As 4 tentativas anteriores nos deram o mapa do que NAO fazer.

## Quem Servimos

**QA Engineers** em equipes enterprise que mantem suites de testes E2E. Trabalham com aplicacoes legadas onde seletores mudam a cada deploy. Precisam de testes que sobrevivam a refatoracoes de UI sem manutencao constante.

**Desenvolvedores** que escrevem testes para seus proprios componentes mas nao querem mante-los. Querem gravar uma vez e rodar sempre.

**Secundario:** Tech leads e arquitetos que precisam de confianca na suite de testes para liberar deploys com seguranca.

## Criterios de Sucesso

1. **Gravacao funcional:** QA grava um fluxo em aplicacao PrimeFaces/Angular real e obtem um script Playwright executavel.
2. **Healing deterministico:** O script sobrevive a uma mudanca de seletor (ex: ID regenerado) sem intervencao manual.
3. **Taxa de falso healing < 5%:** O sistema nao "cura" testes que nao deveriam passar.
4. **Tempo de healing < 2s:** O processo de re-localizacao do elemento nao pode ser mais lento que a execucao manual.
5. **Sem dependencia de LLM no caminho critico:** O LLM so e acionado quando o deterministico esgota todas as opcoes.

## Escopo

### MVP (primeira versao)
- Recorder via extensao Chrome com overlay injection
- Suporte a PrimeFaces, Angular (detecao automatica de framework)
- Geracao de script Playwright Python a partir da gravacao
- Healing deterministico: fallback por score de candidatos
- 1 oracle: visual/DOM comparison
- Relatorio simples: passo, status, healing aplicado

### Fora do MVP
- Shadow mode com revisao humana
- Promotion Gate com estados (experimental → trusted)
- Multiplos oracles por acao
- Curador LLM integrado
- Taxonomia de falhas completa (React, Angular, etc)
- Dashboard/metricas
- Synthetic lab com mutacoes controladas

## Visao

Se o TestForge funcionar, ele se torna a ferramenta padrao para qualquer equipe que mantenha testes E2E em aplicacoes enterprise. O recorder vira uma extensao de browser que qualquer QA instala em 30 segundos. O healing deterministico vira uma biblioteca Python que qualquer pipeline de CI consome. A taxonomia de falhas vira um conhecimento coletivo — cada falha resolvida ensina o sistema a resolver a proxima.

Em 2 anos: TestForge como ferramenta open source de referencia para self-healing de testes E2E, com suporte a 10+ frameworks UI, integracao nativa com CI/CD, e comunidade ativa de contribuidores.

Mas comecamos com 1 framework (PrimeFaces), 1 tipo de healing (locator fallback), 1 usuario real. O resto vem depois.
