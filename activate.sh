#!/bin/bash
# TestForge v1 - Development Environment Activation
# Usage: source activate.sh

export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate Python virtual environment (OpenHarness)
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "[TestForge] Python venv activated (OpenHarness available as 'oh')"
fi

# Add project bin to PATH
export PATH="$PROJECT_ROOT/node_modules/.bin:$PATH"

echo "[TestForge] Development environment ready"
echo "  opencode  - Start OpenCode TUI"
echo "  oh        - Start OpenHarness"
echo "  @git      - Version control agent"
echo "  @bmad     - BMAD Method agent"
echo ""
echo "  REMEMBER: Commit after every change! Use @git agent."
