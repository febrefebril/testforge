# Roteiro de Testes Manuais — TestForge

## Pré-requisitos

- Python 3.13+
- `testforge-core` instalado em modo editável (`pip install -e packages/core`)
- Playwright + Chromium instalados (`playwright install chromium`)
- Terminal com capacidade de executar comandos `testforge`
- Navegador Chromium/Chrome para testes headed

## Setup

```bash
# 1. Ativar ambiente virtual
source /tmp/testforge-venv/bin/activate

# 2. Iniciar servidores de teste
python3 -m http.server 8080 --directory testes/pagina-de-teste &
python3 -m http.server 8081 --directory testes/pagina-de-teste-completa &
python3 -m http.server 8082 --directory tests/test_pages/curation &

# 3. Verificar servidores
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/  # deve retornar 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/  # deve retornar 200
```

---

## Seção 1: Gravação

### 1.1 Gravação Básica (modo full)

**Objetivo:** Validar que o overlay é injetado e eventos são capturados.

```bash
testforge record http://localhost:8080 --name teste-basico --mode full --timeout 5
```

**Procedimento:**
1. O navegador abre com o overlay do TestForge visível
2. Clique em alguns elementos na página (botões, inputs, selects)
3. Pressione `Shift+S` para finalizar a gravação
4. Verifique se o script foi gerado em `testes/teste-basico/teste-basico.py`

**Resultado esperado:** Script gerado com steps de clique, navegação e preenchimento.

### 1.2 Gravação em Modo Shortcuts

**Objetivo:** Validar gravação sem UI do overlay (apenas listeners).

```bash
testforge record http://localhost:8081 --name teste-shortcuts --mode shortcuts --timeout 5
```

**Procedimento:** Mesmo que 1.1, mas sem a interface visual do overlay.

**Resultado esperado:** Script gerado sem diferenças funcionais.

### 1.3 Gravação de Seletores (Página Completa)

**Objetivo:** Testar captura de cada tipo de seletor.

```bash
testforge record http://localhost:8081 --name teste-seletores --mode shortcuts --timeout 10
```

**Procedimento:** Navegue pela página e interaja com cada seção:
1. **SEL-001**: Clique em ambos os botões "Ação"
2. **SEL-004**: Preencha "Campo sem ID"
3. **SEL-008**: Clique em "Prioridade" (botão com data-testid)
4. **SEL-010**: Selecione uma opção de radio
5. **FAM-06**: Preencha o campo CPF, selecione no combo box
6. **FAM-07**: Faça upload de arquivo
7. Pressione `Shift+S`

**Verificação:** Confira no script gerado que:
- SEL-008 usou `[data-testid="btn-prioridade"]` (prioridade máxima)
- SEL-004 gerou `[name="campo-sem-id"]` ou `[placeholder="Apenas name e placeholder"]`
- SEL-010 gerou `label:has-text("Opção A")`
- CPF gerou `#inp-007-cpf`

### 1.4 Gravação com Pause/Resume

**Objetivo:** Validar que Shift+P pausa e retoma a captura.

```bash
testforge record http://localhost:8081 --name teste-pause --mode full --timeout 5
```

**Procedimento:**
1. Clique em alguns elementos
2. Pressione `Shift+P` — overlay deve mostrar "PAUSADO"
3. Clique em mais elementos (não devem ser capturados)
4. Pressione `Shift+P` novamente — retoma
5. Clique em mais elementos (devem ser capturados)
6. `Shift+S` para finalizar

**Resultado esperado:** Script contém apenas steps dos períodos ativos.

### 1.5 Menu Assert (Shift+A)

**Objetivo:** Validar que o menu de assert funciona durante a gravação.

```bash
testforge record http://localhost:8081 --name teste-assert --mode full --timeout 5
```

**Procedimento:**
1. Navegue até a seção FAM-08
2. Clique em um elemento alvo
3. Pressione `Shift+A` — menu de assert deve aparecer
4. Selecione "Texto" e digite o texto esperado
5. Continue gravando, pressione `Shift+S`

**Resultado esperado:** Script contém steps do tipo "assert" com texto esperado.

---

## Seção 2: Execução

### 2.1 Execução Básica

**Objetivo:** Rodar um script gravado.

```bash
testforge run testes/teste-basico/teste-basico.py
```

**Resultado esperado:** Todos os steps passam. Relatório gerado com status "passed".

### 2.2 Execução com Fallbacks

**Objetivo:** Validar que fallbacks de seletor funcionam.

```bash
# Usar script de teste predefinido com fallbacks
testforge run /tmp/teste-cura/teste-cura.py
```

**Resultado esperado:** Script executa com sucesso usando seletor primário.

### 2.3 Execução com Healing Automático

**Objetivo:** Validar que fallbacks são registrados no catálogo.

```bash
HEALING_DB=/tmp/healing-test.jsonl
rm -f "$HEALING_DB"
testforge run /tmp/teste-cura/teste-cura.py --healing "$HEALING_DB"
testforge healing list --db "$HEALING_DB"
```

**Resultado esperado:** Catálogo contém entrada com fallback registrado.

### 2.4 Execução com Slow-mo

**Objetivo:** Validar modo câmera lenta.

```bash
testforge run /tmp/teste-cura/teste-cura.py --slow-mo 500 --headed
```

**Resultado esperado:** Execução visível em câmera lenta (500ms entre ações).

### 2.5 Execução Headless vs Headed

**Objetivo:** Verificar ambos os modos.

```bash
testforge run /tmp/teste-cura/teste-cura.py            # headless (padrão)
testforge run /tmp/teste-cura/teste-cura.py --headed   # headed (visível)
```

### 2.6 Fill com Máscara JS

**Objetivo:** Validar fill em campo com máscara (CPF).

```bash
testforge record http://localhost:8081 --name teste-cpf --mode shortcuts --timeout 5
```

**Procedimento:**
1. Navegue até FAM-06, seção INP-007
2. Digite "12345678901" no campo CPF
3. Finalize com Shift+S
4. Execute:
```bash
testforge run testes/teste-cpf/teste-cpf.py --headed
```

**Resultado esperado:** Runner detecta máscara, usa pressSequentially, valor final correto.

### 2.7 Upload e Download

**Objetivo:** Validar captura e execução de upload/download.

```bash
# Gravar
testforge record http://localhost:8081 --name teste-file --mode shortcuts --timeout 5
```

**Procedimento:**
1. Seção FAM-07: faça upload de um arquivo em FILE-001
2. Clique em download em FILE-004
3. Finalize com Shift+S

**Resultado esperado:** Script tem steps de upload e download.

---

## Seção 3: Healing / Cura

### 3.1 Catálogo — Listar Entradas

```bash
testforge healing list
testforge healing list --family FAM-01
testforge healing list --taxonomy SEL-008
```

### 3.2 Catálogo — Adicionar Manualmente

```bash
testforge healing add \
  --system "Manual" \
  --symptom "data-testid removido por JS" \
  --root-cause "Script externo remove atributo" \
  --fix "Usar has-text como fallback" \
  --family "FAM-01" --taxonomy "SEL-008" \
  --fix-type "curation"
```

### 3.3 Catálogo — Visualizar Detalhes

```bash
# Pegar o ID da entrada
ID=$(python3 -c "import json; print(json.load(open('./healing-catalog.jsonl'))['id'])")
testforge healing show "$ID"
```

### 3.4 Revisão de Entradas

```bash
testforge healing review --all
testforge healing review --stale
testforge healing review --duplicates
testforge healing review --unresolved
```

### 3.5 Promover / Mesclar / Deletar

```bash
# Promover (marcar como revisada)
testforge healing promote "$ID"

# Mesclar duas entradas
# testforge healing merge <id1> <id2>

# Deletar (com confirmação)
# testforge healing delete "$ID"
```

### 3.6 Pipeline de Cura (Full)

**Objetivo:** Testar o pipeline completo L1 → L2 → L3.

```bash
# Executar script contra página com erro + healing
python3 -c "
import json
d = json.load(open('/tmp/teste-cura/teste-cura.data.json'))
d['steps'][0]['url'] = 'http://localhost:8081/fam-01-selector/?error=1'
json.dump(d, open('/tmp/teste-cura/teste-cura.data.json', 'w'), indent=2)
"
testforge run /tmp/teste-cura/teste-cura.py --healing /tmp/healing-full.jsonl
```

**Procedimento:**
1. O seletor primário `[data-testid="btn-salvar"]` falha (error.js remove o atributo)
2. Runner tenta fallbacks: `button:has-text("Salvar")` funciona
3. Healing é registrado automaticamente no catálogo
4. Verificar entrada:
```bash
testforge healing show "$(python3 -c "import json; print(json.load(open('/tmp/healing-full.jsonl'))['id'])")" --db /tmp/healing-full.jsonl
```

---

## Seção 4: Relatório

### 4.1 Relatório de uma Execução

```bash
testforge run /tmp/teste-cura/teste-cura.py
# Relatório gerado automaticamente em teste-cura_report.json
```

Verifique o arquivo de relatório:
```bash
cat /tmp/teste-cura/teste-cura_artifacts/teste-cura_report.json | python3 -m json.tool
```

### 4.2 Histórico de Execuções

```bash
testforge report --history
```

### 4.3 Histórico com Filtros

```bash
testforge report --period 7        # últimos 7 dias
testforge report --status passed   # apenas sucessos
testforge report --status failed   # apenas falhas
testforge report --status partial  # apenas parciais
```

### 4.4 Filtros por Taxonomia/Família

```bash
testforge report --taxonomy SEL-008
testforge report --family FAM-01
```

---

## Seção 5: CLI Completo

### 5.1 Ajuda

```bash
testforge --help
testforge record --help
testforge run --help
testforge report --help
testforge healing --help
```

### 5.2 Listar Sistemas no Catálogo

```bash
testforge healing systems
```

### 5.3 Listar Taxonomias

```bash
testforge healing taxonomy
```

---

## Seção 6: Modos

### 6.1 Modo Full (com interface)

```bash
testforge record http://localhost:8081 --name modo-full --mode full --timeout 3
```

**Características:** Overlay visível com botões, painel de status, indicador de passos.

### 6.2 Modo Shortcuts (sem interface)

```bash
testforge record http://localhost:8081 --name modo-shortcuts --mode shortcuts --timeout 3
```

**Características:** Sem interface visual, apenas atalhos de teclado ativos.

---

## Checklist de Regressão

Marque com [x] cada item após testar:

### Gravação
- [ ] `testforge record` inicia navegador sem erro
- [ ] Overlay injetado (modo full)
- [ ] Cliques são capturados (pointerup)
- [ ] Inputs são capturados (input/change/keydown)
- [ ] Select/option é capturado
- [ ] Upload de arquivo é capturado
- [ ] Download é capturado
- [ ] Shadow DOM é capturado
- [ ] Iframe same-origin é capturado
- [ ] Alert/confirm/prompt são capturados
- [ ] Shift+P pausa/retoma
- [ ] Shift+S finaliza
- [ ] Shift+A abre menu assert
- [ ] Script .py é gerado com steps
- [ ] Data .json é gerado com fallbacks

### Execução
- [ ] `testforge run` executa script sem erro
- [ ] Fallbacks de seletor funcionam
- [ ] Fill em campo com máscara funciona
- [ ] Radio/checkbox são selecionados
- [ ] Upload funciona via runner
- [ ] Download funciona via runner
- [ ] Auto-healing registra fallbacks (--healing)
- [ ] Timeout de step é respeitado
- [ ] Modo headed funciona
- [ ] Modo headless funciona
- [ ] `--slow-mo` funciona

### Healing
- [ ] `healing list` retorna entradas
- [ ] `healing list --family` filtra
- [ ] `healing add` cria entrada
- [ ] `healing show` exibe detalhes
- [ ] `healing promote` marca como revisado
- [ ] `healing review --all` mostra status
- [ ] `healing delete` remove (com confirmação)
- [ ] Pipeline L1/L2/L3 executa sem erro

### Relatório
- [ ] `report --history` mostra execuções
- [ ] `report --period N` filtra por dias
- [ ] `report --status passed` filtra
- [ ] `report --taxonomy` filtra
- [ ] `report --family` filtra
- [ ] JSON do relatório é válido

### CLI Geral
- [ ] `--help` funciona para todos comandos
- [ ] Flags `--headed`/`--timeout`/`--debug` funcionam
- [ ] Modo `full` vs `shortcuts` alterna corretamente
- [ ] Erros CLI produzem mensagens úteis

### Regressão Automatizada
- [ ] `testes/testar-tudo.sh` executa sem falhas
- [ ] 139 testes unitários passam

---

## Resumo

| Seção | Testes | Status |
|-------|--------|--------|
| 1. Gravação | 5 testes | __/5 |
| 2. Execução | 7 testes | __/7 |
| 3. Healing | 6 testes | __/6 |
| 4. Relatório | 4 testes | __/4 |
| 5. CLI | 3 testes | __/3 |
| 6. Modos | 2 testes | __/2 |
| Checklist | 40 itens | __/40 |

**Total:** __/67
