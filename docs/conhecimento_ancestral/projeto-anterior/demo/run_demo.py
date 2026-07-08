import json, threading, time, sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

WARROOT = "/home/febre/Projetos/testforge/packages/war-room/target-site"
DEMO_DIR = "/home/febre/Projetos/testforge/demo"

def serve():
    os.chdir(WARROOT)
    server = HTTPServer(("127.0.0.1", 18765), SimpleHTTPRequestHandler)
    server.serve_forever()

import os
t = threading.Thread(target=serve, daemon=True)
t.start()
time.sleep(1)

data = {
    "steps": [
        {"action": "navigate", "url": "http://127.0.0.1:18765/", "intention": "Abrir sistema de teste"},
        {"action": "fill", "selector": "[data-testid='campo-busca']", "value": "testforge",
         "intention": "Digitar termo de busca"},
        {"action": "click", "selector": "[data-testid='btn-buscar']", "intention": "Clicar em Buscar"},
        {"action": "click", "selector": "a", "intention": "Navegar para Cadastro (SPA)"},
        {"action": "fill", "selector": "[data-testid='input-nome']", "value": "Marilha Testadora",
         "intention": "Preencher nome"},
        {"action": "fill", "selector": "[data-testid='input-email']", "value": "marilha@testforge.ai",
         "intention": "Preencher email"},
        {"action": "select", "selector": "[data-testid='select-tipo']", "value": "pf", "text": "Pessoa Física",
         "intention": "Selecionar tipo PF usando label"},
        {"action": "assert", "assert_type": "textual", "selector": "h2", "expected_value": "Cadastro",
         "intention": "Verificar titulo da pagina"},
        {"action": "assert", "assert_type": "visivel", "selector": "[data-testid='btn-salvar']",
         "intention": "Verificar botao salvar visivel"},
        {"action": "assert", "assert_type": "estado", "selector": "[data-testid='btn-salvar']",
         "assert_state": "enabled", "intention": "Verificar botao habilitado"},
    ]
}

Path(DEMO_DIR).mkdir(parents=True, exist_ok=True)
data_path = Path(f"{DEMO_DIR}/demo_test.data.json")
data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
script_path = Path(f"{DEMO_DIR}/demo_test.py")
script_path.touch()

from testforge.core.execution.runner import TestRunner
from testforge.core.notification import notify_all

print("=" * 60)
print("  TESTFORGE — DEMONSTRAÇÃO COMPLETA (EPIC 1)")
print("=" * 60)

runner = TestRunner(str(script_path), headed=False, timeout=15000, debug=False)
report = runner.run()

print()
print("=" * 60)
print("  RELATÓRIO DE EXECUÇÃO")
print("=" * 60)
print(f"  Status: {report.status}")
print(f"  Duração: {report.duration_ms}ms")
print(f"  Resumo: {report.summary.executive}")
print()

for i, step in enumerate(report.steps):
    icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(step.status, "❓")
    print(f"  {icon} Passo {i+1}: {step.status.upper()} ({step.duration_ms}ms)")
    if step.error_message:
        print(f"     Erro: {step.error_message}")

print()
print("=" * 60)
print("  NOTIFICAÇÃO")
print("=" * 60)
print("  EmailNotifier: SMTP via env vars (TF_NOTIFY_EMAIL_*)")
print("  TeamsNotifier: webhook via TF_NOTIFY_TEAMS_WEBHOOK")
print("  Uso: testforge run script.py --notify")
notify_all(report, {"email": False, "teams": False})
print("  (notificação silenciosa — desligada por padrão)")
print()

print("=" * 60)
print("  COMANDOS CLI DISPONÍVEIS")
print("=" * 60)
print("  testforge record <url>       — gravar interações")
print("  testforge run <script>       — executar teste")
print("  testforge report <path>      — ver relatório")
print("  testforge report --history   — histórico de execuções")
print()

print("=" * 60)
print("  DEMONSTRAÇÃO CONCLUÍDA ✅")
print("=" * 60)
