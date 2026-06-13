# TestForge — Requisitos

## R1: Recorder Sensorial
- Capturar eventos de usuario via Playwright API nativa (pointerup, input, keydown)
- Gerar RawRecordedSession com raw_events.jsonl, screenshots, DOM/AX snapshots
- NAO gerar script final, NAO escolher locator definitivo
- Deteccao de framework (PrimeFaces, Angular, jQuery UI, Kendo)

## R2: SemanticTestCase
- Converter RawRecordedSession em contrato semantico YAML
- Gerar multiplos candidatos de locator por acao
- Scoring deterministico (role+name > label > placeholder > testid > text > css)
- SemanticTestCase e fonte de verdade; script Playwright e derivado

## R3: Compiler Playwright
- Gerar script Python com fallback loop (for/else/try/except)
- Script executavel standalone via pytest
- Suporte a PrimeFaces SelectOneMenu, autocomplete, datepicker

## R4: Self-Healing
- 4-layer healing: Recipe Catalog → Specialist Agent → Evidence Collector → LLM Healer
- Classificacao de falha por taxonomia (locator, actionability, sync, oracle)
- LLM apenas como curador, off critical path

## R5: Evidence + Oracle
- Coleta de evidencias por evento (DOM, screenshot, network, console)
- Oracle visual_dom + business_state
- Sensitive data: alert_only no MVP

## Fora do MVP
- Shadow Mode com revisao humana
- Promotion Gate completo
- Dashboard/metricas em tempo real
- Multiplos oracles complexos
