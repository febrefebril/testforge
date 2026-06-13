#!/usr/bin/env bash
# TestForge — Script de Teste Completo
# Uso: ./testar-tudo.sh [--headed|--full]
set -euo pipefail

# ─── Modo ────────────────────────────────────────
MODE="${1:---headless}"
HEADED_FLAG="--headless"
FULL_MODE=false
if [ "$MODE" = "--headed" ]; then HEADED_FLAG="--headed"; fi
if [ "$MODE" = "--full" ]; then HEADED_FLAG="--headless"; FULL_MODE=true; fi

# ─── Pré-requisitos ──────────────────────────────
check_prereq() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ Pré-requisito faltando: $1"
    echo "   Instale: $2"
    exit 1
  fi
}
check_prereq python3 "Python 3.11+ (https://python.org)"
check_prereq curl "curl (apt install curl)"
check_prereq testforge "pip install testforge-core ou rode source /tmp/testforge-venv/bin/activate"

if ! python3 -c "import playwright" 2>/dev/null; then
  echo "❌ Playwright não instalado. Rode: pip install playwright && playwright install chromium"
  exit 1
fi

source /tmp/testforge-venv/bin/activate 2>/dev/null || true

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_RESET='\033[0m'

pass=0
fail=0
PID_MAIN=""; PID_CURATION=""; PID_COMPLETA=""

pass() { echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"; pass=$((pass+1)); }
fail() { echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"; fail=$((fail+1)); }
info() { echo -e "${COLOR_YELLOW}━━━ $1 ━━━${COLOR_RESET}"; }

cleanup() {
  info "Limpando processos..."
  [ -n "$PID_MAIN" ] && kill "$PID_MAIN" 2>/dev/null || true
  [ -n "$PID_CURATION" ] && kill "$PID_CURATION" 2>/dev/null || true
  [ -n "$PID_COMPLETA" ] && kill "$PID_COMPLETA" 2>/dev/null || true
  rm -rf /tmp/testforge-test-* /tmp/teste-cura 2>/dev/null
}
trap cleanup EXIT

# ─── Servidores de Teste ─────────────────────────
info "Iniciando servidores de teste..."
pkill -f "http.server 8080" 2>/dev/null || true
pkill -f "http.server 8081" 2>/dev/null || true
pkill -f "http.server 8082" 2>/dev/null || true
sleep 1

python3 -m http.server 8080 --directory testes/pagina-de-teste &
PID_MAIN=$!
python3 -m http.server 8081 --directory testes/pagina-de-teste-completa &
PID_COMPLETA=$!
python3 -m http.server 8082 --directory tests/test_pages/curation &
PID_CURATION=$!
sleep 1

# Validar servidores
for port in 8080 8081 8082; do
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/" 2>/dev/null | grep -q 200; then
    pass "Servidor :$port ativo"
  else
    fail "Servidor :$port não respondeu"
  fi
done

# ─── 1. Testes Unitários ─────────────────────────
info "Testes Unitários"
cd packages/core
if python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5 | grep -q "passed"; then
  pass "Todos os testes unitários passaram"
else
  fail "Testes unitários falharam"
fi
cd ../..

if [ "$FULL_MODE" = true ]; then
  info "── Modo Completo ──"
  echo "Siga o roteiro manual em: testes/roteiro-manual.md"
  echo "Inicie os servidores com:"
  echo "  python3 -m http.server 8081 --directory testes/pagina-de-teste-completa"
  echo "  python3 -m http.server 8082 --directory tests/test_pages/curation"
  echo ""
  echo "Após concluir o roteiro manual, pressione ENTER para continuar..."
  read -r
  info "Continuando com validações automáticas..."
fi

# ─── 2. Execução com Healing ─────────────────────
info "Execução com Healing — FAM-01 Seletor"
TEST_SCRIPT="/tmp/teste-cura/teste-cura.py"
HEALING_DB="/tmp/teste-cura/healing-catalog.jsonl"
mkdir -p /tmp/teste-cura
rm -f "$HEALING_DB"

if [ ! -f "$TEST_SCRIPT" ]; then
  python3 -c "
import json
steps = [{
    'action': 'navigate', 'url': 'http://localhost:8082/fam-01-selector/?error=1',
    'selector': '', 'tag_name': '', 'text': '', 'value': '', 'intention': '',
    'fallbacks': [], 'url': 'http://localhost:8082/fam-01-selector/?error=1',
    'attrs': {}, 'is_primary': True
}, {
    'action': 'click', 'selector': 'button:has-text(\"Elemento sem ID\")',
    'fallbacks': ['button.btn', 'button:first-of-type'],
    'tag_name': 'button', 'text': 'Elemento sem ID', 'value': '', 'url': '',
    'intention': '', 'attrs': {}, 'is_primary': True
}, {
    'action': 'assert_text', 'selector': '#result',
    'value': 'Sucesso', 'tag_name': 'div', 'text': '',
    'intention': '', 'fallbacks': [], 'url': '', 'attrs': {},
    'is_primary': True
}]
with open('/tmp/teste-cura/teste-cura.data.json', 'w') as f:
    json.dump({'steps': steps, 'url': steps[0]['url']}, f, indent=2)
"
  cat > "$TEST_SCRIPT" << 'PYEOF'
from testforge.core.execution.runner import PlaywrightRunner
from testforge.core.models.step import RecordedStep
import json
data = json.load(open("/tmp/teste-cura/teste-cura.data.json"))
runner = PlaywrightRunner(headless=True)
def main():
    ctx = runner.start()
    page = ctx.new_page()
    for i, s in enumerate(data["steps"]):
        step = RecordedStep(**s)
        runner.execute_step(page, step, index=i)
    runner.close()
main()
PYEOF
  pass "Script de teste criado em $TEST_SCRIPT"
fi

if testforge run "$TEST_SCRIPT" --healing "$HEALING_DB" 2>&1; then
  pass "Runner com healing concluído"
else
  fail "Runner com healing falhou"
fi

if [ -s "$HEALING_DB" ]; then
  pass "Catálogo de healing populado ($(wc -l < "$HEALING_DB") entradas)"
else
  fail "Catálogo de healing vazio"
fi

# Testar versão limpa (sem fallback)
python3 -c "
import json
d = json.load(open('/tmp/teste-cura/teste-cura.data.json'))
d['steps'][0]['url'] = 'http://localhost:8081/fam-01-selector/'
json.dump(d, open('/tmp/teste-cura/teste-cura.data.json', 'w'), indent=2)
"

if testforge run "$TEST_SCRIPT" 2>&1; then
  pass "Runner versão limpa concluído"
else
  fail "Runner versão limpa falhou"
fi

# ─── 3. Healing CLI ──────────────────────────────
info "CLI de Healing"
if testforge healing list 2>&1; then
  pass "healing list funcionou"
else
  fail "healing list falhou"
fi

if testforge healing review --all 2>&1; then
  pass "healing review --all funcionou"
else
  fail "healing review --all falhou"
fi

# ─── 4. Validar Página de Teste Completa ─────────
info "Validação da Página Completa"
TAXONOMIAS=$(curl -s http://localhost:8081/ 2>/dev/null | grep -o 'data-testid="tax-[A-Z][A-Z]*-[0-9]*"' | wc -l)
if [ "$TAXONOMIAS" -ge 70 ]; then
  pass "Página completa tem $TAXONOMIAS taxonomias (mínimo 70)"
else
  fail "Página completa tem apenas $TAXONOMIAS taxonomias"
fi

for f in iframe-content.html download-redirect.html slow-page.html assets/style.css assets/download-exemplo.txt; do
  if [ -f "testes/pagina-de-teste-completa/$f" ]; then
    pass "Arquivo auxiliar: $f"
  else
    fail "Arquivo auxiliar faltando: $f"
  fi
done

# Validar roteiro manual
if [ -f "testes/roteiro-manual.md" ]; then
  ROTEIRO_LINHAS=$(wc -l < testes/roteiro-manual.md)
  pass "Roteiro manual criado ($ROTEIRO_LINHAS linhas)"
else
  fail "Roteiro manual não encontrado"
fi

# ─── 5. Relatório ────────────────────────────────
info "Relatório"
if testforge report --history 2>&1; then
  pass "report --history funcionou"
else
  fail "report --history falhou"
fi

# ─── Resumo ──────────────────────────────────────
echo ""
info "RESUMO"
echo -e "${COLOR_GREEN}Passou: $pass${COLOR_RESET}"
echo -e "${COLOR_RED}Falhou: $fail${COLOR_RESET}"
if [ "$fail" -eq 0 ]; then
  echo -e "${COLOR_GREEN}✅ Todos os testes passaram!${COLOR_RESET}"
else
  echo -e "${COLOR_RED}❌ $fail teste(s) falharam.${COLOR_RESET}"
fi
