# Interface Gráfica (GUI)

O TestForge tem uma interface gráfica tkinter para gravar testes sem usar linha de comando.

## Abrindo

```bash
testforge-gui
```

Abre uma janela com o título **"TestForge v0.1.0  ·  Gravador de Testes"**.

![GUI screenshot — placeholder]

---

## Campos da interface

### Identificação da Gravação

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **URL \*** | Sim | Endereço da aplicação a gravar. Ex: `https://app.example.com` |
| **Nome** | Não | Nome da gravação. Se vazio, gera automático com timestamp. |
| **Sistema** | Recomendado | Nome do sistema. Ex: `MYSYSTEM`. Usado para organizar no Git. |
| **Suite** | Recomendado | Conjunto de testes. Ex: `credito`, `cadastro`. |
| **Caso de teste** | Não | Nome do caso. Padrão: mesmo valor do Nome. |

### Navegador

| Campo | Descrição |
|-------|-----------|
| **Browser** | Escolha entre Chromium, Chrome, ou Edge. |
| **Headless** | Se marcado, navegador não aparece (roda em background). |

### Configurações Avançadas

| Campo | Descrição |
|-------|-----------|
| **CDP** | Captura paralela via Chrome DevTools Protocol. Mantenha ligado. |
| **Diagnostic** | Modo standalone de telemetria. Não gera teste executável. |
| **Pipeline + Diagnostic** | Roda diagnostic junto com pipeline normal. |
| **Evidence** | `light` = sem screenshots. `full` = screenshot + DOM por evento. |

### Opções

| Campo | Descrição |
|-------|-----------|
| **Completude** | Após gravar, verifica campos pendentes e pergunta valores. |
| **Não-interativo** | Pula perguntas interativas. Gera template para preencher depois. |
| **Validar** | `--validate-before-ready`. Executa teste gerado e avalia qualidade. |
| **Pilot** | `--pilot-mode`. Validação automática; marca READY se passar. |

### Publicação Git (opcional)

Configure `URL`, `Token` e `Branch` do repositório Git para enviar a gravação automaticamente.

---

## Fluxo de uso

1. **Preencha URL** (obrigatório) e os campos de identificação
2. **Configure opções** conforme necessidade
3. **Clique "Iniciar"**
4. O navegador abre com o **overlay do TestForge** no canto superior direito
5. Interaja com a aplicação normalmente — o TestForge grava tudo
6. Use os atalhos do overlay (Shift+P pausar, Shift+S parar, Shift+A assert)
7. Ao terminar, clique **"Parar"** no overlay ou feche o navegador
8. O console na GUI mostra o progresso (PII scan, completude, validação, publicação)

---

## O console de log

A área inferior da GUI mostra o log em tempo real:

```
Iniciando: python -m testforge.cli.app record https://...
------------------------------------------------------------
[TestForge] Gravando: CT-001
  URL: https://...
  Contexto: SIMULADOR / credito / CT-001
  Viewport: 1280x720 (headless)
...
[TestForge] Sessao salva: recordings/CT-001/
[TestForge] [OK] Relatorio: recordings/CT-001/readiness/readiness_report.md
[TestForge] [OK] Publicado: recordings/SIMULADOR/credito/CT-001 (abc12345)
------------------------------------------------------------
Processo encerrado (codigo 0)
```

---

## Dicas

- **Sempre preencha Sistema + Suite.** Sem eles a gravação vai para `uncategorized/`.
- **Mantenha CDP ligado.** Ele captura a árvore de acessibilidade e melhora seletores.
- **Use Validar + Pilot** após gravar — o TestForge executa o teste gerado e avalia se está pronto para o time.
- **Headless** é útil para CI ou gravações rápidas sem interface visual.
