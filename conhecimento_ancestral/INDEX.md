# TestForge - Conhecimento Ancestral

Indice do conhecimento acumulado em 4 tentativas anteriores de construir o TestForge.

---

## 1. Arquitetura & Decisoes Tecnicas

| Arquivo | Conteudo |
|---------|----------|
| `origem/testforge_arquitetura_selfhealing_deterministico.md` | Arquitetura do self-healing deterministico |
| `origem/testforge_plano_macro_completo.md` | Plano macro completo do TestForge |
| `origem/testforge_locators_ranking_fallback.md` | Sistema de locators com ranking e fallback |
| `origem/testforge_tecnologias_oracle_shadow_sintetico.md` | Tecnologias: oracle, shadow mode, synthetic |
| `origem/testforge_shadow_experiment_plan.md` | Plano de experimento shadow |
| `origem/testforge_shadow_mode_validacao.md` | Validacao do shadow mode |
| `origem/testforge_synthetic_mutations.md` | Mutacoes sinteticas para testes |
| `origem/testforge_promotion_gate.md` | Gate de promocao (promotion) |
| `origem/testforge_mis_guia_implementacao.md` | Guia de implementacao MIS |
| `origem/_extracted/testforge_consolidado_discussao_arquitetura/` | Consolidado de discussoes de arquitetura |
| `origem/_extracted/testforge_projeto_completo_v020/testforge/adrs/` | Architecture Decision Records (3 ADRs) |
| `origem/_extracted/testforge_projeto_completo_v020/testforge/policies/` | Politicas: evidence, sensitive data, failure taxonomy |
| `origem/_extracted/testforge_projeto_completo_v020/testforge/schemas/` | Schema: semantic_test_case |

### Diagramas & Taxonomia

| Arquivo | Conteudo |
|---------|----------|
| `testforgeDiagramasTaxonomia/taxonomia.b64` | PlantUML taxonomia de casos (5110 linhas) |
| `testforgeDiagramasTaxonomia/taxonomia_extracted/` | Taxonomia em formato PlantUML extraido |
| `testforgeDiagramasTaxonomia/fluxogramas.b64` | Fluxogramas (protegido por senha) |
| `testforge/docs/fluxogramas/` | Fluxogramas do projeto anterior |

---

## 2. Epic 1 - Recorder (Gravacao de Testes)

Epico principal focado no recorder sensorial.

| Arquivo | Conteudo |
|---------|----------|
| `origem/_extracted/testforge_epicos_historias_plano/` | Epicos, historias e plano macro |
| `origem/_extracted/testforge_recorder_criterios_exemplo_testes/` | Criterios de aceitacao com exemplos de gravacao |
| `testforge/README-EPIC1.md` | README detalhado do Epic 1 |
| `testforge/demo/` | Demonstracao funcional do recorder |
| `testforge/testes/` | 30+ sessoes de teste gravadas |
| `testforge/packages/bridge/` | Pacote bridge |
| `testforge/packages/core/` | Pacote core do recorder |
| `testforge/packages/war-room/` | Pacote war-room |

---

## 3. Codigo Fonte (4 tentativas)

### v0.2.0 - Projeto mais completo
`origem/_extracted/testforge_projeto_completo_v020/testforge/src/testforge/`

| Modulo | Descricao |
|--------|-----------|
| `recorder/` | Gravador raw de eventos + detector de dados sensiveis |
| `semantic/` | Normalizador + gerador de candidatos semanticos |
| `compiler/` | Compilador Playwright |
| `oracle/` | Oracle runner |
| `runner/` | Fallback runner |
| `shadow/` | Shadow validator |
| `evidence/` | Coletor e store de evidencias |
| `taxonomy/` | Classificador de falhas + taxonomia |
| `promotion/` | Promotion gate |
| `metrics/` | Repositorio de metricas |

### Outros codigos

| Arquivo | Conteudo |
|---------|----------|
| `origem/testforge_locator_engine_skeleton.py` | Esqueleto do motor de locators |
| `origem/testforge_promotion_gate.py` | Implementacao do promotion gate |
| `origem/testforge_mis_modelo_python.py` | Modelo Python do MIS |
| `origem/testforge_healing_kb_schema.sql` | Schema SQL da knowledge base de healing |
| `origem/testforge_healing_governance.yaml` | Governanca do healing |
| `origem/testforge_shadow_experiment_plan.yaml` | Plano shadow (YAML) |
| `origem/testforge_shadow_observation_schema.yaml` | Schema de observacao shadow |
| `origem/testforge_promotion_gate_policy.yaml` | Politica do promotion gate |
| `origem/testforge_mis_schema_exemplo.yaml` | Schema exemplo MIS |

---

## 4. LLM Prompt Packs

| Arquivo | Conteudo |
|---------|----------|
| `origem/_extracted/testforge_prompt_pack_llm/` | Prompt pack para desenvolvimento com LLM |
| `origem/_extracted/testforge_prompt_pack_llm_v0_2_0/` | Prompt pack v0.2.0 com epico recorder sensorial |

---

## 5. Tarefas & Priorizacao

| Arquivo | Conteudo |
|---------|----------|
| `origem/_extracted/testforge_tarefas_priorizacao_estimativas/` | Tarefas MVP1 em CSV + guia de transformacao |

---

## 6. Projeto Anterior Completo

`testforge/` — snapshot de um projeto anterior com:
- `.venv/` — ambiente Python
- `demo/` — demonstracao funcional
- `testes/` — 30+ sessoes de teste
- `packages/` — bridge, core, war-room
- `_bmad/` + `_bmad-output/` — BMAD artifacts
- `docs/` — documentacao e fluxogramas

---

## 7. Artefatos Brutos (originais)

| Arquivo | Formato |
|---------|---------|
| `pasta_origem.b64.txt` | Base64 do ZIP original |
| `testforge.tar.gz` | Archive comprimido do projeto |
| `testforgeDiagramasTaxonomia/fluxogramas.b64` | Fluxogramas (protegido) |
| `testforgeDiagramasTaxonomia/taxonomia.b64` | Taxonomia PlantUML |

---

## Como Usar Este Indice

1. **Entender o dominio**: comece por `origem/testforge_plano_macro_completo.md`
2. **Arquitetura**: leia `origem/testforge_arquitetura_selfhealing_deterministico.md`
3. **Codigo mais maduro**: `origem/_extracted/testforge_projeto_completo_v020/`
4. **Testes reais**: `testforge/testes/` e `testforge/demo/`
5. **Decisoes**: `origem/_extracted/testforge_projeto_completo_v020/testforge/adrs/`

---

*Indice gerado automaticamente em $(date). Use `@bmad` para iniciar o processo de brainstorming.*
