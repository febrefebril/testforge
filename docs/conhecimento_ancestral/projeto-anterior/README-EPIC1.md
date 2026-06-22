# TestForge — Guia de Teste Manual (Epic 1)

## Pré-requisitos

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Verificar browsers Playwright instalados
playwright install chromium
```

---

## 1. Gravação de Testes

```bash
testforge record <URL> [opções]
```

**Exemplo:**

```bash
testforge record http://localhost:8765 --headed --name "meu-primeiro-teste"
```

O `--name` define o nome do caso de teste. Afeta:
- Nome do diretório: `./testes/meu-primeiro-teste/`
- Nome do script: `meu-primeiro-teste.py`
- Nome do arquivo de dados: `meu-primeiro-teste.data.json`
- Nome do diretório de artefatos: `meu-primeiro-teste_artifacts/`

Sem `--name`, um nome é auto-gerado com timestamp (`test_20260602_164124`).

O nome do teste também fica disponível no relatório e pode ser usado como dica para o LLM na curadoria (Epic 2).

O navegador abre com um **overlay flutuante** no canto superior direito.

### Atalhos do Overlay

| Tecla        | Função                          |
|-------------|----------------------------------|
| `Shift+P`   | Pausar/retomar gravação          |
| `Shift+A`   | Ativar modo assert               |
| `Shift+S`   | Finalizar gravação               |

### Como gravar

1. Navegue pelo sistema clicando em links, preenchendo campos, selecionando opções
2. O overlay destaca cada elemento interagido e incrementa o contador de passos
3. Para adicionar **asserts**: `Shift+A` → clique em um elemento → escolha o tipo
4. `Shift+S` para finalizar — script `.py` + dados `.data.json` são gerados

---

## 2. Execução de Testes

```bash
testforge run <script.py> [opções]
```

### Modo Headless (CI/CD)

```bash
testforge run ./testes/meu_teste.py
```

### Modo Headed (visual)

```bash
testforge run ./testes/meu_teste.py --headed
```

### Flags

| Flag            | Descrição                                |
|----------------|------------------------------------------|
| `--headed`     | Abre navegador visível                   |
| `--timeout N`  | Timeout global em ms (default: 30000)    |
| `--debug`      | Logs detalhados                          |
| `--notify, -n` | Envia notificação ao finalizar           |
| `--name`       | Nome do caso de teste (record)           |

### Fallback de seletores

Quando um passo falha (elemento não encontrado), o runner tenta automaticamente os seletores alternativos salvos no `data.json`:

1. Seletor primário (capturado na gravação)
2. Fallback 1: `:has-text()` ou XPath com texto
3. Fallback 2: XPath genérico

Se um fallback funciona, o runner loga `🔄 fallback: <seletor>` e continua. Se todos falham, o passo é marcado como falha e a execução segue para o próximo.

### Timeouts por tipo de ação

| Ação       | Timeout |
|------------|---------|
| navigate  | 45s     |
| click     | 15s     |
| fill      | 15s     |
| select    | 15s     |
| upload    | 60s     |
| download  | 60s     |
| assert    | 20s     |

### Comportamento em falha

- Se um passo falha (timeout ou erro), o runner **captura screenshot** automaticamente
- A execução **continua** para o próximo passo
- O relatório marca como **"partial"** se houver falhas parciais
- Playwright **trace** é gerado em `trace.zip` para debug completo

---

## 3. Relatórios

```bash
# Ver relatório de uma execução específica
testforge report ./testes/meu_teste_artifacts/meu_teste_report.json

# Listar histórico de execuções
testforge report --history

# Histórico filtrado
testforge report --history --period 7d --status failed

# Escanear diretório específico
testforge report --history --directory ./testes
```

### O relatório contém

- **Status**: passed / failed / partial
- **Resumo executivo**: linguagem natural (ex: "3 de 4 passos passaram")
- **Detalhamento por passo**: nome, duração, status, erro (se houver)
- **Screenshot** no momento da falha
- **Playwright Trace** (trace.zip) — rede, console, DOM, timeline

---

## 4. Notificações

```bash
testforge run script.py --notify
```

### Configuração por variáveis de ambiente

**E-mail (SMTP):**
```bash
export TF_NOTIFY_EMAIL_SMTP_HOST=smtp.gmail.com
export TF_NOTIFY_EMAIL_SMTP_PORT=587
export TF_NOTIFY_EMAIL_FROM=testforge@meuemail.com
export TF_NOTIFY_EMAIL_TO=gestor@meuemail.com
export TF_NOTIFY_EMAIL_USER=testforge@meuemail.com
export TF_NOTIFY_EMAIL_PASSWORD=sua_senha
```

**Teams (webhook):**
```bash
export TF_NOTIFY_TEAMS_WEBHOOK=https://seu-domain.webhook.office.com/...
```

Se não configurado, o `--notify` apenas loga um aviso sem quebrar o teste.

---

## Troubleshooting

### Overlay não aparece

**Causa comum:** o overlay usa `document.body.appendChild()`, mas em páginas muito grandes ou lentas, o `add_init_script` do Playwright pode executar antes do `<body>` ser parseado.

**Solução:** o overlay já possui guarda DOM que espera até `document.body` existir. Se mesmo assim não aparecer, execute com `--debug` para verificar logs:

```bash
testforge record <URL> --headed --debug
```

Se houver CSP (Content-Security-Policy) bloqueando, o overlay loga `console.warn('[TestForge] overlay failed:')` e a gravação continua em **modo silencioso** (sem overlay visual, mas capturando via Playwright nativo).

### Atalhos do teclado não funcionam

**Possíveis causas:**
- O site pode interceptar eventos de teclado (comum em sites bancários com jQuery). O overlay agora usa `capture: true` para garantir que o handler dispare antes dos scripts da página.
- O gerenciador de janelas (Sway/i3) pode estar capturando Shift+P ou Shift+S como atalho do sistema. Verifique com:
  ```bash
  grep -i "Shift\+P\|Shift\+S" ~/.config/sway/config
  ```

---

## 5. Demonstração Rápida (War Room)

Servidor de teste local incluso:

```bash
# Terminal 1: iniciar servidor
cd packages/war-room/target-site
python3 -m http.server 8765

# Terminal 2: executar teste de demonstração
source .venv/bin/activate
testforge run demo/demo_test.py --headed
```

O teste demo executa: navegação SPA → busca → cadastro → select → asserts.

---

## 6. Roteiro de Teste Manual

### 6.1. Gravação básica

```bash
testforge record http://localhost:8765 --headed
```

1. ✅ O Chromium abre com o overlay "TestForge" no canto superior direito
2. ✅ Clique em "🔍 Busca" — o campo de busca aparece e o passo é registrado
3. ✅ Digite algo no campo de busca — o passo "fill" é registrado (com debounce)
4. ✅ Clique em "📝 Cadastro" — navegação SPA registrada
5. ✅ Preencha nome e email
6. ✅ Selecione "Pessoa Física" no dropdown — registrado como "select"
7. ✅ Pressione `Shift+P` — overlay mostra "Pausado"
8. ✅ Pressione `Shift+P` novamente — retoma "Gravando..."
9. ✅ Pressione `Shift+S` — gravação finaliza, script e data.json são gerados

### 6.2. Asserts — Visão Geral

O modo assert (`Shift+A`) permite verificar condições na página após cada interação.  
O overlay oferece **4 tipos de assert**:

| Tipo | Atalho | O que verifica | Gera no script |
|------|--------|----------------|----------------|
| 🔍 **Texto** (`textual`) | Clica no elemento → escolhe "Texto" | Elemento contém o texto capturado | `expect(locator).to_contain_text("...")` |
| ⌨ **Estado** (`estado`) | Clica no elemento → escolhe "Estado" | Estado do elemento (checked, unchecked, disabled, enabled) | `expect(locator).to_be_checked()` / `to_be_disabled()` / etc. |
| 👁 **Visível** (`visivel`) | Clica no elemento → escolhe "Visível" | Elemento está visível ou oculto | `expect(locator).to_be_visible()` / `not_to_be_visible()` |
| 🤖 **Auto** (`automatico`) | Clica no elemento → escolhe "Auto" | Equivalente a "Texto" (verifica conteúdo textual) | `expect(locator).to_contain_text("...")` |

**Mapeamento completo de assert `estado`:**

| Estado capturado | Playwright gerado | Exemplo de uso |
|-----------------|-------------------|----------------|
| `checked` | `to_be_checked()` | Radio button ou checkbox marcado |
| `unchecked` | `not_to_be_checked()` | Checkbox desmarcado |
| `disabled` | `to_be_disabled()` | Campo desabilitado |
| `enabled` | `to_be_enabled()` | Elemento habilitado (fallback padrão) |

**Mapeamento de assert `visivel`:**

| Valor esperado | Playwright gerado |
|---------------|------------------|
| `"visible"` | `to_be_visible()` |
| `"hidden"` | `not_to_be_visible()` |

#### Como usar

1. ✅ Pressione `Shift+A` — overlay mostra "Clique em um elemento para assert"
2. ✅ Clique em qualquer elemento da página
3. ✅ Escolha um dos 4 tipos no menu que aparece
4. ✅ O passo de assert é registrado com o valor capturado
5. ✅ O assert será executado na posição correspondente do script final

#### Limitação conhecida: `estado` em elementos toggle

Quando você clica em um checkbox/radio **durante o modo assert**, o clique **alterna** o estado do elemento. O overlay registra o estado **após** a alternância. Por isso, asserts `estado` funcionam melhor em elementos cujo estado independe de cliques anteriores:

| Funciona bem ✅ | Não funciona ❌ |
|----------------|----------------|
| `checked` em radio já marcado por padrão | `checked` em radio que precisa ser clicado primeiro |
| `disabled` em input com `disabled` nativo | `unchecked` em checkbox que depende de clique prévio |
| `enabled` em qualquer elemento habilitado | Qualquer estado que dependa de uma cadeia de cliques |

Para verificar estados dependentes de interação, use asserts **após** os passos de clique que estabelecem o estado desejado, e certifique-se de que o elemento alvo do assert **não é o mesmo** que foi clicado para mudar o estado.

### 6.3. Execução e relatório

```bash
# Headless
testforge run ./testes/<seu_teste>.py

# Headed (ver o navegador)
testforge run ./testes/<seu_teste>.py --headed

# Ver relatório
testforge report ./testes/<seu_teste>_artifacts/*_report.json
```

1. ✅ Execução headless: navegador roda sem janela visível
2. ✅ Execução headed: navegador abre e você vê cada passo
3. ✅ ✅/❌ no console para cada passo
4. ✅ Timeout: se um passo demora, falha com mensagem clara e continua
5. ✅ Relatório: `testforge report <path>` mostra status, duração, passos
6. ✅ Histórico: `testforge report --history` lista execuções anteriores

### 6.4. Notificações

```bash
# Sem config (deve logar aviso apenas)
testforge run ./testes/<seu_teste>.py --notify

# Com config
export TF_NOTIFY_EMAIL_TO=seu@email.com
testforge run ./testes/<seu_teste>.py --notify
```

1. ✅ `--notify` sem config — não quebra, apenas aviso no log
2. ✅ Com e-mail configurado — notificação enviada ao finalizar

### 6.5. Upload e download

> Nota: o war-room não tem campo de upload. Teste em qualquer sistema que tenha `input[type="file"]`.

1. ✅ Overlay detecta `input[type="file"]` quando você seleciona um arquivo
2. ✅ Nome e tipo do arquivo são capturados (não o conteúdo binário)
3. ✅ Runner executa: `page.set_input_files(selector, value)`

### 6.6. Select com label

Testado no demo:

```bash
testforge run demo/demo_test.py --headed
```

1. ✅ O runner usa `page.select_option(selector, label="Pessoa Física")`
2. ✅ Funciona com o texto visível, não com o `value` ou índice

---

## 7. Estrutura de Artefatos

```
testes/
└── meu_teste/
    ├── meu_teste.py            # Script gerado (AST Python)
    ├── meu_teste.data.json     # Dados separados do script
    └── meu_teste_artifacts/
        ├── meu_teste_report.json  # Relatório da execução
        ├── screenshots/           # Screenshots de falhas
        └── trace.zip              # Playwright trace
```

---

## 8. Funcionalidades Implementadas (Epic 1)

| Story | Funcionalidade | Status |
|-------|---------------|--------|
| 1-0 | Cross-cutting contracts (models, schemas) | ✅ |
| 1-1 | Overlay de gravação + captura de interações | ✅ |
| 1-2 | Geração de script AST + data.json separado | ✅ |
| 1-3 | Execução headed/headless + timeouts | ✅ |
| 1-4 | Asserts multi-tipo (textual, estado, visível, auto) | ✅ |
| 1-5 | Relatório em 2 camadas + histórico | ✅ |
| 1-6 | Notificação e-mail (SMTP) + Teams (webhook) | ✅ |
| 1-7 | Upload (`set_input_files`) + download (`expect_download`) | ✅ |
| 1-8 | Select com label, Shadow DOM, date picker/autocomplete debounce | ✅ |

---

## 9. Teste de Widgets JS Customizados — Epic F

### 9.0. Resumo da Verificação Automatizada (E2E)

| Framework | Strategies | ElementRect | Framework | PageTech | Execução |
|-----------|-----------|-------------|-----------|----------|----------|
| PrimeFaces | ✅ 12 | ✅ 4/4 | ✅ 4/4 | ✅ primefaces | ✅ |
| jQuery UI  | ✅ 6  | ✅ 2/2 | ✅ 2/2 | ✅ jquery-ui | ✅ |
| Kendo UI   | ✅ 8  | ✅ 2/2 | ✅ 2/2 | ✅ kendo | ✅ |
| Angular    | ✅ 8  | ✅ 2/2 | ✅ 2/2 | ⚠️ (simulado) | ✅ |

O overlay agora é um **Evidence Collector**: gera `strategies` (N estratégias por step), captura `elementRect` (x,y,w,h), `elementParentChain` (DOM path), e detecta o `framework` do widget. Ver arquitetura em `project-context.md`.

---

### 9.1. Páginas de Teste

```bash
cd tests/pagina-de-teste/primefaces && python3 -m http.server 8081
```

| Página | Framework | Widgets |
|--------|-----------|---------|
| `primefaces.html` | PrimeFaces (simulado) | 2× SelectOneMenu + 2× AutoComplete + Kendo-like dropdown |
| `jqueryui-selectmenu.html` | jQuery UI 1.13 (CDN) | 2× SelectMenu (Estado Civil, Escolaridade) |
| `kendo-dropdown.html` | Kendo UI 2023.3 (CDN) | 2× DropDownList (Categoria, Fornecedor) |
| `angular-select.html` | Angular Material (DOM) | 2× mat-select (Categoria, Pagamento) |

---

### 9.2. ✅ Caso de Teste: PrimeFaces SelectOneMenu + AutoComplete

**Verificado via E2E:** SelectOneMenu label atualiza após trigger+item click. Selector `#tipoImovelSelect` com `framework=primefaces`.

#### Gravação Manual

```bash
source /tmp/testforge-venv/activate
cd tests/pagina-de-teste/primefaces && python3 -m http.server 8081 &
testforge record http://localhost:8081/primefaces.html --headed --name tf-pf
```

**Passos a gravar:**
1. Clique no SelectOneMenu "Tipo de Imóvel" (label "Selecione") → clique em "Residencial"
2. **Pressione `Shift+A`** → clique no label "Residencial" → escolha **"Texto"** (assert)
3. Clique no SelectOneMenu "UF" → clique em "Distrito Federal"  
4. **Pressione `Shift+A`** → clique no label "Distrito Federal" → escolha **"Texto"** (assert)
5. Clique no AutoComplete "Cidade" → digite "Bras" → clique em "Brasília"
6. **Pressione `Shift+A`** → clique no input preenchido → escolha **"Texto"** (assert)
7. Pressione `Shift+S` para finalizar

**Verificações no data.json** (`testes/tf-pf/tf-pf.data.json`):

```json
// Step de interação:
{
  "action": "select",
  "selector": "#tipoImovelSelect",
  "strategies": [
    {"strategy": "id", "selector": "#tipoImovelSelect"},
    {"strategy": "dom-path", "selector": "..."}
  ],
  "attrs": {
    "framework": "primefaces",
    "elementRect": {"x":..., "w":..., "h":...}
  }
}
// Step de assert:
{
  "action": "assert",
  "assert_type": "textual",
  "selector": "...",
  "expected_value": "Residencial"
}
```

#### Execução

```bash
testforge run testes/tf-pf/tf-pf.py --headed --debug
```

**Esperado:** `[PF] trigger click... item click... ✅ label='Residencial'`. Steps 100% pass.

#### Critérios de Aceitação

- [ ] Step `select` tem `framework=primefaces` nos attrs
- [ ] `strategies` contém 2+ estratégias (id, dom-path, etc.)
- [ ] `elementRect` presente com w>0 e h>0
- [ ] Passos de assert (`assert_type=textual`) presentes no data.json
- [ ] Asserts passam na execução (verifica que o label foi atualizado)
- [ ] Label do SelectOneMenu atualiza visualmente no navegador headed

---

### 9.3. ✅ Caso de Teste: jQuery UI SelectMenu

**Verificado via E2E:** `pageTech=jquery-ui` detectado.

#### Gravação

```bash
testforge record http://localhost:8081/jqueryui-selectmenu.html --headed --name tf-jqui
```

**Passos:**
1. Clique no SelectMenu "Estado Civil" → selecione "Casado(a)"
2. **`Shift+A`** → clique no texto "Casado(a)" → **"Texto"** (assert)
3. Clique no SelectMenu "Escolaridade" → selecione "Ensino Superior"
4. **`Shift+A`** → clique no texto "Ensino Superior" → **"Texto"** (assert)
5. `Shift+S` para finalizar

#### Execução

```bash
testforge run testes/tf-jqui/tf-jqui.py --headed --debug
```

#### Critérios de Aceitação

- [ ] `pageTechnology= "jquery-ui"` nos attrs
- [ ] Selector gerado aponta para o `<select>` original ou para o span do widget
- [ ] `strategies` e `elementRect` presentes em cada step
- [ ] SelectMenu expande e seleciona corretamente durante execução

---

### 9.4. ✅ Caso de Teste: Kendo DropDownList

**Verificado via E2E:** `pageTech=kendo`, `framework=kendo`, 8 strategies, 2/2 rects.

Página auto-contida (não depende de CDN). DOM simula Kendo real: `.k-dropdownlist > .k-dropdown-wrap > .k-input + .k-select`.

#### Gravação

```bash
testforge record http://localhost:8081/kendo-dropdown.html --headed --name tf-kendo
```

**Passos:**
1. Clique no Kendo DropDownList "Categoria" → selecione "Eletrônicos"
2. **`Shift+A`** → clique no label "Eletrônicos" → **"Texto"** (assert)
3. Clique em "Fornecedor" → selecione "Importadora Brasil"
4. **`Shift+A`** → clique no label "Importadora Brasil" → **"Texto"** (assert)
5. `Shift+S` para finalizar

#### Execução

```bash
testforge run testes/tf-kendo/tf-kendo.py --headed --debug
```

#### Critérios de Aceitação

- [ ] `framework=kendo` e `pageTechnology=kendo` nos attrs
- [ ] `strategies` contém 4+ estratégias (id, has-text, class, dom-path)
- [ ] `elementRect` e `elementParentChain` presentes
- [ ] DropDownList abre e item é selecionado visualmente

---

### 9.5. ✅ Caso de Teste: Angular Material mat-select

**Verificado via E2E:** `fw=angular` detectado via `role="listbox"` e `mat-select`. `pageTech` vazio (página simulada, sem `window.angular`).

#### Gravação

```bash
testforge record http://localhost:8081/angular-select.html --headed --name tf-angular
```

**Passos:**
1. Clique no mat-select "Categoria" → selecione "Eletrônicos"
2. **`Shift+A`** → clique no valor "Eletrônicos" → **"Texto"** (assert)
3. Clique em "Forma de Pagamento" → selecione "PIX"
4. **`Shift+A`** → clique no valor "PIX" → **"Texto"** (assert)
5. `Shift+S` para finalizar

#### Execução

```bash
testforge run testes/tf-angular/tf-angular.py --headed --debug
```

#### Critérios de Aceitação

- [ ] `framework=angular` nos attrs
- [ ] `strategies` contém estratégias baseadas em `id`, `has-text`, `dom-path`
- [ ] `elementRect` capturado
- [ ] `ariaSelected=true` no item selecionado após execução

---

### 9.6. ✅ Teste de Todos os Tipos de Assert

**Objetivo:** Validar que os 4 tipos de assert (textual, estado, visivel, automatico) gravam e executam corretamente.

**Página:** `primefaces.html` (contém radios, checkbox, disabled input, hidden element)

#### Gravação

```bash
testforge record http://localhost:8081/primefaces.html --headed --name tf-assert-all
```

**Passos a gravar:**

| # | Ação | Assert | Tipo | O que verifica |
|---|------|--------|------|---------------|
| 1 | SelectOneMenu → "Residencial" | — | — | Interação normal |
| 2 | `Shift+A` → clique no `<h1>` → **Texto** | textual | `to_contain_text` | Título contém "PrimeFaces Widgets" |
| 3 | `Shift+A` → clique no radio "À Vista" → **Estado** | estado/checked | `to_be_checked()` | Radio "À Vista" está marcado (checked by default) |
| 4 | `Shift+A` → clique no input "Nome" → **Estado** | estado/disabled | `to_be_disabled()` | Input está desabilitado |
| 5 | `Shift+A` → clique no bloco "Última interação" → **Visível** | visivel/visible | `to_be_visible()` | Elemento está visível |
| 6 | `Shift+A` → clique no `#hiddenElement` → **Visível** | visivel/hidden | `not_to_be_visible()` | Elemento oculto (`display:none`) |
| 7 | AutoComplete → digite "Bras" → clique "Brasília" | — | — | Interação normal |
| 8 | `Shift+A` → clique no input preenchido → **Auto** | automatico | `to_contain_text` | (equiv. a textual, captura textContent) |
| 9 | `Shift+S` para finalizar | — | — | — |

> **Nota:** Para o passo 6, o `#hiddenElement` tem `display:none`. Você precisa clicar nele via JS (`element.dispatchEvent(new PointerEvent('pointerup'))`) já que Playwright não clica em elementos invisíveis. No modo headed, use o overlay normalmente — clique no elemento oculto não é possível visualmente.

#### Verificações no data.json

```json
// Assert textual
{
  "action": "assert",
  "assert_type": "textual",
  "expected_value": "🧪 PrimeFaces Widgets — Página de Teste",
  "selector": "h1"
}
// Assert estado (checked)
{
  "action": "assert",
  "assert_type": "estado",
  "assert_state": "checked",
  "expected_value": "checked",
  "selector": "#avistaRadio"
}
// Assert estado (disabled)
{
  "action": "assert",
  "assert_type": "estado",
  "assert_state": "disabled",
  "expected_value": "disabled",
  "selector": "#nomeInput"
}
// Assert visivel (visible)
{
  "action": "assert",
  "assert_type": "visivel",
  "expected_value": "visible",
  "selector": "#result"
}
// Assert visivel (hidden)
{
  "action": "assert",
  "assert_type": "visivel",
  "expected_value": "hidden",
  "selector": "#hiddenElement"
}
// Assert automatico
{
  "action": "assert",
  "assert_type": "automatico",
  "expected_value": "Brasília",
  "selector": "#cidadeAcInput"
}
```

#### Execução Automatizada

O teste completo está em `/tmp/opencode/test_assert_all_types.py` e pode ser executado com:

```bash
source /tmp/testforge-venv/bin/activate
python3 /tmp/opencode/test_assert_all_types.py
```

**Saída esperada:**
```
Asserts recorded: 6
  [textual] state=enabled expected='🧪 PrimeFaces Widgets...'
  [estado] state=checked expected='checked' sel='#avistaRadio'
  [estado] state=disabled expected='disabled' sel='#nomeInput'
  [visivel] state=enabled expected='visible' sel='#result'
  [visivel] state=enabled expected='hidden' sel='#hiddenElement'
  [automatico] state=enabled expected='' sel='#cidadeAcInput'
✅ All 4 assert types recorded!

8/8 passed ✅ ALL ASSERT TYPES OK!
```

**Observações sobre o resultado:**
- ✅ `textual`: `to_contain_text("PrimeFaces Widgets")` — verifica título da página
- ✅ `estado/checked`: `to_be_checked()` — radio "À Vista" está marcado por padrão
- ✅ `estado/disabled`: `to_be_disabled()` — input "Nome" tem `disabled` nativo
- ✅ `visivel/visible`: `to_be_visible()` — `#result` está visível na tela
- ✅ `visivel/hidden`: `not_to_be_visible()` — `#hiddenElement` tem `display:none`
- ✅ `automatico`: equivale a `textual`, verifica `to_contain_text("")` (input vazio em texto)

#### Critérios de Aceitação

- [ ] Todos os 4 tipos de assert (`textual`, `estado`, `visivel`, `automatico`) aparecem no data.json
- [ ] Assert `estado` com `state=checked` executa e passa
- [ ] Assert `estado` com `state=disabled` executa e passa
- [ ] Assert `visivel` com `expected=visible` executa e passa
- [ ] Assert `visivel` com `expected=hidden` executa e passa (gera `not_to_be_visible()`)
- [ ] Assert `textual` com texto capturado executa e passa
- [ ] Assert `automatico` executa (equivale a textual)
- [ ] `builder.py` gera `to_be_visible()` ou `not_to_be_visible()` conforme `expected_value`
- [ ] `runner.py` executa `to_be_visible()` ou `not_to_be_visible()` conforme `expected_value`
- [ ] `builder.py` gera fallback loop (`for/else/try/except`) para ações `click` e `fill`
- [ ] Script gerado usa nome `test_*.py` e classe prefixada com `Test` para compatibilidade pytest
- [ ] Script gerado funciona com `pytest` (coleta e executa, exceto framework-specific healing)

---

### 9.6b. Builder Fallback Loop

O `builder.py` agora gera scripts com **fallback loop** para ações críticas (`click`, `fill`), tentando TODOS os seletores registrados no data.json. Se um seletor falha, tenta o próximo automaticamente.

```python
for _sel in ['li:has-text("Residencial")', 'li.ui-selectonemenu-item']:
    try:
        page.click(_sel)
        break
    except Exception:
        continue
else:
    raise AssertionError('click falhou: ' + str([...]))
```

**Mecanismo:**
- `ScriptBuilder._selector_list(primary, strategies)` → lista completa de seletores (sem duplicatas)
- `ScriptBuilder._build_fallback_block(selectors, template)` → gera AST via `ast.parse()` com o template
- Templates: `CLICK_TEMPLATE`, `FILL_TEMPLATE` para ações com fallback; `SELECT_LABEL_TEMPLATE`, `SELECT_VALUE_TEMPLATE`, `UPLOAD_TEMPLATE` com seletor único (`_SEL_LIST_[0]`)

**Ações com fallback:**
- `click`: loop sobre todas as estratégias de seletor
- `fill`: loop sobre todas as estratégias + valor do data.json
- `select`, `upload`: seletor único (já têm fallback via runner)

**Ações sem fallback:**
- `navigate`, `assert`, `download`, `drag`: seletor único (não faz sentido tentar sel alternativo)

### 9.6c. pytest Naming Conventions

Os scripts gerados agora seguem as convenções do **pytest** para descoberta automática:

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Filename | `tf-assert-all.py` | `test_tf_assert_all.py` |
| Class name | `TfAssertAll` | `TesttfAssertAll` |
| pytest descobre? | ❌ (nome/prefixo não padrão) | ✅ `test_*.py` + `Test*` |

**Implementação:**
- `serializer.py:_pytest_safe_name()` → prefixa `test_` se ausente
- `session.py` → prefixa `test_` no nome do diretório/arquivo
- `builder.py:__init__()` → prefixa `Test` na classe se ausente

**Limitação conhecida:** pytest só executa o Playwright puro. Framework-specific healing (PrimeFaces select, autocomplete, fill strategies) só funciona via `testforge run --healing`. O fallback loop do builder cobre apenas falhas de seletor, não de interação framework.

---

### 9.7. Checklist Final do Testador

Após testar cada framework, preencher:

| Framework | Gravou? | framework OK? | strategies? | rect OK? | Executou? | Asserts OK? |
|-----------|---------|---------------|-------------|----------|-----------|------------|
| PrimeFaces | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| jQuery UI  | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Kendo UI   | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Angular    | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

**Notas do testador:** 
_(preencher com observações, bugs encontrados, comportamentos inesperados)_
_________________________________________________________________
_________________________________________________________________

---

## 10. Backlog — Pendentes

| Item | Descrição | Dependência |
|------|-----------|-------------|
| **F.2 final** | Testar runner com scripts reais gravados (`testforge run`) | F.1 concluído |
| **F.2 final** | Ajustar builder para gerar código com `_try_primefaces_select()` | F.1 concluído |
| **F.3** | Healing — Agente Especialista PrimeFaces (FAM-08) | F.1, F.2 |
| **F.3** | `classifier.py`: adicionar `PRIMEFACES_KEYWORDS` | F.3 |
| **F.3** | `collector.py`: `_capture_primefaces_state()` | F.3 |
| **F.3** | `agents/primefaces.py`: novo agente Layer 2 | F.3 |
| **F.3** | `llm/healer.py`: adicionar `selectonemenu_select` strategy | F.3 |
| **Kendo** | Ajustar `detectFramework` para widget real com CDN carregado | — |
| **Kendo** | Implementar `_try_kendo_select()` no runner | F.2 |
| **Angular** | Adicionar `_try_angular_select()` no runner | F.2 |
| **Multi-framework** | Validar gravação+execução em todas as 4 páginas | F.2 |

## 11. Funcionalidades Implementadas (Epic F)

| Story | Funcionalidade | Status |
|-------|---------------|--------|
| F.0 | Páginas de teste (4 frameworks) | ✅ |
| F.1 | overlay.js: `generateStrategies()` — N estratégias por step | ✅ |
| F.1 | overlay.js: `getParentChain()` — DOM path do elemento | ✅ |
| F.1 | overlay.js: `captureAttributes()` com `elementRect` + `elementParentChain` | ✅ |
| F.1 | overlay.js: `detectFramework()` — PrimeFaces, jQuery UI, Kendo, Angular | ✅ |
| F.1 | overlay.js: `_tf_detectPageTech()` — page technology detect | ✅ |
| F.1 | overlay.js: `addTFStep()` — auto-popula `pageTechnology` + `fallbacks` | ✅ |
| F.1 | session.py: `page_technology` via `attrs.pageTechnology` | ✅ |
| F.1 | session.py: `strategies` lido do overlay | ✅ |
| F.1 | builder.py: `strategies` escrito no data.json | ✅ |
| F.1 | models.py: `RecordedStep.strategies` (list[dict]) | ✅ |
| F.2 | overlay.js: `detectFramework()` — `.mat-calendar` detection | ✅ |
| F.2 | runner.py: `_inject_button_has_text()` — fallback span→button para old recordings | ✅ |
| F.2 | runner.py: `_try_with_fallbacks` usa `strategies` (com fallback p/ `fallbacks`) | ✅ |
| F.2 | runner.py: `_try_primefaces_select()` — trigger → item → label verify | ✅ |
| F.2 | runner.py: PrimeFaces routing no `select` (framework=primefaces) | ✅ |
| F.2 | builder.py: fallback loop `for/else/try/except` para click e fill | ✅ |
| F.2 | serializer.py: `_pytest_safe_name()` — filenome `test_*.py` | ✅ |
| F.2 | builder.py: class name prefixada com `Test` | ✅ |
| F.2 | overlay.js: `resolveElement()` — Angular Material datepicker spans → button | ✅ |
| E.1 | runner.py: cascading failure (identicas + total consecutivas) | ✅ |
| E.1 | runner.py: dialog dismiss (display:none + API, sem force-remove) | ✅ |
| E.1 | runner.py: `_check_action_effect` fill (invisível w=0 h=0) | ✅ |
| E.1 | runner.py: console handler filtra "Failed to load resource" | ✅ |
| E.1 | runner.py: assert timeout reduzido 20s→5s | ✅ |
| CLI | `--ignore-https-errors` flag | ✅ |
| CLI | `--slow-mo` flag | ✅ |
| Doc | `.opencode/project-context.md` atualizado | ✅ |
| Doc | `README-EPIC1.md` — seções 9-11 | ✅ |
| Doc | `sprint-status.yaml` — Epic F tracking | ✅ |
| Doc | Diagramas PlantUML — status Epic F | ✅ |
