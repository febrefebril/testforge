# mode: outline (arquivo grande — apenas assinaturas)

# [OUTLINE — corpo omitido por limite de tamanho]
"""TestForge CLI — Comandos: record, compile, run, pipeline, demo-heal."""
import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import time
from playwright.sync_api import sync_playwright
from testforge.browser import launch_browser
from testforge.recorder import RecorderController
from testforge.evidence import EvidenceCollector
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler
from testforge.oracle import OracleRunner
from testforge.promotion import PromotionGate
from testforge.taxonomy import FailureClassifier
from testforge.runner import FallbackRunner
from testforge.metrics import MetricsRepository, StepOutcome
from testforge.healing import HealingCatalog, HealingRecipe, EvidencePayload
from testforge.healing import CuradorAutomatico, CurationOutcome, ProgressResult
from testforge.evidence import EvidenceCollector
from testforge.validation import validate_url
from testforge.validation.intent_completeness import IntentCompletenessChecker, save_completeness_report
from testforge.recorder.recording_status import RecordingStatus
from testforge.reporting import RunReport, StepReport
import pathlib
_PROJECT_ROOT = ...
import re as _re
def _sanitize_name(name: str):
    """Sanitiza nome de teste/gravacao: remove caracteres especiais, mantem alfanumericos, underscore, hifen."""
    ...
def _make_context_kwargs(headless: bool, verify_ssl: bool=True):
    """Retorna kwargs do browser.new_context: viewport fixo em headless, no_viewport=True em headed."""
    ...
def _validate_and_warn_url(url: str):
    """Valida URL e imprime avisos. Retorna True se houver avisos críticos."""
    ...
def _update_recording_status(rec_dir: str, rec_id: str, status: RecordingStatus):
    """Atualiza recording_metadata.json com novo status de gravação."""
    ...
def _run_post_recording_completion(rec_dir: str, rid: str, args, auto_complete: bool, no_interactive: bool):
    """Executa verificacao de completude de intencao + prompt interativo opcional apos gravacao."""
    ...
def _run_post_recording_validation(rec_dir: str, rid: str, args, stc, completeness_report):
    """Pipeline completa de validacao: verificacao de completude + readiness gate."""
    ...
def _mark_failed_recording(rec_dir: str, rid: str, reason: str='validation_failed'):
    """Marca gravacao como falha em um diretorio dedicado sem mover artefatos originais."""
    ...
def _check_python_keyboard(page, recorder):
    """Monitora estado do assert e ativa via Python se necessario."""
    ...
def _load_config_defaults():
    """Le defaults: secao do .testforge/config.yml. Retorna {} em caso de erro."""
    ...
_LAST_VALUES_FILE = ...
def _load_last_values():
    """Carrega ultimos valores fornecidos. Retorna {} em caso de erro."""
    ...
def _save_last_values(system: str='', suite: str='', test_case: str=''):
    """Salva ultimos valores para preenchimento futuro."""
    ...
def _auto_publish_recording(rid: str, rec_dir: str):
    """Auto-publica artefatos de gravacao no Git se env vars configuradas."""
    ...
def _find_recording_leaf_dirs(base_dir: str):
    """Retorna diretorios de gravacao "folha" abaixo de base_dir."""
    ...
def _record_qa_wizard(args):
    """Wizard modo simples (alinhado com GUI): pergunta dados do teste"""
    ...
def cmd_record(args):
    """Grava fluxo de teste com comandos de teclado."""
    ...
def _publish_diagnostic_to_azure(recording_id: str, diagnostic_dir: str):
    """Sprint 0 commit 6: publish diagnostic/ to Azure DevOps repo via Z5 chain."""
    ...
def _prompt_gherkin_confirm(writer):
    """C4c — solicita confirmacao ou alteracao do Gherkin auto-derivado."""
    ...
import shutil
import subprocess
def _open_in_editor(path: str):
    """Hotfix BUG 4: resolucao graciosa do EDITOR."""
    ...
def _auto_learn(error_msg: str, solution: str, framework: str='generic'):
    """Registra automaticamente licao aprendida no catalogo de cura."""
    ...
def cmd_compile(args):
    ...
def cmd_audit(args):
    """Audita gravacao: metricas de qualidade, analise de eventos, status de compilacao."""
    ...
def cmd_run(args):
    """Executa script Playwright inline com healing L0→L3 via CuradorAutomatico."""
    ...
def _heal_step(page, step, error_msg: str, base_url: str, step_num: int, recording_id: str, app_name: str, debug_healing: bool=False):
    """Tenta curar um step falho usando o pipeline L0→L3."""
    ...
def _try_heal_inline(base_url: str, headless: bool, error_text: str, script_path: str, recording_id: str, browser_type: str='chromium', verify_ssl: bool=True):
    """Fallback: tenta curar script inteiro inline (modo antigo)."""
    ...
def cmd_pipeline(args):
    """Pipeline completa: record → compile → run."""
    ...
def cmd_demo_heal(args):
    """Demo de healing real: grava → quebra seletor → healing corrige."""
    ...
def cmd_pilot_report(args):
    """Gera relatorio consolidado de readiness do piloto a partir de todas as gravacoes."""
    ...
def cmd_admin_install_pat(args):
    """Sprint 0 Z1: persist Azure DevOps credentials with 0600 permission."""
    ...
def cmd_diagnose(args):
    """Sprint 0 alias: invokes cmd_record with diagnostic_mode forced True."""
    ...
def cmd_dashboard(args):
    """Fase 6: gera dashboard.html estatico."""
    ...
def cmd_catalog_migrate(args):
    """Fase 4: importa receitas JSONL legadas para o catalogo de intencoes SQLite."""
    ...
def cmd_catalog_export(args):
    """Fase 4: exporta catalogo de intencoes SQLite para JSONL."""
    ...
def cmd_submit(args):
    """P0.2-S: review and prepare a safe copy. Never publishes to Git."""
    ...
def cmd_send(args):
    """Re-publica artefatos de gravacao para o repositorio Git configurado."""
    ...
def _setup_logging(verbose: bool=False):
    """Configura logging estruturado para componentes do TestForge."""
    ...
def main():
    ...

