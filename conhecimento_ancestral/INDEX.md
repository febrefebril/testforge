# TestForge - Conhecimento Ancestral

Indice do conhecimento acumulado em 4 tentativas anteriores. Organizado e limpo.

---

## Estrutura

```
conhecimento_ancestral/
├── INDEX.md                              ← Este indice
├── origem/                               ← Artefatos extraidos do base64
│   ├── testforge_plano_macro_completo.md
│   ├── testforge_arquitetura_selfhealing_deterministico.md
│   ├── testforge_locators_ranking_fallback.md
│   ├── testforge_tecnologias_oracle_shadow_sintetico.md
│   ├── testforge_synthetic_mutations.md
│   ├── testforge_shadow_*.md/yaml        ← Shadow mode docs
│   ├── testforge_promotion_gate.*        ← Promotion gate
│   ├── testforge_mis_*                   ← MIS docs e modelo
│   ├── testforge_healing_*               ← Healing governance + KB SQL
│   ├── testforge_locator_engine_skeleton.py
│   ├── config.ini, config.yaml
│   ├── testforge_consolidado_discussao_arquitetura/  ← Decisoes de arq
│   ├── testforge_epicos_historias_plano/             ← Epicos e historias
│   ├── testforge_projeto_completo_v020/              ← Codigo v0.2.0 completo
│   ├── testforge_prompt_pack_llm/                    ← LLM prompts v1
│   ├── testforge_prompt_pack_llm_v0_2_0/             ← LLM prompts v2
│   ├── testforge_recorder_criterios_exemplo_testes/  ← Gravacao exemplo
│   └── testforge_tarefas_priorizacao_estimativas/    ← Tarefas MVP
├── testforge/                            ← Projeto ancestral completo
│   ├── demo/                             ← Demo funcional
│   ├── testes/                           ← 30+ sessoes de teste
│   ├── packages/                         ← bridge, core, war-room
│   ├── docs/                             ← Fluxogramas PlantUML
│   └── _bmad/                            ← BMAD artifacts
├── testforge-versao-targz/               ← Versao alternativa (tar.gz)
│   ├── generator/                        ← Gerador de testes
│   ├── healer/                           ← Self-healer
│   ├── optimizer/                        ← Otimizador
│   ├── recorder/                         ← Recorder (injection JS)
│   └── recording_manager.py
└── testforgeDiagramasTaxonomia/          ← Diagramas e taxonomia
    ├── fluxogramas.b64                   ← Fluxogramas (protegido)
    ├── fluxogramas_extracted/            ← Extraido parcial
    ├── taxonomia.puml                    ← Taxonomia PlantUML
    └── taxonomia_extracted/              ← Taxonomia detalhada
```

---

## Guia Rapido de Consulta

| Topico | Onde encontrar |
|--------|---------------|
| **Visao geral** | `origem/testforge_plano_macro_completo.md` |
| **Arquitetura** | `origem/testforge_arquitetura_selfhealing_deterministico.md` |
| **Self-healing** | `origem/testforge_healing_governance.yaml`, `origem/testforge_healing_kb_schema.sql` |
| **Sistema de locators** | `origem/testforge_locators_ranking_fallback.md` |
| **Codigo mais maduro** | `origem/testforge_projeto_completo_v020/testforge/src/` |
| **ADRs** | `origem/testforge_projeto_completo_v020/testforge/adrs/` |
| **Taxonomia de falhas** | `testforgeDiagramasTaxonomia/taxonomia_extracted/` |
| **Epicos/historias** | `origem/testforge_epicos_historias_plano/` |
| **Demo funcional** | `testforge/demo/` |
| **Testes reais** | `testforge/testes/` |
| **Healing agents** | `testforge/packages/core/testforge/core/healing/agents/` |
| **Recorder v1** | `testforge/packages/core/testforge/core/recording/` |
| **Recorder v2 (targz)** | `testforge-versao-targz/recorder/` |
| **Generator** | `testforge-versao-targz/generator/` |
| **Healer** | `testforge-versao-targz/healer/` |
| **Diagramas PlantUML** | `testforge/docs/fluxogramas/plantuml/` |
| **Prompt packs LLM** | `origem/testforge_prompt_pack_llm_v0_2_0/` |

---

*Limpo em $(date). 7 ZIPs + 3 originais + 3 temp files removidos. Estrutura reorganizada.*
