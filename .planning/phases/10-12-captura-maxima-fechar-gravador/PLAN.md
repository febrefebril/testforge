---
phase: 10-12-captura-maxima-fechar-gravador
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/testforge/runner/incremental_runner.py
  - src/testforge/semantic/recording_normalizer.py
  - src/testforge/cli/app.py
  - src/testforge/metrics/pilot_metrics.py
  - docs/GUIA_TESTER.md
autonomous: true
requirements:
  - B1
  - B2
  - C1
  - C2
  - D1

must_haves:
  truths:
    - "Step 24 (assert #body) no simulador-credito6 termina como SKIP, nao healing_rejected"
    - "Steps 3, 4, 21, 22 (radio buttons Angular Material) passam como [OK] sem healing"
    - "testforge record --pilot-mode produz relatorio de readiness com contagem real de steps"
    - "testforge compile --check imprime '% campos auto-resolvidos: N%'"
    - "docs/GUIA_TESTER.md existe com instrucoes de instalacao, gravacao, atalhos e envio"
  artifacts:
    - path: "src/testforge/runner/incremental_runner.py"
      provides: "Skip early para steps com selector body/html ou skip_reason preenchido"
    - path: "src/testforge/semantic/recording_normalizer.py"
      provides: "Candidato mat-radio-button:has-text() com score 0.92 para radio Angular Material"
    - path: "src/testforge/cli/app.py"
      provides: "_run_post_recording_validation compila + executa incremental headless com step_results reais"
    - path: "src/testforge/metrics/pilot_metrics.py"
      provides: "compute_auto_resolution_rate() retorna percentual de campos auto-resolvidos"
    - path: "docs/GUIA_TESTER.md"
      provides: "Guia de 1 pagina para testers: instalar, gravar, enviar"
  key_links:
    - from: "src/testforge/cli/app.py (_run_post_recording_validation)"
      to: "src/testforge/runner/incremental_runner.py (IncrementalRunner)"
      via: "IncrementalRunner instanciado com headless=True, stop_on_failure=False, no_healing=True"
    - from: "src/testforge/cli/app.py (cmd_compile --check)"
      to: "src/testforge/metrics/pilot_metrics.py (compute_auto_resolution_rate)"
      via: "PilotMetrics.compute_auto_resolution_rate(report) chamado apos IntentCompletenessChecker"
---

<objective>
Estabilizar o gravador para distribuicao ao time de testers. Cinco correcoes independentes:
B1 skip de assert #body no runner, B2 selector Angular Material radio button no normalizer,
C1 execucao incremental headless real no pilot-mode, C2 metrica de campos auto-resolvidos
no compile --check, D1 guia do tester.

Purpose: Fechar o gravador para modificacoes — apos essa fase o recorder congela e o time
pode gravar, enviar recordings/, e a engenharia itera apenas nos modulos downstream.

Output: simulador-credito6 atinge 12 passed / 0 healed_validated / 0 healing_rejected / 12 skipped.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/phases/10-12-captura-maxima-fechar-gravador/CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>P1 — B1: Skip assert steps com selector body/html no IncrementalRunner</name>
  <files>src/testforge/runner/incremental_runner.py</files>
  <action>
No inicio de `_run_one_step()` (antes de instanciar `IncrementalStepResult`), adicionar
um bloco de early-return que produz status "skipped" quando o step deve ser ignorado por
razao de seguranca de selector.

Duas condicoes disparam o skip (qualquer uma basta):
1. `getattr(step, "skip_reason", "")` e nao-vazio — o compiler/normalizer ja marcou o step.
2. O step tem action=="assert" E o selector primario (primeiro candidato em `step.target.candidates`)
   e "body", "#body", "html" ou "xpath=/html/body" (comparacao case-insensitive apos strip).

Logica de implementacao em `_run_one_step`:
- Antes de criar `IncrementalStepResult`, extrair `skip_reason = getattr(step, "skip_reason", "")`.
- Se nao tiver skip_reason mas `step.action == "assert"`, checar o primeiro candidato:
  `sel = (step.target.candidates[0].selector if step.target and step.target.candidates else "")`.
  Se `sel.strip().lower()` in `{"body", "#body", "html", "xpath=/html/body", "xpath=//body"}`,
  setar `skip_reason = "assert_on_body_element_skipped"`.
- Se `skip_reason` for nao-vazio apos essa logica: criar o `IncrementalStepResult` normalmente
  mas imediatamente setar `result.status = "skipped"`, `result.skip_reason = skip_reason`,
  `result.duration_ms = 0` e retornar. Nao chamar `_heal_failed_step`, nao chamar
  `step_executor.execute`, nao chamar `evidence_collector`.

Nao alterar `_DANGEROUS_LOCATORS`, `_is_dangerously_generic`, nem nenhum outro metodo.
O set `_DANGEROUS_LOCATORS` ja tem "body" e "html" mas e usado apenas para rejeitar
proposals de healing — nao interfere.

Referencia: step 24 do simulador-credito6 tem action="assert" com selector derivado de
`document.body` — apos B1 deve aparecer como SKIP no relatorio.
  </action>
  <verify>
    <automated>cd /home/febre/Projetos/testforge-v1-claude/testforge && python -c "
from testforge.runner.incremental_runner import IncrementalRunner
from unittest.mock import MagicMock
runner = IncrementalRunner.__new__(IncrementalRunner)
runner.evidence_collector = None
runner.step_executor = None
runner.precondition_validator = None
runner.postcondition_validator = None
runner.failed_step_indices = set()
runner.steps = []
runner.ui = MagicMock()
runner.page = MagicMock()

# Simula step de assert com selector body
step = MagicMock()
step.action = 'assert'
step.skip_reason = ''
cand = MagicMock(); cand.selector = 'body'
step.target = MagicMock(); step.target.candidates = [cand]
step.value = ''

result = runner._run_one_step(0, step)
assert result.status == 'skipped', f'Esperado skipped, got {result.status}'
print('B1 OK: assert body -> skipped')
"
</automated>
  </verify>
  <done>
    `_run_one_step` retorna status="skipped" para steps com skip_reason preenchido OU
    com action=="assert" e selector em {body, #body, html, xpath=/html/body}.
    Step 24 do simulador-credito6 passa como SKIP no run-incremental.
  </done>
</task>

<task type="auto">
  <name>P2 — B2: Angular Material radio button selector no RecordingNormalizer</name>
  <files>src/testforge/semantic/recording_normalizer.py</files>
  <action>
Em `_build_target()` (linha ~1060), apos o bloco que trata `label + id` gerando
`label[for="{el_id}"]`, adicionar deteccao especifica para radio buttons Angular Material.

A condicao de ativacao: `target_data.get("id", "").startswith("mat-radio-")`.
Quando verdadeira, o selector `label[for="{el_id}"]` nao funciona porque Angular Material
nao renderiza o atributo `for` nativo em radio buttons.

Acoes:
1. Se o `label[for="mat-radio-N-input"]` ja foi adicionado (pelo bloco `label + id` acima),
   remover esse candidato da lista `candidates` (e nao adicionado, pois a condicao
   `target_data.get("label") and target_data.get("id")` continua valida — ajustar a ordem
   de insercao ou usar uma flag para suprimi-lo).
   Alternativa mais simples: rebaixar o score do candidato label[for] adicionado logo acima
   para 0.30 quando `el_id.startswith("mat-radio-")`, modificando o score ao inves de
   remover o candidato.

2. Adicionar um candidato de alta prioridade (score 0.92) usando `mat-radio-button`:
   - Se `target_data.get("label")`:
     `mat-radio-button:has-text("{label}")` com score 0.92 e hint "Angular Material radio by label".
   - Se `target_data.get("accessible_name")` (alternativa quando label ausente):
     `mat-radio-button:has-text("{accessible_name}")` com score 0.88.
   - Adicionar esse candidato ANTES dos demais candidatos gerados para o mesmo elemento
     (use `candidates.insert(0, ...)` ou adicione antes do bloco de role/label).

3. O candidato `mat-radio-button:has-text()` deve ser inserido SOMENTE quando
   `el_id.startswith("mat-radio-")` — nao aplicar a outros elementos.

Nao alterar nenhuma logica fora do escopo de `_build_target()`. Nao modificar tratamento
de `select`, `checkbox`, `role`, ou qualquer outro tipo de elemento.

Referencia: steps 3, 4, 21, 22 do simulador-credito6 tem element_id como "mat-radio-1-input",
"mat-radio-2-input", etc. O selector atual `label[for="mat-radio-1-input"]` nao bate no DOM
Angular Material — o candidato `mat-radio-button:has-text("Sim")` resolve.
  </action>
  <verify>
    <automated>cd /home/febre/Projetos/testforge-v1-claude/testforge && python -c "
from testforge.semantic.recording_normalizer import RecordingNormalizer
n = RecordingNormalizer()
target = n._build_target({
    'id': 'mat-radio-1-input',
    'label': 'Sim',
    'tag': 'input',
    'attributes': {'type': 'radio'},
})
sels = [c.selector for c in target.candidates]
scores = {c.selector: c.score for c in target.candidates}
print('Candidatos:', sels)
mat_sel = 'mat-radio-button:has-text(\"Sim\")'
assert mat_sel in sels, f'Candidato mat-radio-button ausente. Got: {sels}'
assert scores[mat_sel] >= 0.90, f'Score insuficiente: {scores[mat_sel]}'
# Deve ser o candidato de maior score
top = max(target.candidates, key=lambda c: c.score)
assert top.selector == mat_sel, f'Top candidato nao e mat-radio-button: {top.selector}'
print('B2 OK: mat-radio-button:has-text(Sim) score', scores[mat_sel])
"
</automated>
  </verify>
  <done>
    `_build_target()` com `id=mat-radio-N-input` e `label=X` retorna
    `mat-radio-button:has-text("X")` como candidato de maior score (>=0.90).
    Steps 3, 4, 21, 22 do simulador-credito6 passam como [OK] sem healing.
  </done>
</task>

<task type="auto">
  <name>P3 — C1: pilot-mode executa IncrementalRunner headless e passa step_results reais ao gate</name>
  <files>src/testforge/cli/app.py</files>
  <action>
Modificar `_run_post_recording_validation()` (linha ~170) para compilar o script e rodar
`IncrementalRunner` em modo headless antes de chamar `RecordingReadinessGate.evaluate()`.

Implementacao dentro de `_run_post_recording_validation`:

1. Verificar se `getattr(args, 'pilot_mode', False)` e True. Se nao for, manter
   o comportamento atual (step_results=[] com warning).

2. Se pilot_mode=True:
   a. Compilar: usar `PlaywrightCompiler` para gerar o script no diretorio temporario.
      Importar `PlaywrightCompiler` e `RecordingNormalizer` localmente (ja estao disponiveis
      no modulo via imports no topo do arquivo).
      Reutilizar o `stc` ja recebido como parametro (nao renormalizar).
      `out_dir = os.path.join(rec_dir, "_pilot_tmp")`
      `script_path = PlaywrightCompiler().compile(stc, out_dir)`

   b. Rodar incremental headless:
      ```
      from testforge.runner.incremental_runner import IncrementalRunner
      runner = IncrementalRunner(
          script_path=script_path,
          headless=True,
          timeout=90,
          stop_on_failure=False,
          no_healing=True,
          capture=False,
          output_root=os.path.join(rec_dir, "_pilot_runs"),
      )
      report = runner.run()
      step_results = runner.step_results
      ```

   c. Tratar excecoes: envolver em try/except. Se falhar, imprimir aviso e usar
      `step_results = []` com print indicando que pilot run falhou.

   d. Passar `step_results` reais para `gate.evaluate(...)` no lugar do `[]` atual.

3. Nao alterar a assinatura de `_run_post_recording_validation` (recebe rec_dir, rid, args, stc, completeness_report).

4. Nao alterar `cmd_record` — ela ja chama `_run_post_recording_validation` quando pilot_mode=True
   (linha ~338: `run_validation = validate_before_ready or pilot_mode`).

Importacoes necessarias ja estao no arquivo (`PlaywrightCompiler`, `RecordingNormalizer`).
`IncrementalRunner` deve ser importado localmente dentro do bloco pilot_mode para evitar
import circular no nivel de modulo.
  </action>
  <verify>
    <automated>cd /home/febre/Projetos/testforge-v1-claude/testforge && python -c "
import ast, sys
src = open('src/testforge/cli/app.py').read()
tree = ast.parse(src)
# Checar que IncrementalRunner aparece na funcao _run_post_recording_validation
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == '_run_post_recording_validation':
        func_src = ast.get_source_segment(src, node)
        assert 'IncrementalRunner' in func_src, 'IncrementalRunner nao encontrado em _run_post_recording_validation'
        assert 'pilot_mode' in func_src, 'pilot_mode check ausente'
        assert 'step_results = runner.step_results' in func_src or 'step_results=runner.step_results' in func_src or 'runner.step_results' in func_src, 'step_results reais nao coletados'
        print('C1 OK: _run_post_recording_validation usa IncrementalRunner headless')
        sys.exit(0)
print('ERRO: funcao nao encontrada')
sys.exit(1)
"
</automated>
  </verify>
  <done>
    `testforge record --pilot-mode URL --name X` produz relatorio de readiness com
    contagem real de steps passed/healed/failed (nao mais 0/0/0).
    A funcao _run_post_recording_validation compila o script, roda IncrementalRunner
    com headless=True, no_healing=True, stop_on_failure=False, e passa runner.step_results
    para RecordingReadinessGate.evaluate().
  </done>
</task>

<task type="auto">
  <name>P4 — C2: Wire pilot_metrics ao compile --check</name>
  <files>src/testforge/metrics/pilot_metrics.py, src/testforge/cli/app.py</files>
  <action>
Adicionar metodo `compute_auto_resolution_rate()` em `PilotMetrics` (pilot_metrics.py)
e chamar esse metodo em `cmd_compile` apos o bloco `--check` (app.py).

**Em pilot_metrics.py — adicionar metodo a classe PilotMetrics:**

```
def compute_auto_resolution_rate(self, completeness_report=None) -> float:
    """Retorna fracao de campos resolvidos automaticamente (0.0 a 1.0).
    
    Se completeness_report fornecido, usa dados diretos dele.
    Senao, usa campos acumulados em self (fields_auto_resolved / total).
    """
    if completeness_report is not None:
        total = getattr(completeness_report, 'total_count', 0) or 0
        resolved = getattr(completeness_report, 'resolved_count', 0) or 0
        # resolved_count inclui resolved + resolved_with_warning — ambos sao auto-resolvidos
        if total == 0:
            return 1.0
        return round(resolved / total, 4)
    total = self.fields_auto_resolved + self.fields_user_supplied + self.fields_missing
    if total == 0:
        return 1.0
    return round(self.fields_auto_resolved / total, 4)
```

**Em app.py — em cmd_compile, apos o bloco `if getattr(args, 'check', False):` que ja existe (linha ~431-450):**

Adicionar ao final desse bloco (dentro do `if check`), apos os prints existentes:

```python
from testforge.metrics.pilot_metrics import PilotMetrics as _PilotMetrics
_pm = _PilotMetrics()
rate = _pm.compute_auto_resolution_rate(report)
print(f"[TestForge] % campos auto-resolvidos: {rate:.0%}")
```

O objeto `report` e o `IntentCompletenessReport` retornado por `checker.check_steps()`
— ele tem `resolved_count` e `total_count` (verificar atributos reais com grep antes
de implementar; se atributos diferem, adaptar o metodo para usar os nomes corretos).

Verificar atributos do report antes de implementar:
`grep -n "resolved_count\|total_count\|missing_count" src/testforge/semantic/intent_completeness.py`

Nao criar arquivo novo. Nao alterar PilotMetrics.ingest_recording nem nenhum outro metodo.
  </action>
  <verify>
    <automated>cd /home/febre/Projetos/testforge-v1-claude/testforge && python -c "
from testforge.metrics.pilot_metrics import PilotMetrics
pm = PilotMetrics()
# Teste com mock de report
class FakeReport:
    resolved_count = 8
    total_count = 10
rate = pm.compute_auto_resolution_rate(FakeReport())
assert rate == 0.8, f'Esperado 0.8, got {rate}'
print(f'C2 OK: compute_auto_resolution_rate = {rate:.0%}')

# Teste sem report (usa campos internos)
pm2 = PilotMetrics()
pm2.fields_auto_resolved = 6
pm2.fields_missing = 4
rate2 = pm2.compute_auto_resolution_rate()
assert rate2 == 0.6, f'Esperado 0.6, got {rate2}'
print(f'C2 OK: sem report = {rate2:.0%}')
"
</automated>
  </verify>
  <done>
    `testforge compile --check recordings/X/` imprime linha
    "[TestForge] % campos auto-resolvidos: N%" onde N e a fracao de campos com
    resolved_count / total_count do IntentCompletenessReport.
    PilotMetrics.compute_auto_resolution_rate() existe e funciona com e sem report.
  </done>
</task>

<task type="auto">
  <name>P5 — D1: Guia do Tester (docs/GUIA_TESTER.md)</name>
  <files>docs/GUIA_TESTER.md</files>
  <action>
Criar arquivo `docs/GUIA_TESTER.md` com conteudo objetivo para testers nao-tecnicos.
O arquivo deve cobrir exatamente os topicos definidos no CONTEXT.md:

1. Como instalar: instrucao `pip install testforge` (ou caminho alternativo se o
   pacote ainda nao esta no PyPI: `pip install -e .` a partir do repositorio).
   Mencionar prerequisito: Python 3.10+ e Playwright (`playwright install chromium`).

2. Como gravar: comando completo `testforge record --app CAIXA URL --name nome`.
   Exemplo real com URL do Simulador de Habitacao.
   Mencionar que o navegador abre automaticamente.

3. Atalhos durante a gravacao (tabela simples):
   - Shift+S: Parar gravacao e salvar
   - Shift+A: Marcar assert (verificar elemento na tela)
   - Shift+P: Pausar/retomar gravacao

4. Como enviar: zipar a pasta `recordings/{nome}/` completa e enviar para o time de engenharia.
   Instrucao de como zipar no terminal e no explorador de arquivos.

5. O que NAO fazer (lista curta):
   - Nao editar nenhum arquivo dentro de `recordings/{nome}/`
   - Nao renomear a pasta da gravacao
   - Nao gravar com VPN ativa (pode mascarar URLs internas)
   - Nao fechar o navegador manualmente — sempre usar Shift+S

Formato: Markdown simples, sem emojis excessivos, linguagem direta.
Maximo 1 pagina impressa (aprox 60 linhas de conteudo).
Nao incluir detalhes tecnicos de implementacao ou arquitetura interna.
  </action>
  <verify>
    <automated>cd /home/febre/Projetos/testforge-v1-claude/testforge && python -c "
from pathlib import Path
p = Path('docs/GUIA_TESTER.md')
assert p.exists(), 'docs/GUIA_TESTER.md nao encontrado'
content = p.read_text()
checks = [
    ('pip install', 'instrucao de instalacao'),
    ('testforge record', 'comando de gravacao'),
    ('Shift+S', 'atalho parar'),
    ('Shift+A', 'atalho assert'),
    ('Shift+P', 'atalho pausar'),
    ('recordings/', 'instrucao de envio'),
    ('NAO', 'secao do que nao fazer'),
]
for term, desc in checks:
    assert term in content, f'Ausente: {desc} ({term!r})'
lines = [l for l in content.splitlines() if l.strip()]
assert len(lines) <= 80, f'Arquivo muito longo: {len(lines)} linhas (max 80)'
print(f'D1 OK: GUIA_TESTER.md valido ({len(lines)} linhas)')
"
</automated>
  </verify>
  <done>
    `docs/GUIA_TESTER.md` existe com instrucoes de instalacao, gravacao, atalhos
    (Shift+S/A/P), envio e proibicoes. Maximo 80 linhas uteis.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI -> IncrementalRunner (pilot-mode) | Script compilado e executado headless com dados da gravacao |
| recordings/ dir | Arquivos JSON gravados pelo overlay — conteudo vem do browser do usuario |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-10-01 | Tampering | recordings/ JSON input | accept | Dados sao gravados localmente pelo proprio tester — nao ha superficie externa |
| T-10-02 | Denial of Service | pilot-mode IncrementalRunner | mitigate | timeout=90s hardcoded no IncrementalRunner instanciado em C1; processo filho nao pode travar o CLI indefinidamente |
| T-10-03 | Information Disclosure | _pilot_tmp/ e _pilot_runs/ | accept | Diretorios temporarios dentro de recordings/ — mesma confidencialidade dos dados ja gravados |
</threat_model>

<verification>
Apos executar todos os 5 planos, verificar o resultado esperado no simulador-credito6:

```bash
cd /home/febre/Projetos/testforge-v1-claude/testforge
testforge compile recordings/simulador-credito6 --check
testforge run-incremental semantic_tests/ST-simulador-credito6/test_script.py
```

Resultado esperado:
- total: 24
- passed: 12
- healed_validated: 0
- healing_rejected: 0
- skipped: 12
</verification>

<success_criteria>
- [ ] P1: `_run_one_step` retorna skipped para assert com selector body/html — step 24 nao aparece como healing_rejected
- [ ] P2: `_build_target` com id=mat-radio-N-input gera candidato mat-radio-button:has-text() com score >=0.90 como top candidato
- [ ] P3: `_run_post_recording_validation` com pilot_mode=True instancia IncrementalRunner headless e passa step_results reais ao gate
- [ ] P4: `testforge compile --check` imprime "% campos auto-resolvidos: N%" — PilotMetrics.compute_auto_resolution_rate() implementado
- [ ] P5: docs/GUIA_TESTER.md existe, cobre instalacao/gravacao/atalhos/envio/proibicoes, <= 80 linhas uteis
</success_criteria>

<output>
Criar `.planning/phases/10-12-captura-maxima-fechar-gravador/10-01-SUMMARY.md` quando concluido.
</output>
