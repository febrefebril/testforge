#!/bin/bash
# TestForge v1 - Ambiente Virtual de Desenvolvimento
# Uso: source activate.sh

export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Python Virtual Environment (OpenHarness SDK) ----
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "[TestForge] Python venv ativado ($(.venv/bin/python --version))"
    echo "[TestForge] OpenHarness $(pip show openharness-ai 2>/dev/null | grep Version | cut -d' ' -f2)"
fi

# ---- Node.js bins (GSD Core, BMAD, MCPs) ----
NODE_BINS="$PROJECT_ROOT/.config/opencode/node_modules/.bin"
GSD_BIN="$PROJECT_ROOT/.config/opencode/gsd-core/bin"
if [ -d "$NODE_BINS" ]; then
    export PATH="$NODE_BINS:$GSD_BIN:$PATH"
fi

# ---- Project no PATH ----
export PATH="$PROJECT_ROOT:$PATH"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  TestForge v1 - Ambiente Pronto              ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  opencode     → OpenCode TUI                 ║"
echo "║  oh           → OpenHarness CLI              ║"
echo "║  @git         → Versionamento                ║"
echo "║  @bmad        → BMAD Method                  ║"
echo "║  /gsd-*       → GSD Core Pipeline            ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  ⚠  COMMIT APOS CADA MUDANCA! Use @git       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Lembrar ao sair
function testforge_reminder() {
    echo ""
    echo "[TestForge] Verifique se fez commit antes de sair: git status"
}
trap testforge_reminder EXIT
