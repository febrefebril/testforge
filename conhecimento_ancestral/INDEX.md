# TestForge - Conhecimento Ancestral

Conhecimento acumulado em 4 tentativas anteriores de construir o TestForge.
Organizado, limpo e renomeado para facilitar consulta.

---

## Estrutura

```
conhecimento_ancestral/
├── INDEX.md
├── planejamento/                       ← Artefatos de planejamento e arquitetura
│   ├── plano-macro.md                  ← Visao geral do TestForge
│   ├── arquitetura-selfhealing.md      ← Arquitetura do self-healing deterministico
│   ├── locators-ranking-fallback.md    ← Sistema de locators
│   ├── tecnologias-oracle-shadow.md    ← Oracle, shadow, sintetico
│   ├── mutacoes-sinteticas.md          ← Mutacoes sinteticas para teste
│   ├── shadow-*.md|yaml               ← Shadow mode (experimento, validacao, observacao)
│   ├── promotion-gate.*               ← Gate de promocao
│   ├── mis-*                           ← MIS (guia, modelo, schema)
│   ├── healing-*                       ← Healing (governance YAML, KB SQL)
│   ├── locator-engine.py              ← Motor de locators esqueleto
│   ├── config.ini, config.yaml
│   ├── discussao-arquitetura/          ← Consolidado de decisoes de arquitetura
│   ├── epicos-historias/               ← Epicos, historias, backlog, criterios
│   ├── codigo-v020/                    ← Codigo fonte v0.2.0 (versao mais completa)
│   │   ├── src/testforge/             ← Modulos: recorder, semantic, compiler, etc
│   │   ├── adrs/                       ← 3 Architecture Decision Records
│   │   └── tests/                      ← Testes unitarios
│   ├── prompt-pack-v1/                 ← LLM prompt pack v1
│   ├── prompt-pack-v2/                 ← LLM prompt pack v2 (recorder sensorial)
│   ├── recorder-exemplos/              ← Exemplo de gravacao raw real
│   └── tarefas-mvp/                    ← Tarefas MVP, priorizacao, estimativas
├── projeto-anterior/                   ← Snapshot do projeto anterior completo
│   ├── demo/                           ← Demonstracao funcional do recorder
│   ├── testes/                         ← 30+ sessoes de teste reais
│   ├── packages/                       ← bridge (extensao), core (healing agents), war-room
│   ├── docs/                           ← Fluxogramas PlantUML e pesquisas
│   └── _bmad/                          ← BMAD artifacts da tentativa anterior
├── versao-alternativa/                 ← Versao alternativa do projeto (tar.gz)
│   ├── generator/                      ← Gerador de testes via LLM
│   ├── healer/                         ← Self-healer (patcher, runner)
│   ├── optimizer/                      ← Profiler e tuner
│   ├── recorder/                       ← Recorder com injection JS
│   └── recording_manager.py
└── diagramas-taxonomia/                ← Diagramas e taxonomia de casos
    ├── fluxogramas/                    ← Fluxogramas PlantUML (C4, componentes, sequencia, estados)
    ├── taxonomia/                      ← Taxonomia completa de casos conhecidos
    │   ├── curator-decision-tree.puml ← Arvore de decisao do curador
    │   ├── healing-strategies.md      ← Estrategias de healing por caso
    │   ├── taxonomy.cases.yaml        ← Catalogo de casos
    │   └── taxonomy.schema.yaml       ← Schema da taxonomia
    └── taxonomia.puml                  ← Taxonomia PlantUML completa
```

---

## Guia Rapido de Consulta

| Topico | Caminho |
|--------|---------|
| Visao geral do projeto | `planejamento/plano-macro.md` |
| Arquitetura self-healing | `planejamento/arquitetura-selfhealing.md` |
| Decisoes de arquitetura | `planejamento/discussao-arquitetura/` |
| ADRs | `planejamento/codigo-v020/adrs/` |
| Epicos e historias | `planejamento/epicos-historias/` |
| Tarefas MVP | `planejamento/tarefas-mvp/` |
| Locators e fallback | `planejamento/locators-ranking-fallback.md` |
| Self-healing governance | `planejamento/healing-governance.yaml` |
| Healing KB schema | `planejamento/healing-kb.sql` |
| Taxonomia de falhas | `diagramas-taxonomia/taxonomia/` |
| Arvore de decisao do curador | `diagramas-taxonomia/taxonomia/curator-decision-tree.puml` |
| Estrategias de healing | `diagramas-taxonomia/taxonomia/healing-strategies.md` |
| Codigo mais maduro | `planejamento/codigo-v020/src/testforge/` |
| Demo funcional | `projeto-anterior/demo/` |
| Testes reais | `projeto-anterior/testes/` |
| Healing agents | `projeto-anterior/packages/core/testforge/core/healing/agents/` |
| Recorder alternativo | `versao-alternativa/recorder/` |
| Generator LLM | `versao-alternativa/generator/` |
| Diagramas PlantUML | `projeto-anterior/docs/fluxogramas/plantuml/` |
| Prompt packs LLM | `planejamento/prompt-pack-v2/` |
| Exemplo gravacao raw | `planejamento/recorder-exemplos/exemplo_raw_recording/` |

---

*Organizado em $(date). Nomes simplificados, prefixos `testforge_` removidos, manifests descartados.*
