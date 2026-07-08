#!/bin/bash
# TestForge v1 - Setup do Ambiente Virtual
# Uso: bash setup.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "==> TestForge v1 - Setup do Ambiente Virtual"
echo "==> Diretorio: $PROJECT_ROOT"
echo ""

# ---- 1. Python Virtual Environment ----
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "=> Criando Python venv..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

echo "=> Instalando dependencias Python..."
source "$PROJECT_ROOT/.venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$PROJECT_ROOT/requirements.txt" -q
echo "   Python: $(python --version)"
echo "   OpenHarness: $(pip show openharness-ai | grep Version | cut -d' ' -f2)"

# ---- 2. BMAD Method ----
echo ""
echo "=> Instalando BMAD Method..."
npx bmad-method install --directory "$PROJECT_ROOT" --modules bmm --tools opencode --yes 2>&1 | grep -E "installed|ready|✓" || true

# ---- 3. GSD Core ----
echo ""
echo "=> Instalando GSD Core..."
npx @opengsd/gsd-core@latest --opencode --local --config-dir "$PROJECT_ROOT/.config/opencode" 2>&1 | grep -E "Installed|Done|✓" || true

# ---- 4. MCP Dependencies ----
echo ""
echo "=> Instalando dependencias MCP..."
npx -y npm install --prefix "$PROJECT_ROOT/.config/opencode" 2>&1 | tail -3 || true

echo ""
echo "=================================="
echo " Setup concluido!"
echo " Ative o ambiente: source activate.sh"
echo " Inicie: opencode"
echo "=================================="
