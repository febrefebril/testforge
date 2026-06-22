# Estrategia de Preservacao do Conhecimento

## O Problema

4 tentativas anteriores do TestForge falharam. Mas cada tentativa gerou conhecimento valioso — 49 receitas de cura testadas em sites reais da CAIXA. Esse conhecimento nao pode ser perdido novamente.

## A Solucao

Todo aprendizado e armazenado em 3 camadas independentes:

```
1. HealingCatalog (.planning/healing-catalog.jsonl)
   └── 53 receitas de cura (4 novas + 49 ancestrais)

2. Conhecimento Ancestral (docs/conhecimento_ancestral/)
   └── Documentacao completa das 4 tentativas

3. Git History (35+ commits)
   └── Cada decisao, cada bug, cada correcao versionada
```

## Como o Aprendizado Funciona

```
Teste executa → encontra bug
    ↓
FailureClassifier → classifica falha
    ↓
HealingCatalog.match_recipes() → busca receitas existentes
    ↓
    ├── Receita encontrada → aplica → registra sucesso
    └── Sem receita → cria nova → adiciona ao catalogo
```

## Se o Projeto Falhar Novamente

O conhecimento sobrevive em 3 lugares independentes:

| Fonte | Conteudo | Como recuperar |
|-------|----------|---------------|
| `.planning/healing-catalog.jsonl` | 53 receitas de cura | `cat .planning/healing-catalog.jsonl` |
| `docs/conhecimento_ancestral/` | Documentacao + codigo | `cat docs/conhecimento_ancestral/INDEX.md` |
| `git log` | Historico completo | `git log --oneline` |

## Catalogo Atual (53 receitas)

| Familia | Receitas | Origem |
|---------|----------|--------|
| FAM-01 (Seletores) | 7 | Taxonomia ancestral |
| FAM-02 (Timing) | 3 | Taxonomia ancestral |
| FAM-03 (Contexto) | 4 | Taxonomia ancestral |
| FAM-04 (Estado) | 3 | Taxonomia ancestral |
| FAM-05 (DOM Dinamico) | 3 | Taxonomia ancestral |
| FAM-06 (Input) | 4 | Taxonomia ancestral |
| FAM-07 (Upload) | 2 | Taxonomia ancestral |
| FAM-08 (Assert) | 6 | Taxonomia ancestral |
| FAM-09 (Recorder) | 3 | Taxonomia ancestral |
| FAM-10 (Execucao) | 10 | Testes reais CAIXA |
| FAM-11 (Browser/Limits) | 4 | Testes reais CAIXA |
| Angular (Novo) | 3 | Nossa implementacao |
| Generic (Novo) | 1 | Nossa implementacao |

## Proxima Tentativa (se houver)

```bash
# 1. Clone este repo
git clone <repo>

# 2. O catalogo de cura ja esta aqui
cat .planning/healing-catalog.jsonl

# 3. A documentacao ancestral tambem
cat docs/conhecimento_ancestral/INDEX.md

# 4. O historico completo de decisoes
git log --oneline

# 5. Os diagramas da arquitetura
ls docs/diagramas/

# 6. Rode os testes para ver o que funciona
python -m pytest tests/ -v
```
