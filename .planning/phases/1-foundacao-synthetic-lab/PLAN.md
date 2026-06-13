# Milestone 1 — Plano: Fundacao + Synthetic Lab

## Objetivo
Criar estrutura base do repositorio e synthetic lab com fake app + 5 mutacoes.

## Tarefas

### T1: Estrutura do Repositorio
- [ ] Criar diretorios: src/testforge/{recorder,semantic,compiler,runner,healing,evidence,oracle,promotion,taxonomy,metrics,models,config,cli,logging}
- [ ] Criar diretorios: recordings/, semantic_tests/, generated_tests/, evidence/, policies/, schemas/, adrs/, synthetic_lab/, tests/
- [ ] Criar README.md com arquitetura e como executar
- [ ] Criar CHANGELOG.md
- [ ] Criar VERSION (0.1.0)
- [ ] Criar pyproject.toml com deps: playwright, pyyaml, typer
- [ ] Criar .gitignore (se necessario atualizar)

### T2: ADRs
- [ ] ADR-0001: Shadow mode before auto-heal
- [ ] ADR-0002: EvidenceCollector alert_only
- [ ] ADR-0003: SemanticTestCase as source of truth

### T3: fake-react-bank-app
- [ ] synthetic_lab/fake-react-bank-app/index.html
  - Campo CPF com label acessivel
  - Botao Pesquisar com accessible name
  - Secao Resultado da consulta
  - Suporte a query string para mutacoes

### T4: Teste Playwright base (sem mutacao)
- [ ] tests/test_fake_bank_flow.py
  - Preenche CPF
  - Clica Pesquisar
  - Verifica resultado visivel

### T5: mutation_matrix.yaml
- [ ] synthetic_lab/mutation_matrix.yaml com 5 mutacoes:
  - change_id
  - change_accessible_name
  - duplicate_button_text
  - overlay_blocks_click
  - disabled_button

### T6: Implementar mutacoes no fake app
- [ ] change_id: query string ?mutation=change_id altera IDs
- [ ] change_accessible_name: altera aria-label/nome acessivel
- [ ] duplicate_button_text: duplica botao com mesmo texto
- [ ] overlay_blocks_click: overlay cobre o botao
- [ ] disabled_button: botao fica disabled

### T7: Testes Playwright para cada mutacao
- [ ] test_change_id.py: verifica que seletor original quebra
- [ ] test_change_accessible_name.py
- [ ] test_duplicate_button_text.py
- [ ] test_overlay_blocks_click.py
- [ ] test_disabled_button.py

### T8: Script de execucao
- [ ] scripts/run_all_mutations.sh: executa fake app + todos os testes
- [ ] Documentar no README como rodar

## Verificacao
- Todos os diretorios existem
- README documenta a estrutura
- Fake app roda com `python -m http.server`
- Teste base passa (fluxo sem mutacao)
- Cada mutacao quebra o teste base como esperado
- mutation_matrix.yaml valido
