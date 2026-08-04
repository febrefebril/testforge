
# P0.2 — Golden recordings e harness de regressão

## Suposição segura adotada

O arquivo `todas_gravacoes.txt` foi gerado com o perfil `diag`: os `raw_events.jsonl` e vários dumps DOM/AX aparecem como *stubs* (conteúdo bruto omitido). Para não inventar segredos nem afirmar equivalência byte a byte com arquivos indisponíveis, as fixtures deste incremento são **projeções mínimas, sanitizadas e determinísticas** das famílias observadas. Antes do merge, o gate DES deve substituir ou complementar essas projeções com exportações sanitizadas feitas a partir das gravações originais completas.

## Arquivos adicionados e motivo

- `tests/test_golden_regression.py`: harness parametrizado; compara `load`, `dedup`, `compact`, `audit` e `compile_v2`; verifica ausência aparente de segredos e imutabilidade de assertions.
- `tests/golden/regenerate_snapshots.py`: regeneração deliberada; nunca é executada automaticamente pelo teste.
- `tests/golden/<caso>/case.json`: parâmetros estáveis do caso.
- `tests/golden/<caso>/raw_events.jsonl`: entrada mínima sanitizada.
- `tests/golden/<caso>/steps.jsonl`: assertions/oráculos preservados.
- `tests/golden/<caso>/recording_metadata.json`: metadados mínimos sem identidade, token ou credencial.
- `tests/golden/<caso>/snapshots/{load,dedup,compact,audit,compile_v2}.json`: baseline do código atual.

Nenhum arquivo de produção foi alterado. O incremento é reversível removendo `tests/test_golden_regression.py` e `tests/golden/`.

## Casos selecionados

1. `sso_keycloak_redirect`: SSO/OIDC, redirects e parâmetros dinâmicos mascarados.
2. `angular_material_overlay_noise`: Angular Material, `formControlName` e ruído `#tf-*`.
3. `jsf_primefaces_postback`: JSF/PrimeFaces, IDs com `:` e postback/form values.
4. `simax_datatable_dedup`: DataTable/HTML tradicional, selects repetidos e assert textual.
5. `assertion_immutable`: assertions textual e de estado; prova que o healer não as altera.
6. `captura_incompleta_locator_ausente`: alvo sem sinais, locator repetido e baseline de falha/captura incompleta.

## Executar o baseline

Na pasta que contém o pacote `testforge`:

```powershell
python -m pytest -q testforge/tests/test_golden_regression.py
```

Resultado obtido neste incremento: **13 testes aprovados**.

O harness é offline: não abre navegador e não realiza chamadas de rede/Azure OpenAI.

## Regenerar snapshots conscientemente

Somente quando a mudança semântica for esperada e aprovada:

```powershell
python testforge/tests/golden/regenerate_snapshots.py
python -m pytest -q testforge/tests/test_golden_regression.py
```

Depois:

1. revisar o diff dos cinco snapshots de cada caso;
2. confirmar que assertions mantêm `action="assert"`, tipo e valor esperado;
3. confirmar que um resultado falho não virou sucesso;
4. confirmar que não entraram CPF, matrícula, senha, token, cookie, `state`, `nonce`, `code_verifier` ou `code_challenge` reais;
5. registrar no PR por que cada diferença é intencional.

Nunca use atualização automática de snapshot no CI.

## GATE DE AMBIENTE — DES

### Objetivo

Confirmar que as seis famílias escolhidas representam o comportamento real observado em DES e que o baseline offline detecta regressões sem transformar falha em sucesso.

### Pré-condições

- patch aplicado em branch isolada;
- testes unitários verdes;
- flag/comportamento de produção inalterado (este incremento só adiciona testes);
- QA com acesso autorizado aos fluxos DES equivalentes;
- ferramenta de sanitização/revisão disponível antes de copiar evidências;
- nenhuma credencial real será versionada.

### Passo a passo

1. Executar o harness e guardar o resultado: `python -m pytest -q testforge/tests/test_golden_regression.py`.
2. Em DES, regravar um fluxo equivalente para cada família: SSO, Angular Material com overlay, JSF/PrimeFaces postback, DataTable/selects, assertions e captura incompleta/locator ausente.
3. Comparar, para cada fluxo, a sequência funcional e os efeitos esperados de `load`, `dedup`, `compact`, `audit` e `compile_v2` com o golden correspondente.
4. Verificar especialmente: deduplicação não remove ação necessária; compactação não altera valor; assertion mantém tipo/valor; falha continua falha ou `indeterminado`; compilação não introduz healing de assertion.
5. Sanitizar uma cópia das gravações completas; executar varredura de segredo/PII; revisar manualmente URL, payload, headers, storage state, DOM, AX e texto.
6. Se a gravação completa validada tiver sinais ausentes na projeção mínima, substituir/complementar a fixture e regenerar snapshots conscientemente.
7. Um QA diferente do autor revisa os seis casos, os diffs e o resultado do harness.

### Dados e ambientes-alvo

- DES: aplicações autorizadas que representem SSO/OIDC, Angular Material, JSF/PrimeFaces e DataTable.
- Dados: massa sintética/autorizada; usuários, CPFs, matrículas, senhas e tokens sempre substituídos por marcadores.
- HML não é necessário para este incremento de baseline; pode ser usado se DES não disponibilizar uma das famílias.

### Resultado esperado

- 13 testes (ou mais, após inclusão de fixtures completas) verdes;
- saídas determinísticas em duas execuções consecutivas;
- nenhuma diferença não explicada entre comportamento observado e golden;
- assertions idênticas e não curadas;
- falhas reais permanecem vermelhas; ausência de validação permanece `indeterminado`;
- varredura e revisão manual sem segredos/PII.

### Critério de aprovação

Liberar o próximo prompt somente se:

- DoD de código: patch aplicado e harness verde;
- DoD de ambiente: seis famílias reexecutadas/confirmadas em DES (ou HML justificada), baseline revisado por **1 QA**, determinismo confirmado e zero segredo/PII;
- qualquer divergência está explicada e aprovada no PR.

### Critério de rollback

Fazer rollback integral deste incremento se houver segredo/PII, snapshot não determinístico, assertion alterada, falso verde, ou caso golden que não reflita a gravação real. O rollback consiste em reverter o commit/patch que adiciona `tests/golden/` e `tests/test_golden_regression.py`; nenhum código de produção é afetado. Corrigir a sanitização/fixture e repetir o gate antes de avançar.

