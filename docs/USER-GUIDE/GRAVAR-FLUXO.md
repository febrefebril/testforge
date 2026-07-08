# Como Gravar um Teste

Guia completo do fluxo de gravação: do comando ao teste executável.

---

## 1. Iniciar a gravação

### Pela GUI (recomendado para QA)
```bash
testforge-gui
```
Preencha os campos e clique **Iniciar**. Veja [GUI-LAUNCHER.md](GUI-LAUNCHER.md) para detalhes.

### Pela linha de comando
```bash
testforge record https://app.example.com \
  --name CT-001 \
  --system MYSYSTEM \
  --suite credito \
  --test-case "fluxo end-to-end" \
  --complete \
  --validate-before-ready \
  --pilot-mode
```

**Flags importantes:**
| Flag | Efeito |
|------|--------|
| `--headless` | Navegador invisível (CI) |
| `--complete` | Após gravar, verifica campos pendentes e pergunta valores |
| `--validate-before-ready` | Executa o teste gerado e avalia qualidade |
| `--pilot-mode` | Validação automática — marca READY se passar |
| `--no-interactive` | Pula perguntas. Gera template JSON. |
| `--diagnostic-mode` | Só telemetria, sem gerar teste executável |

---

## 2. O Overlay

Ao abrir o navegador, um **painel flutuante** aparece no canto superior direito:

```
┌──────────────────────────────────────┐
│  R  Gravando...  ||  []  Assert  │  ← Painel do overlay
│  Passos: 5  |  Asserts: 2           │
│  SIMULADOR / credito / fluxo end-to-end │  ← Contexto
│  v0.1.0                             │  ← Versão
└──────────────────────────────────────┘
```

**O que cada elemento significa:**

| Elemento | Significado |
|----------|-------------|
| **R** (vermelho) | Indicador de gravação ativa |
| **Gravando...** | Status atual. Muda para "Pausado" ao pausar |
| **\|\|** | Botão Pausar. Ao clicar vira **0** vermelho. Clique de novo para retomar. |
| **[]** | Botão Parar. Encerra a gravação. |
| **Assert** | Entra no modo de assert (mesmo que Shift+A) |
| **Passos** | Número de ações capturadas (clicks, fills, navegações) |
| **Asserts** | Número de verificações adicionadas (Shift+A) |

**O overlay é arrastável** — clique e segure para mover.

---

## 3. Interagindo com a aplicação

Enquanto grava, **use a aplicação normalmente**:

- Clique em botões, links, menus
- Preencha campos de texto
- Selecione opções em dropdowns
- Navegue entre páginas

O TestForge captura **todas as interações** automaticamente. Você não precisa fazer nada especial — apenas executar o fluxo de teste como faria manualmente.

**Atalhos do teclado:**

| Tecla | Ação |
|-------|------|
| **Shift+P** | Pausar / Retomar |
| **Shift+S** | Parar gravação |
| **Shift+A** | Modo Assert (adicionar verificação) |

---

## 4. Adicionando verificações (Assert)

Durante a gravação, você pode marcar elementos que devem ser verificados. Pressione **Shift+A** e depois **clique no elemento** que quer verificar.

Aparece um menu com 5 opções:

### Tipos de Assert

| Tipo | Quando usar | O que o teste verifica |
|------|-------------|----------------------|
| **Text** | Verificar o texto exato de um elemento | `expect(locator).toHaveText("valor esperado")` |
| **State** | Verificar o estado do elemento (visível, habilitado, selecionado) | `expect(locator).toBeVisible()` ou `.toBeEnabled()` |
| **Visible** | Confirmar que um elemento está visível | `expect(locator).toBeVisible()` |
| **Auto** | Confiança automática — o TestForge decide o melhor check | Heurística baseada no tipo do elemento |
| **Error** | Marcar que este elemento indica um **erro esperado** | Gera assert com metadata de erro |

### Quando usar cada um

- **Text**: use quando o valor exato importa. Ex: "Saldo: R$ 1.500,00", mensagem "Operação concluída com sucesso".
- **State**: use para verificar que um campo está habilitado/desabilitado. Ex: botão "Confirmar" só aparece após preencher formulário.
- **Visible**: use quando você só precisa confirmar que algo apareceu. Ex: modal de confirmação, resultado de busca.
- **Error**: use em mensagens de erro **esperadas**. Ex: "CPF inválido" após digitar CPF errado de propósito. O teste entende que esta mensagem é o resultado correto.
- **Auto**: use quando não tem certeza. O TestForge analisa o elemento e escolhe a verificação mais adequada.

**Para cancelar um assert:** pressione **Esc** antes de escolher o tipo.

---

## 5. Parando a gravação

- Clique no botão **[] (Stop)** no overlay, ou
- Pressione **Shift+S**, ou
- Feche o navegador

O TestForge processa a gravação e executa (se `--complete` ou `--validate-before-ready`):

```
[TestForge] Sessao salva: recordings/CT-001/
[TestForge] [BUSCA] Verificando completude da intencao...
[TestForge] [OK] Relatorio: recordings/CT-001/completeness/intent_completeness_report.md
[TestForge] [OK] Validacao PASSOU — gravacao pronta para o time!
```

---

## 6. O que acontece depois

### Compilar o teste gerado
```bash
testforge compile CT-001
```
Gera um script Playwright Python em `semantic_tests/ST-CT-001/test_st_ct_001.py`.

### Executar o teste
```bash
testforge run-incremental semantic_tests/ST-CT-001/test_st_ct_001.py
```
Executa o teste com self-healing. Gera relatório em `healing_report.md`.

### Ver resultado
```bash
testforge pilot-report CT-001
```
Relatório de métricas: passos passaram, curas aplicadas, issues encontradas.

---

## 7. Onde os arquivos ficam

```
recordings/
  SIMULADOR/
    credito/
      CT-001/
        ├── recording_metadata.json    ← Metadados da gravação
        ├── raw_events.jsonl           ← Eventos brutos capturados
        ├── steps.jsonl                ← Asserts manuais (Shift+A)
        ├── value_mutations.jsonl      ← Valores de campos ao longo do tempo
        ├── submission_report.json     ← Relatório de publicação
        ├── completeness/              ← Relatório de completude
        ├── readiness/                 ← Gate de prontidão (READY/REVIEW/FAIL)
        └── diagnostic/                ← Telemetria da gravação

semantic_tests/
  ST-CT-001/
    ├── test_st_ct_001.py              ← Teste Playwright compilado
    └── semantic_steps.jsonl           ← Passos semânticos
```

Veja [RECORDING-FILES.md](../REFERENCIA/RECORDING-FILES.md) para explicação detalhada de cada arquivo.
