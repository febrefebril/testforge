# TestForge — Quick Start

**Grave seu primeiro teste em 5 minutos.**

---

## 1. Requisitos

- Python 3.10+
- Google Chrome ou Chromium

## 2. Instalação

```bash
cd testforge
source .venv/bin/activate
playwright install chromium
```

## 3. Grave um fluxo

```bash
testforge record --app CAIXA https://habitacao.caixa.gov.br/simulador --name simulador-credito
```

O navegador abre automaticamente. Execute o fluxo desejado.

**Atalhos durante a gravação:**

| Atalho | Ação |
|--------|------|
| `Shift+S` | Parar e salvar |
| `Shift+A` | Marcar verificação (assert) |
| `Shift+P` | Pausar/retomar |

## 4. Execute o teste

```bash
testforge run --recording simulador-credito
```

## 5. Veja o código gerado

```bash
cat recordings/simulador-credito/script.py
```

---

**Próximos passos:** [Guia Completo](GRAVAR-FLUXO.md) — [Troubleshooting](TROUBLESHOOTING.md)
