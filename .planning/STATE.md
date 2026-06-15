# TestForge — Estado do Projeto

**Inicio:** 2026-06-13
**Versao:** 0.3.0
**Fase:** v0.3.0 Shipada — LLM Self-Healing completo
**Ultimo commit:** `17a4708` feat: data-driven testing

## Metricas
- **19 commits** nesta sessão (77 total no projeto)
- **124 testes** passando
- **24 modulos** implementados
- **13 diagramas** PlantUML
- **88 falhas** catalogadas na taxonomia
- **6 agentes** especialistas L2
- **11 prompts** família-específicos (EN)
- **LLM real validado:** Azure GPT-4.1-mini curou `change_id` (conf 0.90)

## Milestones Concluidos
- [x] BMAD Brainstorming (Failure Analysis + Five Whys)
- [x] BMAD Product Brief
- [x] BMAD Arquitetura
- [x] M1: Fundacao + Synthetic Lab
- [x] M2: Recorder Sensorial + Asserts
- [x] M3: Evidence Collector + Store
- [x] M4: MIS + Compiler Playwright
- [x] M5: Oracle + PromotionGate
- [x] M6: Taxonomia + ShadowValidator + FallbackRunner
- [x] M7: Metricas + Revisao CLI
- [x] CLI installavel: record, compile, run, pipeline, demo-heal
- [x] 6 diagramas PlantUML: plano LLM self-healing (componentes, sequencia, estados, integracao, classes, deploy)

## Em Progresso (v0.2.0)
- [x] Fase 1: Expandir taxonomia (6→11 familias, keyword+group classifier)
- [ ] Fase 2: EvidencePayload estruturado para LLM
- [ ] Fase 3: LLM Healer + MockLLMHealer + 11 prompts familia
- [ ] Fase 4: CuradorAutomatico (pipeline L0→L1→L2→L3)
- [ ] Fase 5: Integrar cmd_run com CuradorAutomatico
- [ ] Fase 6: Testes de integracao L3
- [ ] Fase 7: L2 Agents (opcional)

## Proximo
- [ ] EvidencePayload dataclass + adaptar EvidenceCollector
- [ ] LLMClient (Azure OpenAI / OpenAI)
- [ ] Prompt pack GSD (US-08.05)
