# TestForge v0.2.0

Plataforma para gravar fluxos de usuário como contratos semânticos, gerar testes Playwright robustos, executar validações em shadow mode, sugerir self-healing determinístico, coletar evidências, validar oracles pós-ação e promover curas apenas por meio de Promotion Gate.

## Arquitetura
```
Recorder Sensorial -> RawRecordedSession (recordings/)
  -> SemanticTestCase (semantic_tests/) [fonte de verdade]
  -> Playwright Compiler -> Generated Test (generated_tests/) [derivado]
  -> Runner / Shadow Mode / Evidence / Oracle / Promotion Gate
```

## Princípios
1. Determinístico primeiro. LLM apenas como curadoria.
2. Nenhum healing sem evidência. Nenhuma promoção sem Promotion Gate.
3. Shadow mode antes de auto-heal. Synthetic Lab antes de piloto real.
4. SemanticTestCase é fonte de verdade; Playwright gerado é derivado.
5. Dados sensíveis no MVP: alert_only, sem mascaramento automático.

## Como executar
```bash
pip install playwright pyyaml pytest pytest-asyncio
playwright install chromium
python -m pytest tests/ -v
python scripts/record_fake_flow.py
python scripts/compile_recording.py <RECORDING_ID>
python scripts/run_synthetic_shadow_flow.py change_accessible_name
python scripts/review_pending.py
python scripts/generate_synthetic_report.py
```
