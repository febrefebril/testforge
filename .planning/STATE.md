# TestForge — Estado do Projeto

**Inicio:** 2026-06-13
**Versao:** 0.3.0
**Fase:** Shipada — LLM Self-Healing L0→L3 completo, Data-Driven Testing
**Ultimo commit:** `6095846` fix: AttributeError _try_layer2_agents + double underscore collapse

## Metricas
- **84 commits** no main
- **124 testes** passando
- **28 modulos** implementados
- **15 diagramas** PlantUML
- **88 falhas** catalogadas na taxonomia (11 familias)
- **6 agentes** especialistas L2
- **11 prompts** familia-especificos (EN)
- **LLM real validado:** Azure GPT-4.1-mini curou mutation `change_id` (conf 0.90)

## Milestones Concluidos
- [x] BMAD Brainstorming + Product Brief + Arquitetura
- [x] M1-M7 (v0.1.0): Fundacao + Recorder + Evidence + MIS + Oracle + Taxonomia + Metricas
- [x] M8 (v0.2.0): CLI + Pipeline (record, compile, run, pipeline, demo-heal)
- [x] M9 (v0.3.0): LLM Self-Healing L0→L3
  - [x] Taxonomia expandida (6→11 families, 88 codigos, keyword+group classifier)
  - [x] EvidencePayload + EvidenceCollector.build_llm_payload()
  - [x] LLMClient (Azure/OpenAI) + retry + imagens base64
  - [x] LLMHealer + MockLLMHealer + 11 family prompts (EN)
  - [x] CuradorAutomatico (pipeline L0→L1→L2→L3) + failure tracker
  - [x] 6 L2 Specialist Agents (Selector, Timing, Context, State, DOM, Input)
  - [x] cmd_run inline execution com healing L0→L3
  - [x] Data-driven testing: massa JSON externa (--data, --scenarios)
  - [x] Validado com Azure GPT-4.1-mini real
- [x] Sprint 10: Prompt Pack v0.3.0 + TUTORIAL-LLM-HEALING
- [x] 15 diagramas PlantUML atualizados

## Proximo
- L3c: LLM Curator (valida execucao, registra receitas aprendidas)
- Pipeline CI (GitHub Actions / Azure DevOps)
- Dashboard web de metricas
- Mascaramento automatico de dados sensiveis (alem de alert_only)
- Suporte a mais frameworks (PrimeFaces SelectOneMenu, autocomplete, datepicker)
