# TestForge — Test Patterns (padrão de mercado)

**Audiência**: LLMs implementando fases do `HEALING-GAPS-PLAN.md` + humanos escrevendo novos testes.
**Data**: 2026-07-02.
**Escopo**: (1) testes de suíte interna do TestForge; (2) testes gerados pelo TestForge para aplicações do cliente.

Este documento é **contrato obrigatório**. Toda fase do plano segue essas regras. Testes novos que não seguem são rejeitados no code review.

---

## 1. Filosofia

TestForge testa aplicações **críticas** (bancárias, seguros, saúde, gov). Nossa suíte precisa ser tão confiável quanto o código que emite. Duas propriedades não-negociáveis:

1. **Um teste falha por UMA razão específica**. Não misturar setup, ação, validação em ordem obscura.
2. **Manutenção previsível**. Renomear arquivo, mover fixture, adicionar caso — não deve quebrar 40 outros testes.

Não usamos ferramentas exóticas. Stack fixado: `pytest` + `pytest-playwright` + `pytest-parametrize` + `unittest.mock`. Se um cenário exige biblioteca nova, decisão explícita no plano da fase.

---

## 2. Estrutura de diretórios

```
tests/
  conftest.py                  # fixtures root (page factory, tmp_recording_dir, etc)
  pytest.ini                   # marks, testpaths, asyncio_mode, addopts
  factories/                   # dataclass/dict factories — não são testes
    __init__.py
    semantic_action.py         # make_semantic_action(...)
    semantic_target.py         # make_semantic_target(...)
    locator_candidate.py       # make_candidate(strategy="role", ...)
    raw_event.py               # make_raw_event(event_type="click", ...)
    curator_outcome.py         # make_curation_outcome(status="passed_step", ...)
  helpers/                     # utilities compartilhados por múltiplas suites
    __init__.py
    dom_snapshot_builder.py
    mock_page.py               # MockPage class factory
    assertion_helpers.py       # assert_curation_passed_step(...) etc
  unit/                        # <10ms cada, sem I/O, sem browser
    conftest.py
    healing/
      test_curator_l0_when_runner_missing_then_falls_through.py
      test_curator_l2_when_runner_missing_then_falls_through.py
      test_state_agent_when_dom_lacks_dialog_then_returns_none.py
      test_input_agent_when_dom_lacks_mask_attrs_then_returns_none.py
    runtime/
      test_resolver_when_first_candidate_fill_fails_then_tries_next.py
      test_resolver_when_cache_hit_then_uses_cached_idx.py
    runner/
      test_step_postcondition_when_mask_currency_then_compares_magnitude.py
      test_step_executor_when_action_raises_then_retries_next_candidate.py
    semantic/
      test_normalizer_when_target_empty_candidates_then_synthesizes_css.py
      test_normalizer_when_ir_dedupe_drops_entry_then_logs_reason.py
    recorder/
      test_overlay_snapshot_when_dom_has_no_inputs_then_emits_unknown.py
  integration/                 # 10-500ms, componentes reais, sem browser
    conftest.py
    test_pipeline_normalize_to_compile.py
    test_pipeline_resolve_to_execute_with_retry.py
    test_pipeline_healing_l0_to_l3_escalation.py
    test_pipeline_recording_to_semantic_test_case.py
  e2e/                         # 1-30s cada, browser real, fixture HTML
    conftest.py
    pages/                     # HTML fixtures (também usadas por intent_lab)
      material_hidden_after_render.html
      currency_mask_form.html
      broken_submit.html       # p/ Fase 7 bug detection
      dialog_on_click.html
    test_recording_captures_currency_mask_intent.py
    test_replay_recovers_from_hidden_input_via_retry.py
    test_bug_detection_flags_500_response_during_recording.py  # Fase 7
  regression/                  # bug_lab consolidado + widget_regression
    conftest.py
    material/
      test_datepicker_click_only_regression.py
      test_dedup_key_collision_regression.py
    resolver/
      test_gap01_first_candidate_exists_but_fill_fails.py
  contract/                    # invariantes de módulo — hexagonal boundary
    test_curator_outcome_invariants.py
    test_semantic_action_serialization_roundtrip.py
```

**Regras**:
- Um arquivo por unidade lógica testada. Não `test_utils.py` com 50 asserts.
- Máximo 300 linhas por arquivo de teste. Se estoura, quebrar por sub-classe.
- Diretórios ausentes hoje (`unit/`, `integration/`, `e2e/`, `regression/`, `contract/`) são criados progressivamente. Ver Fase 8 do plano.
- Legacy `tests/test_*.py` na raiz continuam válidos temporariamente. Novos testes vão direto para diretório correto.

---

## 3. Convenção de nomes

### 3.1 Arquivo
```
test_<subject_under_test>_when_<condition>_then_<expected_outcome>.py
```

Exemplos:
- ✅ `test_resolver_when_first_candidate_fill_fails_then_tries_next.py`
- ✅ `test_curator_l0_when_runner_missing_then_falls_through.py`
- ❌ `test_resolver.py` (o quê do resolver?)
- ❌ `test_hotfix22_stuff.py` (nome de commit, não de comportamento)
- ❌ `test_bug_fix_encoding.py` (o quê estava encoded errado?)

### 3.2 Função de teste
```python
def test_<method_or_verb>_when_<condition>_then_<outcome>():
    ...
```

Exemplos:
- ✅ `def test_resolve_when_count_positive_but_fill_raises_then_returns_next_candidate():`
- ✅ `def test_heal_when_dom_snapshot_lacks_dialog_role_then_returns_none():`
- ❌ `def test_case_1():` (case 1 de quê?)
- ❌ `def test_bug():` (qual bug?)

### 3.3 Classe (opcional, use para agrupar contexto compartilhado)
```python
class TestResolverWhenFirstCandidateFails:
    def test_returns_next_candidate_from_ranked_list(self):
        ...
    def test_updates_cache_with_winning_index(self):
        ...
    def test_emits_span_with_attempted_indices(self):
        ...
```

Uma classe = um contexto de setup. Não use classe apenas por organização visual.

---

## 4. Padrão AAA (Arrange, Act, Assert)

Todo teste tem **três blocos visualmente separados** por linha em branco:

```python
def test_resolve_when_first_candidate_exists_but_fill_fails_then_tries_next():
    # Arrange
    page = mock_page_with_two_candidates(
        first_candidate_state=CandidateState.EXISTS_BUT_REJECTS_FILL,
        second_candidate_state=CandidateState.EXISTS_AND_ACCEPTS_FILL,
    )
    candidates = [
        make_candidate(strategy="role", score=0.9),
        make_candidate(strategy="label", score=0.7),
    ]
    resolver = LocatorResolver(page)
    executor = StepExecutor(resolver, page)

    # Act
    result = executor.fill(intent="Renda mensal", candidates=candidates, value="R$ 1.000,00")

    # Assert
    assert result.status == StepResult.PASSED
    assert result.winning_candidate_idx == 1
    assert resolver.winning_idx_cache["Renda mensal"] == 1
```

**Regras**:
- Comentários `# Arrange`, `# Act`, `# Assert` **obrigatórios** para testes acima de 5 linhas de corpo.
- Uma única ação em `# Act`. Se precisa de 2 ações, é 2 testes.
- Múltiplos asserts permitidos em `# Assert` **apenas se testam a mesma unidade de comportamento**. Estado do sistema após ação = OK. "Ação executou e emitiu span e atualizou cache" = OK.
- Setup complexo mora em fixtures. Não copie 20 linhas de setup em 6 testes.

---

## 5. Fixtures — hierarquia + escopo

### 5.1 Escopo por camada
- `tests/conftest.py` — fixtures globais (`tmp_recording_dir`, `sample_semantic_test_case`, `mock_azure_openai`).
- `tests/unit/conftest.py` — mocks: `mock_page`, `mock_resolver`, `mock_curator`.
- `tests/integration/conftest.py` — componentes reais montados: `real_resolver_with_mock_page`, `real_curator_no_llm`.
- `tests/e2e/conftest.py` — Playwright real: `browser_page`, `serve_fixture_html`.

### 5.2 Scope pytest
- `function` (default) — recriado a cada teste. Use para state mutável.
- `class` — compartilhado dentro de classe. Use quando setup caro mas testes não mudam state.
- `module` — arquivo inteiro. Use para read-only fixtures (fixture HTML paths).
- `session` — projeto inteiro. Use para servidor HTTP dev, browser launched.

### 5.3 Nomeação de fixture
`<what_it_provides>` no singular. Sem prefixo `fixture_`, sem sufixo `_fixture`.

- ✅ `mock_page`, `sample_recording_dir`, `curator_with_real_catalog`
- ❌ `page_fixture`, `create_mock_page`, `get_recording_dir`

### 5.4 Factories vs fixtures
- **Fixture**: retorna instância pronta. Um por teste.
- **Factory**: função que gera instâncias parametrizadas. Chamada explicitamente no teste.

Use factory quando teste precisa customizar. Use fixture quando estado é constante.

```python
# tests/factories/locator_candidate.py
def make_candidate(strategy="role", score=0.9, selector=None, **overrides):
    """Factory para LocatorCandidate. Defaults sensatos, override livre."""
    call = f'get_by_role("{strategy}", name="Test")'
    return {
        "strategy": strategy,
        "playwright_call": call,
        "selector": selector or f'page.{call}',
        "score": score,
        **overrides,
    }
```

Uso:
```python
def test_...(self):
    # Arrange
    good = make_candidate(score=0.9)
    bad = make_candidate(score=0.5, selector="body")  # dangerous
```

---

## 6. Parametrize para edge cases

Casos-tabela: usar `pytest.mark.parametrize` com `ids=` explícito.

```python
@pytest.mark.parametrize(
    "expected,actual,mask_type,should_pass",
    [
        ("1000", "R$ 1.000,00", "currency", True),   # magnitude match
        ("1000", "R$ 1,00", "currency", False),      # magnitude mismatch (bug atual!)
        ("1000", "", "currency", False),             # empty
        ("01/01/1980", "01/01/1980", "date", True),
        ("01/01/1980", "1980-01-01", "date", True),  # ISO variant
        ("01/01/1980", "01/02/1980", "date", False),
    ],
    ids=[
        "currency_magnitude_match",
        "currency_magnitude_mismatch_gap08_regression",
        "currency_empty_rejects",
        "date_br_format_match",
        "date_iso_normalization_match",
        "date_mismatch_rejects",
    ],
)
def test_mask_postcondition_when_masked_value_then_compares_magnitude(
    expected, actual, mask_type, should_pass
):
    # Arrange
    post = StepPostcondition(...)

    # Act
    result = post.evaluate_fill(
        expected=expected, actual=actual, mask_hint=mask_type
    )

    # Assert
    assert result.passed == should_pass
```

**Regras**:
- `ids=` obrigatório. `parametrize` sem `ids` gera `test_x[expected0-actual0]` que ninguém consegue debugar.
- Cada caso é uma linha. Testes com > 12 casos param, quebre em 2 funções por eixo.
- Regressões conhecidas ganham sufixo `_gapNN_regression` ou `_bug_YYYY_MM_DD_regression`.

---

## 7. Marks pytest (obrigatório)

Definir em `pytest.ini`:

```ini
[pytest]
markers =
    unit: fast (<10ms), no I/O, no browser
    integration: multi-component, real objects, no browser (10-500ms)
    e2e: browser real, fixture HTML servida (1-30s)
    regression: cobre bug conhecido — não deletar sem discussão
    slow: >1s — pulados por default em CI local
    critical: bloqueia release — sempre roda antes de merge
    known_bug: teste que documenta bug ainda não corrigido (xfail com reason)
```

Uso obrigatório:
```python
@pytest.mark.unit
@pytest.mark.critical
def test_resolver_when_first_candidate_fill_fails_then_tries_next():
    ...

@pytest.mark.integration
@pytest.mark.regression
def test_gap01_regression_resolver_falls_through_execution_failure():
    ...

@pytest.mark.e2e
@pytest.mark.slow
def test_bug_detection_flags_500_response_during_recording():
    ...
```

Comandos:
```bash
pytest -m unit                  # rápido, roda a cada save
pytest -m "unit or integration" # roda em pre-commit
pytest -m critical              # bloqueia merge
pytest -m "not slow"            # CI PR
pytest                          # tudo, CI nightly
```

---

## 8. Testes de INTEGRAÇÃO — regras específicas

**Objetivo**: verificar que componentes reais conversam corretamente. Não é E2E (sem browser). Não é unit (mais de um componente).

**Padrão**:
```python
# tests/integration/test_pipeline_resolve_to_execute_with_retry.py

@pytest.mark.integration
def test_resolver_and_executor_retry_next_candidate_on_fill_failure():
    """Integração: resolver retorna candidate #0, executor chama fill,
    fill raise, executor pede candidate #1 ao resolver via exclude_indices.
    Cache in-memory promove #1 para próximas resoluções do mesmo intent.
    """
    # Arrange
    page = mock_page_with_material_hidden_input()  # tests/helpers/mock_page.py
    resolver = LocatorResolver(page)
    executor = StepExecutor(resolver)
    candidates = [
        make_candidate(strategy="role", score=0.9, selector="input[name=renda]"),
        make_candidate(strategy="label", score=0.85, selector="label:has-text('Renda')"),
    ]

    # Act
    outcome = executor.fill(intent="Renda mensal", candidates=candidates, value="1000")

    # Assert — camada resolver
    assert resolver.winning_idx_cache["Renda mensal"] == 1
    # Assert — camada executor
    assert outcome.status == StepResult.PASSED
    assert outcome.attempted_indices == [0, 1]
    # Assert — persistência
    assert resolver.sqlite.last_recorded_success.candidate_selector == candidates[1]["selector"]
```

**Regras**:
- Um teste de integração cobre **uma jornada específica** de dado atravessando >= 2 camadas.
- Nome do arquivo: `test_pipeline_<start>_to_<end>.py` ou `test_<component>_and_<component>_<behavior>.py`.
- Fixtures dessa camada expõem **objetos reais** conectados, não mocks profundos.

---

## 9. Testes E2E — regras específicas

**Objetivo**: verificar que TestForge funciona ponta a ponta com browser real e HTML controlado.

**Regras**:
- HTML fixtures em `tests/e2e/pages/`, servidas por `serve_fixture_html` (fixture session-scope que sobe http.server em porta livre).
- Nunca depender de site externo. Nunca `localhost:8765` implícito — usar fixture.
- Toda navegação, click, fill vai por `browser_page` fixture.
- Screenshots on fail: `pytest --screenshot=only-on-failure` no `pytest.ini` addopts.
- Trace obrigatório em `critical`: `pytest --tracing=retain-on-failure`.

Exemplo:
```python
@pytest.mark.e2e
@pytest.mark.critical
def test_recording_captures_currency_mask_intent(browser_page, serve_fixture_html, tmp_recording_dir):
    # Arrange
    url = serve_fixture_html("currency_mask_form.html")
    recorder = RecorderController(browser_page, recording_dir=tmp_recording_dir)

    # Act
    recorder.start()
    browser_page.goto(url)
    browser_page.locator("input[name=amount]").fill("1000000")
    recorder.stop()

    # Assert — raw event capturado
    raw = load_jsonl(tmp_recording_dir / "raw_events.jsonl")
    fill_events = [e for e in raw if e["type"] == "fill"]
    assert len(fill_events) == 1
    assert fill_events[0]["raw_value"] == "1000000"
    assert fill_events[0]["displayed_value"] == "R$ 1.000.000,00"
```

---

## 10. Testes forçando erro (edge cases + adversarial)

Toda fase do plano exige teste que **prova que a antiga implementação quebra**. Regressão-gate.

```python
# tests/regression/resolver/test_gap01_first_candidate_exists_but_fill_fails.py

@pytest.mark.regression
@pytest.mark.critical
def test_gap01_resolver_should_fall_to_next_candidate_when_first_fill_rejects():
    """Regressão GAP-01: pré-fix, resolver retornava candidate[0] mesmo
    quando fill rejeitava. Este teste **falha** contra implementação
    antiga; passa contra a fix (retry-with-next-candidate).

    Bug original: rodadas SIOPI 15b-e, hotfix22 — 14-64% assert_hit_rate.
    """
    # Arrange
    page = MagicMock()
    good_locator = MagicMock()
    good_locator.count.return_value = 1
    good_locator.fill = MagicMock()  # aceita
    bad_locator = MagicMock()
    bad_locator.count.return_value = 1  # EXISTE
    bad_locator.fill.side_effect = TimeoutError("fill timeout — material hidden")

    def route_locator(strategy, **kwargs):
        return bad_locator if strategy == "role" else good_locator

    page.get_by_role.side_effect = lambda **k: route_locator("role", **k)
    page.get_by_label.side_effect = lambda t: route_locator("label", t=t)

    resolver = LocatorResolver(page)
    executor = StepExecutor(resolver)

    candidates = [
        make_candidate(strategy="role", playwright_call='get_by_role("textbox", name="Renda")', score=0.9),
        make_candidate(strategy="label", playwright_call='get_by_label("Renda")', score=0.85),
    ]

    # Act
    result = executor.fill(intent="Renda mensal", candidates=candidates, value="1000")

    # Assert
    assert result.status == StepResult.PASSED, (
        "Pré-fix: resolver retornava candidate[0] (existe), executor chamava "
        "fill que raise, escalava direto para healing. Fix: retry candidate[1]."
    )
    assert result.winning_candidate_idx == 1
    good_locator.fill.assert_called_once_with("1000")
```

**Regras**:
- Docstring cita o bug original + condição de falha do estado antigo.
- Nomeação inclui `regression` ou `gapNN`.
- Assert message no `assert ...` explica **o que deveria acontecer** — a próxima LLM vai ler isso e não a memória histórica.

### Adversarial edge cases obrigatórios por camada

**Resolver**:
- `test_resolve_when_zero_candidates_then_raises_locator_not_found`
- `test_resolve_when_all_candidates_exist_but_all_actions_fail_then_raises`
- `test_resolve_when_cache_hit_but_page_changed_url_then_invalidates`
- `test_resolve_when_candidate_selector_dangerous_generic_then_skips`

**Curator**:
- `test_curator_when_step_runner_none_then_falls_through_not_passed`
- `test_curator_when_l0_recipe_solution_selector_empty_then_treats_as_js_only`
- `test_curator_when_agent_returns_conf_below_threshold_then_returns_none`
- `test_curator_when_agent_proposal_execution_raises_then_records_failure`

**Recorder / overlay**:
- `test_snapshot_when_page_has_no_input_elements_then_emits_unknown_batch`
- `test_snapshot_when_snapshot_function_throws_then_logs_error_and_emits_synth`
- `test_inline_prompt_when_field_empty_after_zero_keystrokes_then_does_not_prompt`
- `test_inline_prompt_when_field_receives_paste_only_then_captures_value`

**Normalizer**:
- `test_build_target_when_no_identifiers_match_then_synthesizes_css_fallback`
- `test_ir_dedupe_when_entry_has_empty_key_then_logs_dropped_reason`
- `test_convert_step_when_click_has_no_candidates_then_records_blind_spot`

---

## 11. Testes de contrato / invariantes

**Objetivo**: garantir que estruturas de dados atravessando camadas mantêm shape esperado.

```python
# tests/contract/test_curator_outcome_invariants.py

@pytest.mark.unit
def test_curation_outcome_passed_step_requires_proposal():
    """Invariante: outcome status PASSED_STEP nunca vem sem proposal
    (regressão pré-GAP-02: retornava PASSED_STEP com proposal=None)."""
    for status in [ProgressResult.PASSED_STEP]:
        outcome = CurationOutcome(status=status, proposal=None)
        errors = outcome.validate_invariants()
        assert errors == ["passed_step_requires_proposal"]
```

Adicionar método `.validate_invariants() -> list[str]` em dataclasses críticas. Teste roda para todas as combinações válidas.

---

## 12. Testes do CÓDIGO GERADO por TestForge

TestForge emite arquivos `semantic_tests/ST-<name>/test_st_<name>.py` — código Playwright que **o cliente** executa. Padrão para esse output:

### 12.1 Estrutura do teste gerado
```python
# semantic_tests/ST-simulacao-completa/test_st_simulacao_completa.py
"""
Test gerado por TestForge em 2026-07-02T14:00:00Z.
Recording: recordings/simulacao-completa/
Intent SPEC: semantic_tests/ST-simulacao-completa/semantic_steps.jsonl

Manutenção:
- Modificar valores em test_data.json (não recompilar).
- Modificar seletores: regravar via `testforge record ... --resume`.
- Bug conhecido na aplicação testada: veja pytest.mark.known_bug em cada teste.
"""
import pytest
from playwright.sync_api import Page, expect
from testforge.runtime import step
from pathlib import Path

CANDIDATES_DIR = Path(__file__).parent / "candidates"
TEST_DATA = Path(__file__).parent / "test_data.json"


@pytest.fixture(scope="module")
def test_data():
    import json
    return json.loads(TEST_DATA.read_text())


@pytest.mark.e2e
@pytest.mark.generated
class TestSimulacaoCompleta:
    """Cenário: preencher formulário de simulação de crédito imobiliário."""

    def test_navega_para_pagina_de_simulacao(self, page: Page):
        # Arrange
        page.goto(test_data["fields"]["start_url"])
        # Act + Assert (encapsulado)
        step.click(page, intent="Iniciar simulação",
                   candidates_file=str(CANDIDATES_DIR / "step_001.json"))

    def test_preenche_renda_mensal(self, page: Page, test_data):
        # Arrange
        expected = test_data["fields"]["renda_mensal"]  # "R$ 10.000,00"
        # Act
        step.fill(page, intent="Renda mensal",
                  value=expected,
                  candidates_file=str(CANDIDATES_DIR / "step_005.json"))
        # Assert
        expect(page.locator("input[name=renda]")).to_have_value(expected)

    @pytest.mark.known_bug(
        bug_id="BUG-BANK-2026-07-01",
        detected_during_recording=True,
        description="Botão Calcular não desabilita durante submit — permite duplo click. "
                    "Comportamento esperado: disable até response chegar."
    )
    def test_clica_calcular(self, page: Page):
        # Arrange — intentionally left blank; recording context in candidates_file
        # Act
        step.click(page, intent="Calcular",
                   candidates_file=str(CANDIDATES_DIR / "step_012.json"))
```

**Regras**:
- Todo teste gerado é `class TestXxx` + métodos `test_yyy`.
- Método por passo lógico do usuário — não `test_full_flow` monolítico.
- `test_data` fixture module-scoped lê `test_data.json`. Nunca hardcode.
- `expect(...).to_have_value(...)` explícito onde faz sentido — não confiar só em ausência de exception.
- Comentários `# Arrange`, `# Act`, `# Assert` **também obrigatórios em código gerado**.
- Mark `@pytest.mark.generated` sempre.
- Mark `@pytest.mark.known_bug(...)` quando recorder detectou bug (Fase 7).

### 12.2 Compilador (PlaywrightCompiler) — obrigações
- Emitir docstring de módulo com timestamp + path do recording.
- Emitir docstring de classe com resumo do cenário (extraído do gherkin se `--diagnostic-mode`).
- Emitir docstring de método com nome legível derivado do `intent`.
- Emitir bloco Arrange/Act/Assert visível.
- Nunca inline value do form direto no código — sempre via `test_data.json`.

---

## 13. Coverage & CI

### 13.1 Metas
- `pytest -m "unit or contract" --cov=src/testforge --cov-fail-under=85`
- `pytest -m integration --cov-append --cov-fail-under=70`
- `pytest -m e2e` — sem exigência de cobertura, mas obrigatório passar para merge em `critical`.

### 13.2 Ordem CI
1. Lint (`ruff`, `mypy`).
2. `pytest -m unit` (< 30s total).
3. `pytest -m integration` (< 3min).
4. `pytest -m critical`.
5. `pytest -m e2e` (paralelizar por diretório).

Falha em qualquer bloqueia próximo. Bloco 3 e 4 podem paralelizar após 2.

### 13.3 Nightly
- `pytest` sem `-m` (roda tudo, inclui `slow`).
- Rec base SIOPI + hotfix22 + hotfix27 executam via `testforge run-incremental` e reportam `assert_hit_rate`.

---

## 14. Anti-padrões (rejected em code review)

- ❌ `time.sleep(1)` em teste de unit ou integration. Se timing é essencial, usar `page.wait_for_selector` ou fixture com poll+timeout.
- ❌ `try/except` engolindo assert. Se teste espera exception, `pytest.raises`.
- ❌ Múltiplos cenários em uma função — quebrar via `parametrize`.
- ❌ Assert em fixture. Fixtures **provêm** estado, não validam.
- ❌ Teardown com side effect visível (delete DB, remove arquivo global). Usar `tmp_path` fixture.
- ❌ Mocks profundos (`mock.patch("a.b.c.d")` com 5 níveis). Refatorar código ou usar injeção de dependência.
- ❌ Nome de teste como `test_1`, `test_bug`, `test_new_feature`.
- ❌ Comentário `# TODO: fix this test` sem issue linkada e sem xfail.
- ❌ Legacy `testforge run` reportando 100% — ver `[[project-run-legacy-decommission]]`. Novos testes E2E de recording usam `run-incremental`.

---

## 15. Referências

- Plano principal: `docs/HEALING-GAPS-PLAN.md`.
- Arquitetura: `docs/ARCHITECTURE-V2.md`.
- Contrato no-regrave (não regravar rec existente para testar fix): memória `[[feedback-no-regrave]]`.
- Bugs históricos: `bug_lab/README.md` + `bug_lab/TEST-CASES.md`.
