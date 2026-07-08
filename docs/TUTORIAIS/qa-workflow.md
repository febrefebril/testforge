# Workflow do QA no TestForge

> Guia prático: do zero ao teste publicado. Siga como receita de bolo.

---

## 1. Instalação

Antes de começar, instale o TestForge CLI. Siga o guia completo em:

→ [INSTALL.md](../INSTALL.md) (ou `docs/INSTALL.md`)

Verifique se tudo funciona:

```bash
testforge --version
# Deve mostrar a versão instalada
```

---

## 2. Abrindo a GUI

A interface gráfica é o ponto de partida para gravar testes. Siga:

→ [GUI-LAUNCHER.md](../USER-GUIDE/GUI-LAUNCHER.md) (ou `docs/USER-GUIDE/GUI-LAUNCHER.md`)

Resumo rápido:

```bash
testforge gui
```

A GUI abre no navegador em `http://localhost:5173`. É aqui que você gerencia gravações, revisa `SemanticTestCases` e acompanha o pipeline.

---

## 3. Configurando a gravação

Na GUI, clique em **"Nova Gravação"**. Preencha os campos:

| Campo | O que colocar | Exemplo |
|-------|---------------|---------|
| **URL** | Endereço da aplicação que será testada | `https://homolog.meusistema.com.br/login` |
| **Sistema** | Nome do sistema/produto | `Portal Financeiro` |
| **Suite** | Conjunto de testes relacionados | `Login e Autenticação` |
| **Nome** | Nome descritivo do teste | `CT001-Login com credenciais válidas` |

### Opções de gravação

Marque as opções recomendadas:

- [x] **Complete** — gravação completa com captura de asserts sugeridos
- [x] **Validate** — valida campos obrigatórios ao final da gravação
- [x] **Pilot** — modo assistido com sugestões proativas do TestForge

Clique em **"Iniciar Gravação"**.

---

## 4. Gravando

### O que esperar

1. Um navegador Chromium abre automaticamente com sua aplicação
2. Um **overlay** aparece no canto superior direito: barra de status com botões (Pausar, Adicionar Assert, Parar)
3. O overlay mostra um contador de passos capturados

### Interagindo com a aplicação

Use a aplicação **normalmente**, como um usuário real faria:

- Preencha campos de formulário
- Clique em botões
- Navegue entre páginas
- Selecione opções em dropdowns

O TestForge captura tudo automaticamente.

### Adicionando asserts nos momentos certos

Asserts são verificações. Adicione-os quando algo **precisa ser verdade** para o teste passar:

| Momento | Assert recomendado |
|---------|--------------------|
| Após login bem-sucedido | Verificar que o nome do usuário aparece no header |
| Após envio de formulário | Verificar mensagem de sucesso: "Cadastro realizado" |
| Após exclusão | Verificar que o item sumiu da lista |
| Após erro intencional | Verificar mensagem de erro: "CPF inválido" |

**Como adicionar:** clique no botão "➕ Assert" no overlay, depois clique no elemento da página que quer verificar. Escolha o tipo de verificação (visível, texto contém, valor igual, etc.).

### Parando a gravação

Quando terminar o fluxo, clique em **"⏹ Parar"** no overlay. O navegador fecha e você volta para a GUI.

---

## 5. Revisando o resultado

Após parar a gravação, a GUI mostra o **Relatório de Completude**.

### Olhando o relatório de completude

O relatório lista cada passo do teste com ícones:

- ✅ Passo completo — capturado e compreendido
- ⚠️ Passo com ressalva — requer atenção
- ❌ Passo incompleto — requer intervenção

### Preenchendo campos pendentes

Passos marcados com ⚠️ ou ❌ precisam de ajuste:

1. Clique no passo problemático
2. Preencha campos faltantes (ex: field value que o MIS não inferiu)
3. Confirme ou corrija intents sugeridas
4. Resolva blind spots seguindo as instruções na tela

### Olhando o readiness report

No canto superior direito da tela de revisão, o **Readiness Gate** mostra o status atual:

| Status | Significado | Ação |
|--------|-------------|------|
| **READY** ✅ | Teste pronto para compilar | Pode avançar |
| **REVIEW** ⚠️ | Precisa de revisão, mas não está bloqueado | Revise os alertas e decida |
| **FAIL** ❌ | Problemas bloqueantes | Resolva os itens em vermelho antes de continuar |

**Só avance quando o status for READY** — ou REVIEW se você decidiu conscientemente ignorar alertas não-bloqueantes.

---

## 6. Compilando e executando

### Compilar

Com o `SemanticTestCase` pronto, compile para gerar o script executável:

```bash
testforge compile caminho/para/CT001-Login.testforge.json
```

Saída esperada:
```
[SUCCESS] Compilado: CT001-Login.spec.ts (Playwright)
[INFO] Healing layers: L0=3, L1=1, L2=0, L3=0
```

### Executar

Execute o teste compilado:

```bash
testforge run-incremental caminho/para/CT001-Login.spec.ts
```

### Interpretando o healing report

Se o teste falhar por mudanças na UI, o healing report mostra:

```
[HEALING] Passo 4: Seletor L0 falhou → L1 aplicado com sucesso
[HEALING] Passo 7: Seletor L0 e L1 falharam → L2 aplicado (texto "Salvar")
[WARNING] Passo 9: Todas as camadas L0-L3 falharam. Intervenção manual necessária.
```

- **L0 → L1 → L2 aplicados**: o teste se curou sozinho. Tudo certo.
- **L3 aplicado**: o teste se curou por heurística. Verifique se a interação ainda faz sentido.
- **Todas as camadas falharam**: o teste quebrou de verdade. Reabra na GUI e ajuste o passo manualmente.

---

## 7. Publicando

### Enviar para o repositório

Com o teste passando, publique:

```bash
testforge send caminho/para/CT001-Login/
```

Isso empacota o `SemanticTestCase`, o script compilado, e os metadados de healing, e envia para o repositório Git interno do TestForge.

### Verificar submission_report.json

Após o envio, um arquivo `submission_report.json` é gerado. Consulte-o:

```bash
cat caminho/para/CT001-Login/submission_report.json
```

Exemplo de conteúdo:

```json
{
  "test_id": "CT001",
  "status": "published",
  "timestamp": "2026-07-08T14:30:00Z",
  "warnings": [
    {
      "type": "PII_DETECTED",
      "field": "email",
      "message": "Campo contém dado similar a e-mail pessoal. Confirmar que é dado de teste."
    }
  ],
  "artifacts": {
    "semantic_testcase": "CT001-Login.testforge.json",
    "compiled_script": "CT001-Login.spec.ts",
    "healing_profile": "CT001-Login.healing.json"
  }
}
```

---

## 8. Checklist do QA

Antes de marcar o teste como **pronto** no seu quadro, confira cada item:

- [ ] **Todos os campos têm valor?** Nenhum field value ficou vazio ou com placeholder.
- [ ] **Readiness report mostra READY?** (REVIEW é aceitável se os alertas forem intencionais — ex: PII de dados de teste).
- [ ] **Teste compilado executa sem falhas?** Rodou `testforge run-incremental` e todos os passos passaram.
- [ ] **Dados sensíveis foram alertados mas não bloqueiam?** O relatório de PII está revisado e os dados usados são de teste, não de produção.
- [ ] **Teste cobre o fluxo feliz e pelo menos um cenário de erro?** Se o ticket pede só o caminho feliz, ok. Se pede variações, gravou-as.
- [ ] **O nome do teste é descritivo?** Outro QA consegue entender o que o teste faz só pelo nome.
- [ ] **Submission report não tem erros?** `status: "published"`.
- [ ] **Deu commit no repositório de testes?** Confirmar que o `testforge send` foi bem-sucedido e os artefatos estão versionados.

---

## Fluxo resumido (colar na parede)

```
Instalar → Abrir GUI → Gravar → Revisar (ready?) → Compilar →
→ Executar (passou?) → Publicar (send) → Checklist ✓ → Pronto ✅
```

---

## Ver também

- [Glossário](../REFERENCIA/GLOSSARY.md) — termos técnicos explicados
- [Guia do Usuário](../USER-GUIDE/) — documentação completa
- [Padrões de Teste](../TEST-PATTERNS.md) — boas práticas de gravação
