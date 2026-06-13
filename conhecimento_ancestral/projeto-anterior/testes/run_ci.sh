#!/usr/bin/env bash
set -euo pipefail

CI_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$CI_DIR")"
cd "$ROOT"

echo "=== TestForge CI ==="
echo ""

echo "--- 1. Verificando servidor de teste ---"
if ! curl -s -o /dev/null http://localhost:8000/index.html 2>/dev/null; then
    echo "Iniciando servidor..."
    cd testes/pagina-de-teste && python3 -m http.server 8000 &
    SERVER_PID=$!
    cd "$ROOT"
    sleep 2
    if ! curl -s -o /dev/null http://localhost:8000/index.html; then
        echo "ERRO: servidor nao iniciou"
        exit 1
    fi
    echo "Servidor OK (PID $SERVER_PID)"
else
    echo "Servidor OK (ja rodando)"
    SERVER_PID=""
fi

echo ""
echo "--- 2. Suite de elementos da pagina de teste ---"
cd "$ROOT"
uv run pytest testes/pagina-de-teste/tests/ -v -x --tb=long 2>&1
echo "✅ Suite de elementos OK"

echo ""
echo "--- 3. Gravacao automatizada ---"
CI=true uv run python testes/gravacao-automatizada/gravacao_automatizada.py 2>&1
echo "✅ Gravacao automatizada OK"

echo ""
echo "--- 4. Limpeza ---"
if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
fi

echo ""
echo "=== ✅ CI PASSOU ==="
