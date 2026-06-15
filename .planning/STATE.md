# TestForge — Estado do Projeto

**Inicio:** 2026-06-13
**Versao:** 0.2.0-dev
**Fase:** LLM Self-Healing L3 — Fase 1 concluida (taxonomia)
**Ultimo commit:** `b66803f` feat: expandir taxonomia 6→11 familias, 80+ codigos, keyword+group classifier

## Metricas
- **65 commits** no main
- **99 testes** passando
- **3239 linhas** de codigo
- **16 modulos** implementados
- **13 diagramas** PlantUML
- **88 falhas** catalogadas na taxonomia

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
