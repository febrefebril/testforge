# Milestone 1 — Discussao: Fundacao + Synthetic Lab

## Decisoes de Implementacao

### 1. Estrutura do Repositorio
- **Decisao:** Usar estrutura definida na arquitetura (src/testforge/, recordings/, semantic_tests/, generated_tests/, evidence/, policies/, schemas/, adrs/, synthetic_lab/, tests/)
- **Alternativa rejeitada:** Estrutura plana (tudo em src/) — descartada por poluir namespace
- **Motivo:** Separacao clara de responsabilidades, alinhada com a arquitetura de 6 componentes

### 2. Fake App: React ou HTML puro?
- **Decisao:** HTML puro com estilos inline, simulando comportamento React
- **Alternativa rejeitada:** React app real com Vite/webpack
- **Motivo:** Zero dependencias, roda em qualquer maquina com `python -m http.server`. O objetivo e testar o pipeline de testes, nao o build do fake app.

### 3. Mutation Matrix
- **Decisao:** YAML declarativo com 5 mutacoes iniciais
- **Mutations:** change_id, change_accessible_name, duplicate_button_text, overlay_blocks_click, disabled_button
- **Cada mutation:** code, technology, url_query, expected_taxonomy, expected_recoverable, expected_strategy, expected_oracles

### 4. README e Documentacao
- **Decisao:** README.md documentando a arquitetura, diretorios, e como executar
- **CHANGELOG.md:** formato Keep a Changelog
- **VERSION:** 0.1.0 (primeira versao do novo TestForge)

### 5. ADRs Iniciais
- ADR-0001: Shadow mode antes de auto-heal
- ADR-0002: EvidenceCollector alert_only para dados sensiveis
- ADR-0003: SemanticTestCase como fonte de verdade, Playwright gerado como derivado

### 6. Dependencias Python
- **Decisao:** `pyproject.toml` com dependencias minimas: playwright, pyyaml, typer
- **Sem SQLite no MVP:** JSONL + filesystem. SQLite entra no Milestone 3.

### 7. Ordem de Implementacao
1. Estrutura de diretorios + arquivos base
2. fake-react-bank-app (HTML puro)
3. Teste Playwright do fluxo sem mutacao
4. mutation_matrix.yaml
5. Cada mutacao: implementar + teste Playwright
6. Validar que cada mutacao quebra o teste base como esperado

## Riscos
- Fake app muito simples pode nao exercitar casos edge do healing
- Mitigacao: 5 mutacoes cobrem os casos principais (id change, ambiguous text, overlay, disabled)
