# Pagina de Teste — Cobertura da Taxonomia

Pagina HTML unica com 1 exemplo de cada tipo de elemento da taxonomia
(`taxonomy.cases.yaml`). Serve como especificacao viva para validar:

- Gravador (overlay captura todos os eventos corretamente)
- Runner (execucao consegue interagir com todos os elementos)
- Curador (consegue curar quando algo quebra)

## Mapeamento Elemento → Caso Taxonomia

| Elemento | ID | Caso |
|---|---|---|
| Input sem id/name | `#secao-seletores .no-id-input` | SEL-006 |
| Label sem `for` | `label + #campo-label-for` | SEL-010 |
| Radio sem `for` | `.radio-label-custom` + `.hidden-radio` | SEL-010 |
| Botoes com texto duplicado | `.acao-duplicada[data-id]` | SEL-009 |
| Div generica sem atributos | `#secao-seletores span` | SEL-004 |
| Botao fora do form | `#btn-fora-form` | SEL-007 |
| Mascara CPF | `#campo-cpf` | INP-007 |
| Date picker jQuery UI | `#campo-data` | INP-009 |
| Combobox customizado | `#campo-combobox` | INP-010 |
| Upload arquivo | `#campo-upload` | INP-002 |
| Drag-and-drop | `#sortable-list` + `#drop-zone` | INP-005 |
| Contenteditable | `#campo-richedit` | INP-006 |
| Autocomplete jQuery UI | `#campo-autocomplete` | TIM-006, INP-010 |
| Conteudo com delay 2s | `#lazy-container` | TIM-006 |
| Select com opcoes async | `#select-assincrono` | TIM-006 |
| Shadow DOM | `#shadow-host` (shadow root) | CTX-003 |
| Iframe same-origin | `#iframe-teste` | CTX-001 |
| Modal/dialog | `#modal-overlay` + `#campo-modal` | CTX-006 |
| Overlay bloqueando clique | `#overlay-blocker` | STA-002 |
| Alert nativo | `#btn-alert` | STA-004 |
| Confirm nativo | `#btn-confirm` | STA-004 |
| Prompt nativo | `#btn-prompt` | STA-004 |
| Lista reordenavel | `#lista-reordenavel` | DOM-002 |
| Conteudo sob demanda | `#conteudo-dinamico` | DOM-005 |
| Form completo | `#form-completo` | Integracao |

## Como usar

1. Abra a pagina em um navegador (file:// ou servidor local):
   ```
   python3 -m http.server 8080 --directory testes/pagina-de-teste
   ```
2. Inicie a gravacao com TestForge:
   ```
   testforge record --name teste-taxonomia --url http://localhost:8080
   ```
3. Interaja com cada elemento da pagina
4. Execute o teste gerado:
   ```
   testforge run testes/teste-taxonomia/teste-taxonomia
   ```
5. Verifique se todos os steps passam

## Criterios de Aceite

- Gravador captura cada interacao como um step separado
- Runner executa todos os steps sem timeout
- Seletores gerados sao resilientes (nao usam XPath absoluto)
- Elementos ocultos/disablers tem fallback (label click, JS)
- Dialogs nativos sao auto-acceptados
- Shadow DOM e iframe sao acessiveis
