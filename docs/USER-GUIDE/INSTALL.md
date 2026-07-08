# Instalação do TestForge

Guia de instalação para Windows e Linux. Ao final você terá o CLI `testforge` e a interface gráfica `testforge-gui` funcionando.

---

## Pré-requisitos

| Ferramenta | Windows | Linux |
|---|---|---|
| Python 3.10+ | [python.org](https://python.org) — **marque "Add to PATH"** e **"tcl/tk"** | `sudo apt install python3 python3-tk python3-venv` |
| Git | [git-scm.com](https://git-scm.com) | `sudo apt install git` |
| Playwright browsers | Automático no passo 4 | Automático no passo 4 |

---

## Passo 1 — Clonar o repositório

```bash
git clone <url-do-repositorio> testforge
cd testforge
```

---

## Passo 2 — Criar ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Windows (cmd):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux:**
```bash
source activate.sh
# ou manualmente:
python -m venv .venv
source .venv/bin/activate
```

---

## Passo 3 — Instalar o TestForge

```bash
pip install -e ".[dev]"
```

O `-e` instala em modo editável (mudanças no código refletem imediatamente). O `[dev]` instala dependências de desenvolvimento e teste.

---

## Passo 4 — Instalar navegadores Playwright

```bash
playwright install chromium
```

Isto baixa o Chromium que o TestForge usa para gravar e executar testes.

---

## Passo 5 — Verificar

```bash
# Versão do CLI
testforge --version
# Deve mostrar: TestForge v0.1.0

# Interface gráfica
testforge-gui
# Deve abrir janela com "TestForge v0.1.0  ·  Gravador de Testes"
```

---

## Problemas comuns

### "tkinter não encontrado" (Windows)
Reinstale o Python do [python.org](https://python.org) marcando a opção **"tcl/tk and IDLE"** durante a instalação.

### "command not found: testforge" (Linux)
O ambiente virtual pode não estar ativo. Rode `source activate.sh` novamente.

### "playwright: command not found"
O Playwright não foi instalado no ambiente virtual. Rode `pip install playwright` e depois `playwright install chromium`.

### "auto-updater: git pull falhou" (inofensivo)
O auto-updater tenta puxar atualizações mas não está configurado. Ignore esta mensagem — não afeta a gravação.

### Chromium não abre (Linux)
Pode faltar dependências de sistema:
```bash
sudo apt install libgtk-3-0 libgbm1 libnss3 libasound2
```
