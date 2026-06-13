# TestForge — Como Testar o Recorder Automaticamente

## 1. Estratégia

O gravador deve ser testado em três níveis:

```text
1. Testes unitários
2. Testes de integração com Playwright e fake-react-bank-app
3. Teste E2E: gravação -> RawRecordedSession -> SemanticTestCase -> teste Playwright gerado
```

O objetivo não é validar apenas que arquivos foram criados, mas que a gravação é reprocessável e contém sinais suficientes para o MIS.

---

# 2. Testes unitários

## Deve testar

- `RecordingSession` cria `recording_id`.
- `RecorderController.start()` cria diretório da gravação.
- `RecorderController.stop()` atualiza metadata.
- Sessão finalizada rejeita novos eventos.
- `RawRecordingStore.append_event()` escreve uma linha JSONL válida.
- Detector de dados sensíveis gera alerta sem mascarar.

## Exemplo de teste unitário

```python
def test_recording_session_start_stop(tmp_path):
    controller = RecorderController(root_dir=tmp_path)

    session = controller.start(
        application="fake-react-bank-app",
        base_url="http://localhost:3000"
    )

    assert session.recording_id.startswith("REC-")
    assert (tmp_path / session.recording_id).exists()
    assert (tmp_path / session.recording_id / "recording_metadata.json").exists()

    controller.stop(session.recording_id)

    metadata = json.loads(
        (tmp_path / session.recording_id / "recording_metadata.json").read_text()
    )

    assert metadata["status"] == "finished"
    assert metadata["finished_at"] is not None
```

---

# 3. Testes de integração com Playwright

## Deve testar

- Abre fake-react-bank-app.
- Inicia gravação.
- Preenche CPF.
- Clica em Pesquisar.
- Finaliza gravação.
- Valida `raw_events.jsonl`.
- Valida screenshots e DOM snapshots.
- Valida `sensitive_data_alert.json`.

## Exemplo de teste com pytest + Playwright async

```python
import json
from pathlib import Path
import pytest
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_recorder_captures_fake_flow(tmp_path):
    app_url = Path("synthetic_lab/fake-react-bank-app/index.html").resolve().as_uri()

    controller = RecorderController(root_dir=tmp_path / "recordings")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        session = await controller.start_browser_recording(
            page=page,
            application="fake-react-bank-app",
            base_url=app_url,
        )

        await page.goto(app_url)
        await page.get_by_label("CPF").fill("12345678900")
        await page.get_by_role("button", name="Pesquisar").click()

        await controller.stop(session.recording_id)
        await browser.close()

    recording_dir = tmp_path / "recordings" / session.recording_id

    assert (recording_dir / "recording_metadata.json").exists()
    assert (recording_dir / "raw_events.jsonl").exists()
    assert (recording_dir / "sensitive_data_alert.json").exists()

    events = [json.loads(line) for line in (recording_dir / "raw_events.jsonl").read_text().splitlines()]

    assert any(e["type"] in {"fill", "input"} for e in events)
    assert any(e["type"] == "click" for e in events)

    fill_event = next(e for e in events if e["type"] in {"fill", "input"})
    assert fill_event["target"]["label"] == "CPF"
    assert fill_event["input"]["value"] == "12345678900"
    assert fill_event["input"]["sensitive_data_alert"]["masking_applied"] is False

    click_event = next(e for e in events if e["type"] == "click")
    assert click_event["target"]["role"] == "button"
    assert click_event["target"]["accessible_name"] == "Pesquisar"

    assert len(list((recording_dir / "screenshots").glob("*.png"))) >= 1
    assert len(list((recording_dir / "dom_snapshots").glob("*.html"))) >= 1
```

---

# 4. Teste de contrato do raw_events.jsonl

Validar que cada linha do `raw_events.jsonl` cumpre contrato mínimo.

```python
def test_raw_events_contract(recording_dir):
    events_path = recording_dir / "raw_events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines()]

    required_fields = {"schema_version", "event_id", "sequence", "timestamp", "type", "url", "page_title"}

    for event in events:
        assert required_fields.issubset(event.keys())
        assert event["event_id"].startswith("evt_")
        assert isinstance(event["sequence"], int)

        if event["target"] is not None:
            assert "tag" in event["target"]
            assert "attributes" in event["target"]
```

---

# 5. Teste de não mascaramento

Este teste garante a decisão atual: alertar, mas não mascarar.

```python
def test_recorder_alerts_sensitive_data_without_masking(recording_dir):
    alert = json.loads((recording_dir / "sensitive_data_alert.json").read_text())
    raw = (recording_dir / "raw_events.jsonl").read_text()

    assert alert["policy"] == "alert_only"
    assert alert["masking_applied"] is False
    assert alert["possible_sensitive_data_detected"] is True

    # O valor original permanece preservado no MVP.
    assert "12345678900" in raw
```

---

# 6. Teste E2E da cadeia gravação -> MIS -> teste gerado

## Deve testar

1. Grava fluxo no fake app.
2. Gera `semantic_test_case.yaml`.
3. Compila teste Playwright em `generated_tests/{test_id}`.
4. Executa teste gerado.
5. Teste gerado passa contra fake app sem mutação.

## Exemplo de pseudo-teste

```python
@pytest.mark.asyncio
async def test_recording_can_generate_semantic_test_and_playwright_test(tmp_path):
    recording_id = await record_fake_flow(tmp_path)

    semantic_test_path = generate_semantic_test_case(
        recording_dir=tmp_path / "recordings" / recording_id,
        output_dir=tmp_path / "semantic_tests"
    )

    assert semantic_test_path.exists()

    generated_test_path = compile_playwright_test(
        semantic_test_path=semantic_test_path,
        output_dir=tmp_path / "generated_tests"
    )

    assert generated_test_path.exists()

    result = run_pytest(generated_test_path)
    assert result.exit_code == 0
```

---

# 7. Critérios para considerar o gravador aprovado no MVP

O gravador estará aprovado para o MVP quando:

- Capturar fluxo básico no fake-react-bank-app.
- Persistir RawRecordedSession completa.
- Gerar raw_events.jsonl válido.
- Capturar pelo menos screenshot e DOM snapshot por evento relevante.
- Registrar alerta de dado sensível sem mascarar.
- Gerar SemanticTestCase a partir da gravação.
- Gerar teste Playwright executável a partir do SemanticTestCase.
- O teste gerado passar contra o fake app sem mutação.
